"""Efecto AJUSTADO de cada interconsulta sobre las horas hasta hospitalizacion (ingresados, episodio unico, >=15 min).
Regresion cuantil (mediana) con controles: edad, sexo, hora y dia de llegada, anio, censo de urgencias y de hospitalizacion
a la llegada, UCI. Compara el efecto crudo (diferencia de medianas) con el ajustado."""
import duckdb, os, json, numpy as np, pandas as pd
import statsmodels.formula.api as smf
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect(read_only=True)
ETQ = {'Referral to trauma and orthopaedics surgery service': 'ortopedia', 'Seen by urology service': 'urologia',
       'Anesthesia consultation': 'anestesia', 'Seen by general surgery service': 'cirugia', 'Seen by psychiatrist': 'psiquiatria',
       'Referral to obstetrics and gynecology service': 'ginecobstetricia', 'Referral to pediatrician': 'pediatria',
       'Specialized medical examination': 'examen_especializado', 'Other consultation': 'otra_interconsulta',
       'Emergency department Consult note': 'nota_interconsulta_urg', 'Seen by hospital-based dietetics service': 'nutricion'}
d = con.execute("""
  SELECT a.visit_occurrence_id, a.h_en_urg, a.edad, a.sexo, hour(a.llegada) hora, isodow(a.llegada) dow, year(a.llegada) anio,
         a.censo_urg, a.censo_hosp, coalesce(v.uci, false) uci
  FROM ep1 a LEFT JOIN vflags v USING (visit_occurrence_id) WHERE a.ingresa AND a.edad IS NOT NULL""").df()
s = con.execute("SELECT visit_occurrence_id, servicio FROM svc").df()
s = s[s.servicio.isin(ETQ)]
s["servicio"] = s.servicio.map(ETQ)
dummies = pd.crosstab(s.visit_occurrence_id, s.servicio).clip(upper=1)
d = d.join(dummies, on="visit_occurrence_id").fillna({c: 0 for c in ETQ.values()})
d["franja"] = pd.cut(d.hora, [-1, 6, 8, 17, 23], labels=["madrugada", "temprano", "dia", "noche"]).astype(str)
d["uci"] = d.uci.astype(int); d["sexo"] = d.sexo.astype(str)
servs = list(ETQ.values())
formula = "h_en_urg ~ " + " + ".join(servs) + " + edad + C(sexo) + C(franja) + C(dow) + C(anio) + censo_urg + censo_hosp + uci"
m = smf.quantreg(formula, d).fit(q=0.5, max_iter=5000)
ci = m.conf_int()
filas = []
for sname in servs:
    con_ = d.loc[d[sname] == 1, "h_en_urg"]; sin_ = d.loc[d[sname] == 0, "h_en_urg"]
    filas.append(dict(servicio=sname, n=int((d[sname] == 1).sum()), crudo_h=round(con_.median() - sin_.median(), 1),
                      ajustado_h=round(m.params[sname], 1), ic95_inf=round(ci.loc[sname, 0], 1), ic95_sup=round(ci.loc[sname, 1], 1),
                      p_valor=float(m.pvalues[sname])))
t = pd.DataFrame(filas).sort_values("ajustado_h", ascending=False)
t.to_csv("derived/interconsultas_ajustado.csv", index=False)
extra = {k: round(float(m.params[k]), 2) for k in ["edad", "censo_urg", "censo_hosp", "uci"]}
extra.update({k: round(float(v), 1) for k, v in m.params.items() if k.startswith("C(franja)")})
json.dump({"n": len(d), "controles": extra, "pseudo_r2": round(float(m.prsquared), 3)}, open("derived/interconsultas_ajustado_meta.json", "w"), indent=1)
print(len(d), "ingresados"); print(t.to_string(index=False)); print(extra, "pseudoR2", round(m.prsquared, 3))
