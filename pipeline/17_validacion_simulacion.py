"""Validacion FUERA DE MUESTRA de la simulacion: parametros calibrados con 2025 (C=269, k=0.55, s=0.8, medianas de estudio por
perfil de 2025) aplicados a las llegadas reales de ene-mar 2026 (no usadas en la calibracion). Se compara lo simulado con lo
observado en 2026: mediana, llegada de dia, llegada de madrugada y % > 24 h."""
import duckdb, os, heapq, json, numpy as np, pandas as pd
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect(read_only=True)
cal = json.load(open("derived/simulacion.json", encoding="utf-8"))["calibracion"]
C, k, s = cal["camas_efectivas"], cal["fraccion_estudio_k"], cal["dispersion_s"]
q = """
WITH g AS (SELECT visit_occurrence_id,
             bool_or(servicio IN ('Referral to trauma and orthopaedics surgery service','Seen by urology service','Anesthesia consultation','Seen by general surgery service')) quir,
             count(*) n_svc FROM svc GROUP BY 1)
SELECT e.llegada, e.h_en_urg t_obs_h, e.d_estancia_hosp los_d, hour(e.t_alta_hosp) + minute(e.t_alta_hosp)/60.0 h_alta,
  CASE WHEN coalesce(v.uci,false) THEN 'UCI' WHEN coalesce(g.quir,false) THEN 'QUIR' WHEN g.n_svc>0 THEN 'OTRA_IC' ELSE 'SIN_IC' END grupo
FROM ed e LEFT JOIN vflags v USING (visit_occurrence_id) LEFT JOIN g USING (visit_occurrence_id)
WHERE e.ingresa AND e.d_estancia_hosp > 0 AND e.h_en_urg >= 0 AND e.llegada >= '2025-07-01' AND e.llegada < '2026-04-01' ORDER BY ALL"""
df = con.execute(q).df()
df = df[df.grupo != "UCI"].sort_values("llegada").reset_index(drop=True)
med_2025 = con.execute("SELECT grupo, median(t_obs_h) FROM sim_in WHERE llegada >= '2025-01-01' AND grupo<>'UCI' GROUP BY 1").fetchall()
med_obs = dict(med_2025)
t0 = pd.Timestamp("2025-07-01")
A = ((df.llegada - t0).dt.total_seconds() / 3600).to_numpy(); LOS = df.los_d.to_numpy() * 24; G = df.grupo.to_numpy()
H_ALTA = con.execute("SELECT hour(t_alta_hosp) + minute(t_alta_hosp)/60.0 FROM sim_in WHERE llegada >= '2025-01-01' AND grupo<>'UCI' ORDER BY 1").df().iloc[:, 0].to_numpy()
hora = df.llegada.dt.hour.to_numpy(); ev = (df.llegada >= "2026-01-01").to_numpy()


def simular(seed):
    rng = np.random.default_rng(seed)
    W = np.array([k * med_obs[g] for g in G]) * np.exp(rng.normal(0, s, len(G)))
    req = A + W; h_alta = rng.choice(H_ALTA, len(G)); camas = []; start = np.empty(len(G))
    for i in np.argsort(req):
        r = req[i]
        si = r if len(camas) < C else max(r, heapq.heappop(camas))
        fin = np.floor((si + LOS[i]) / 24) * 24 + h_alta[i]
        if fin < si + 2: fin += 24
        heapq.heappush(camas, fin); start[i] = si
    return start - A


def res(t):
    return dict(mediana=np.median(t[ev]), dia=np.median(t[ev & (hora >= 9) & (hora <= 17)]), madrugada=np.median(t[ev & (hora <= 6)]), pct24=100 * np.mean(t[ev] > 24))


obs = res(df.t_obs_h.to_numpy())
sims = [res(simular(300 + j)) for j in range(20)]
simm = {m: (float(np.mean([x[m] for x in sims])), float(np.quantile([x[m] for x in sims], .025)), float(np.quantile([x[m] for x in sims], .975))) for m in obs}
tabla = pd.DataFrame([dict(indicador=m, observado_2026=round(obs[m], 1), simulado=round(simm[m][0], 1), sim_ic95=f"{simm[m][1]:.1f}–{simm[m][2]:.1f}",
                           error=round(simm[m][0] - obs[m], 1)) for m in obs])
tabla.to_csv("derived/validacion_simulacion_2026.csv", index=False)
json.dump(dict(periodo="ene-mar 2026 (fuera de muestra)", n=int(ev.sum()), parametros=dict(C=C, k=k, s=s), tabla=tabla.to_dict("records")),
          open("derived/validacion_simulacion_2026.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(int(ev.sum()), "ingresos evaluados"); print(tabla.to_string(index=False))


# --- Recalibracion de la capacidad para 2026 y estabilidad de los efectos de las medidas ---
def simular_kw(seed, CC, f_alta_am=0.0, r_quir=1.0, extra=0):
    rng = np.random.default_rng(seed)
    W = np.array([k * med_obs[g] for g in G]) * np.where(G == "QUIR", r_quir, 1.0) * np.exp(rng.normal(0, s, len(G)))
    req = A + W; h_alta = rng.choice(H_ALTA, len(G))
    if f_alta_am > 0:
        mover = (h_alta >= 12) & (rng.random(len(G)) < f_alta_am)
        h_alta = np.where(mover, rng.uniform(9, 12, len(G)), h_alta)
    camas = []; start = np.empty(len(G))
    for i in np.argsort(req):
        r = req[i]
        si = r if len(camas) < CC + extra else max(r, heapq.heappop(camas))
        fin = np.floor((si + LOS[i]) / 24) * 24 + h_alta[i]
        if fin < si + 2: fin += 24
        heapq.heappush(camas, fin); start[i] = si
    return start - A


grid = {CC: np.mean([np.median(simular_kw(400 + j, CC)[ev]) for j in range(5)]) for CC in range(250, 270)}
C26 = min(grid, key=lambda c: abs(grid[c] - obs["mediana"]))
base26 = [res(simular_kw(500 + j, C26)) for j in range(20)]
fit26 = {m: round(float(np.mean([x[m] for x in base26])), 1) for m in obs}
esc = {"altas_am_50pct": dict(f_alta_am=0.5), "interconsulta_quir_-50pct": dict(r_quir=0.5),
       "combinado_altas50_quir50": dict(f_alta_am=0.5, r_quir=0.5), "referencia_+10_camas": dict(extra=10)}
deltas = {}
for nombre, kw in esc.items():
    d = [np.median(simular_kw(500 + j, C26, **kw)[ev]) - np.median(simular_kw(500 + j, C26)[ev]) for j in range(20)]
    deltas[nombre] = dict(delta_mediana=round(float(np.mean(d)), 1), ic95=[round(float(np.quantile(d, .025)), 1), round(float(np.quantile(d, .975)), 1)])
out2 = dict(C_2025=C, C_2026_recalibrada=int(C26), ajuste_2026=fit26, observado_2026={m: round(float(v), 1) for m, v in obs.items()}, deltas_2026=deltas)
json.dump(out2, open("derived/recalibracion_2026.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out2, indent=1, ensure_ascii=False))
