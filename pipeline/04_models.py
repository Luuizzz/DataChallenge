import duckdb, os, numpy as np, pandas as pd, lightgbm as lgb, json
from sklearn.metrics import roc_auc_score, average_precision_score, mean_absolute_error
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect()
con.execute("""
CREATE OR REPLACE TABLE feat AS
WITH b AS (
  SELECT *, split_part(secuencia,'>',1) primera_etapa FROM ed_c WHERE llegada < '2026-05-01'),
h AS (
  SELECT *,
    count(*) OVER (PARTITION BY person_id ORDER BY llegada RANGE BETWEEN INTERVAL 30 DAY PRECEDING AND INTERVAL 1 SECOND PRECEDING) urg_30d,
    count(*) OVER (PARTITION BY person_id ORDER BY llegada RANGE BETWEEN INTERVAL 365 DAY PRECEDING AND INTERVAL 1 SECOND PRECEDING) urg_365d,
    sum(ingresa::INT) OVER (PARTITION BY person_id ORDER BY llegada RANGE BETWEEN INTERVAL 365 DAY PRECEDING AND INTERVAL 1 SECOND PRECEDING) ingresos_365d,
    epoch(llegada - lag(llegada) OVER (PARTITION BY person_id ORDER BY llegada))/86400 dias_desde_ultima
  FROM b)
SELECT h.*, hour(llegada) hora, dayofweek(llegada) dow, month(llegada) mes,
  (SELECT count(*) FROM 'visit_occurrence.parquet' v WHERE v.person_id=h.person_id AND v.visit_concept_id=581479
     AND v.visit_start_datetime < h.llegada AND v.visit_start_datetime >= h.llegada - INTERVAL 365 DAY) rehab_365d
FROM h
""")
df = con.execute("SELECT * FROM feat ORDER BY ALL").df()
df['sexo'] = df['sexo'].astype('category'); df['primera_etapa'] = df['primera_etapa'].astype('category')
base = ['edad','sexo','hora','dow','mes','censo_urg','censo_hosp','urg_30d','urg_365d','ingresos_365d','dias_desde_ultima','rehab_365d','primera_etapa']
tr = df[df.llegada < '2025-01-01']; va = df[(df.llegada >= '2025-01-01') & (df.llegada < '2026-01-01')]; te = df[df.llegada >= '2026-01-01']
out = {}
def fit(X, y, Xv, yv, obj):
    m = lgb.LGBMClassifier(n_estimators=2000, learning_rate=0.05, num_leaves=63, min_child_samples=100, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, random_state=42, deterministic=True, force_row_wise=True) if obj=='bin' else \
        lgb.LGBMRegressor(objective='l1', n_estimators=2000, learning_rate=0.05, num_leaves=63, min_child_samples=100, verbose=-1, random_state=42, deterministic=True, force_row_wise=True)
    m.fit(X, y, eval_set=[(Xv, yv)], callbacks=[lgb.early_stopping(100, verbose=False)])
    return m
# 1) ingreso a hospitalizacion desde la llegada a urgencias
m1 = fit(tr[base], tr.ingresa, va[base], va.ingresa, 'bin')
p = m1.predict_proba(te[base])[:,1]
out['ingreso'] = dict(n_test=len(te), prevalencia=float(te.ingresa.mean()), auc=float(roc_auc_score(te.ingresa,p)), ap=float(average_precision_score(te.ingresa,p)),
    importancia=dict(sorted(zip(base, m1.booster_.feature_importance('gain').round().tolist()), key=lambda x:-x[1])))
# 2) espera hasta piso > 24h (solo ingresados)
ad = lambda d: d[d.ingresa]
f2 = base
m2 = fit(ad(tr)[f2], ad(tr).h_en_urg>24, ad(va)[f2], ad(va).h_en_urg>24, 'bin')
p2 = m2.predict_proba(ad(te)[f2])[:,1]
out['espera_piso_mas24h'] = dict(n_test=int(len(ad(te))), prevalencia=float((ad(te).h_en_urg>24).mean()), auc=float(roc_auc_score(ad(te).h_en_urg>24,p2)),
    importancia=dict(sorted(zip(f2, m2.booster_.feature_importance('gain').round().tolist()), key=lambda x:-x[1])))
# 3) estancia hospitalaria (dias) - regresion L1 al momento del ingreso a piso
m3 = fit(ad(tr)[f2+['h_en_urg']], ad(tr).d_estancia_hosp, ad(va)[f2+['h_en_urg']], ad(va).d_estancia_hosp, 'reg')
p3 = m3.predict(ad(te)[f2+['h_en_urg']])
out['estancia_dias'] = dict(mae=float(mean_absolute_error(ad(te).d_estancia_hosp,p3)), mae_baseline_mediana=float(mean_absolute_error(ad(te).d_estancia_hosp, np.full(len(p3), ad(tr).d_estancia_hosp.median()))))
json.dump(out, open('derived/model_results.json','w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
