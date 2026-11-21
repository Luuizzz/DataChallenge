"""
Simulacion de eventos discretos (cola FIFO con C camas) del paso urgencias -> hospitalizacion.
Cada paciente que ingresa (2025, sin UCI) llega a urgencias a su hora REAL, necesita un tiempo de estudio/interconsulta W
(aleatorio, segun su perfil) y luego pide cama. Recibe cama cuando se libera una (FIFO). Ocupa la cama su estancia REAL,
y el alta ocurre el dia que corresponde a una hora del dia muestreada de la distribucion REAL de horas de alta.
Parametros no observables (camas efectivas C, fraccion k del tiempo que es estudio, dispersion s) se calibran para
reproducir tres hechos observados: mediana 24 h, 28 h si llega de dia (9-17 h) y 16 h si llega de madrugada (0-6 h).
Los escenarios se reportan como DIFERENCIA frente a la linea base calibrada (mas robusto que los valores absolutos).
"""
import duckdb, os, heapq, json, itertools, numpy as np, pandas as pd
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
from hun.cola import asignar_camas
con = connect(read_only=True)
df = con.execute("""SELECT llegada, t_obs_h, los_d, grupo, hour(t_alta_hosp) + minute(t_alta_hosp)/60.0 h_alta
                    FROM sim_in WHERE grupo<>'UCI' AND llegada >= '2024-07-01' ORDER BY llegada, t_obs_h, los_d, grupo, h_alta""").df()
t0 = pd.Timestamp('2024-07-01')
A = ((df.llegada - t0).dt.total_seconds()/3600).to_numpy()
LOS = df.los_d.to_numpy()*24
G = df.grupo.to_numpy()
H_ALTA = df.h_alta.to_numpy()                      # distribucion empirica de horas de alta
med_obs = df.groupby('grupo').t_obs_h.median().to_dict()
hora_lleg = df.llegada.dt.hour.to_numpy()
eval_mask = (df.llegada >= '2025-01-01').to_numpy()  # 6 meses de calentamiento
TARGET = dict(med=24.0, dia=28.0, noche=16.3)

def simular(C, k, s, seed, f_alta_am=0.0, r_quir=1.0, extra_camas=0):
    rng = np.random.default_rng(seed)
    med_w = np.array([k*med_obs[g] for g in G]) * np.where(G=='QUIR', r_quir, 1.0)
    W = med_w * np.exp(rng.normal(0, s, len(G)))
    req = A + W
    order = np.argsort(req)
    h_alta = rng.choice(H_ALTA, len(G))
    if f_alta_am > 0:                               # adelantar una fraccion de las altas de la tarde a 9-12 h del mismo dia
        mover = (h_alta >= 12) & (rng.random(len(G)) < f_alta_am)
        h_alta = np.where(mover, rng.uniform(9, 12, len(G)), h_alta)
    start = asignar_camas(req, LOS, h_alta, C + extra_camas)
    T = start - A; B = start - req
    return T, B

def resumen(T, B):
    m = eval_mask; t = T[m]; b = B[m]
    return dict(med=np.median(t), p90=np.quantile(t,0.9), pct24=100*np.mean(t>24),
                dia=np.median(t[(hora_lleg[m]>=9)&(hora_lleg[m]<=17)]), noche=np.median(t[hora_lleg[m]<=6]),
                espera_cama_med=np.median(b), espera_cama_p90=np.quantile(b,0.9),
                horas_paciente_anio=t.sum(), censo_espera_cama=b.sum()/(365*24))

# --- calibracion (grid) ---
best = None
for C, k, s in itertools.product(range(150, 341, 10), [0.2,0.3,0.4,0.5,0.6], [0.8,1.0,1.2]):
    r = resumen(*simular(C, k, s, seed=1))
    loss = sum((r[x]-TARGET[x])**2 for x in TARGET)
    if best is None or loss < best[0]: best = (loss, C, k, s, r)
loss, C, k, s, r = best
# refinamiento fino alrededor del mejor C
for C2, k2 in itertools.product(range(C-9, C+10, 1), [k-0.05, k, k+0.05]):
    r2 = resumen(*simular(C2, k2, s, seed=1))
    l2 = sum((r2[x]-TARGET[x])**2 for x in TARGET)
    if l2 < loss: loss, C, k, r = l2, C2, k2, r2
cal = dict(camas_efectivas=C, fraccion_estudio_k=k, dispersion_s=s, error_cuadratico=round(loss,2), ajuste={x: round(r[x],1) for x in TARGET}, objetivo=TARGET)
print('CALIBRACION', cal)

# --- escenarios (10 replicas cada uno) ---
ESC = {
 'base': {},
 'altas_am_30pct': dict(f_alta_am=0.30),
 'altas_am_50pct': dict(f_alta_am=0.50),
 'interconsulta_quir_-25pct': dict(r_quir=0.75),
 'interconsulta_quir_-50pct': dict(r_quir=0.50),
 'combinado_altas30_quir25': dict(f_alta_am=0.30, r_quir=0.75),
 'combinado_altas50_quir50': dict(f_alta_am=0.50, r_quir=0.50),
 'referencia_+10_camas': dict(extra_camas=10),
}
res, REPS = {}, {}
for nombre, kw in ESC.items():
    reps = [resumen(*simular(C, k, s, seed=100+j, **kw)) for j in range(30)]
    REPS[nombre] = reps
    res[nombre] = {m: (float(np.mean([x[m] for x in reps])), float(np.quantile([x[m] for x in reps],0.025)), float(np.quantile([x[m] for x in reps],0.975))) for m in reps[0]}
base = res['base']
def dq(nombre, m):  # IC 95 % de la diferencia pareada (mismas semillas) frente a la base
    d = [REPS[nombre][j][m] - REPS['base'][j][m] for j in range(30)]
    return [round(float(np.quantile(d, 0.025)), 1), round(float(np.quantile(d, 0.975)), 1)]
tabla = []
for nombre, v in res.items():
    tabla.append(dict(escenario=nombre,
        mediana_h=round(v['med'][0],1), p90_h=round(v['p90'][0],1), pct_mas24h=round(v['pct24'][0],1),
        espera_cama_mediana_h=round(v['espera_cama_med'][0],1),
        delta_mediana_h=round(v['med'][0]-base['med'][0],1), delta_mediana_ic95=dq(nombre,'med'),
        delta_p90_h=round(v['p90'][0]-base['p90'][0],1), delta_p90_ic95=dq(nombre,'p90'),
        horas_paciente_ahorradas_anio=round(base['horas_paciente_anio'][0]-v['horas_paciente_anio'][0]),
        censo_esperando_cama=round(v['censo_espera_cama'][0],1)))
t = pd.DataFrame(tabla); print(t.to_string(index=False))
json.dump(dict(calibracion=cal, escenarios=tabla), open('derived/simulacion.json','w'), indent=1, ensure_ascii=False)
t.to_csv('derived/simulacion_escenarios.csv', index=False)
