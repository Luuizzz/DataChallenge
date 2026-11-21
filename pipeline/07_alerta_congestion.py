# Pronostico del censo de urgencias (episodios >=15 min) a 1, 2 y 3 horas + alerta de saturacion (censo > p90 historico)
import duckdb, os, numpy as np, pandas as pd, lightgbm as lgb, json
from sklearn.metrics import mean_absolute_error, precision_score, recall_score
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect()
con.execute("""
CREATE OR REPLACE TABLE ed15_int AS SELECT llegada t0, coalesce(t_ingreso_hosp, t_fin_urg) t1 FROM ed WHERE h_en_urg >= 0.25 AND h_en_urg <= 240;
CREATE OR REPLACE TABLE census_ed15 AS
WITH ev AS (SELECT t0 t, 1 d FROM ed15_int UNION ALL SELECT t1, -1 FROM ed15_int),
c AS (SELECT t, sum(sum(d)) OVER (ORDER BY t) n FROM ev GROUP BY t),  -- un valor por instante: sin empates
arr AS (SELECT date_trunc('hour', t0) hr, count(*) llegadas FROM ed15_int GROUP BY 1)
SELECT h.hr, coalesce(c.n,0) censo, coalesce(a.llegadas,0) llegadas, cs.censo_hosp
FROM hours h ASOF LEFT JOIN c ON h.hr >= c.t LEFT JOIN arr a ON a.hr=h.hr LEFT JOIN census cs ON cs.hr=h.hr
WHERE h.hr >= '2023-01-15' AND h.hr < '2026-05-01' ORDER BY h.hr;
""")
d = con.execute("SELECT * FROM census_ed15 ORDER BY hr").df().set_index('hr')
X = pd.DataFrame(index=d.index)
for l in [0,1,2,3,6,12,24,48,168]: X[f'censo_l{l}'] = d.censo.shift(l)
for l in [0,1,2]: X[f'lleg_l{l}'] = d.llegadas.shift(l)
X['lleg_3h'] = d.llegadas.rolling(3).sum(); X['lleg_24h'] = d.llegadas.rolling(24).sum()
X['hosp_l0'] = d.censo_hosp; X['hosp_d24'] = d.censo_hosp - d.censo_hosp.shift(24)
X['hora'] = d.index.hour; X['dow'] = d.index.dayofweek; X['mes'] = d.index.month
umbral = float(d.censo[d.index < '2025-01-01'].quantile(0.9))
out = {'definicion': 'censo = pacientes simultaneos en urgencias (episodios de 15 min a 10 dias)', 'umbral_saturacion_p90_2023_2024': umbral,
       'censo_medio_test': float(d.censo[d.index >= '2026-01-01'].mean())}
for h in [1,2,3]:
    y = d.censo.shift(-h)
    m_ok = X.notna().all(axis=1) & y.notna()
    tr = m_ok & (X.index < '2025-01-01'); va = m_ok & (X.index >= '2025-01-01') & (X.index < '2026-01-01'); te = m_ok & (X.index >= '2026-01-01')
    mdl = lgb.LGBMRegressor(n_estimators=3000, learning_rate=0.03, num_leaves=31, min_child_samples=50, objective='l1', verbose=-1, random_state=42, deterministic=True, force_row_wise=True)
    mdl.fit(X[tr], y[tr], eval_set=[(X[va], y[va])], callbacks=[lgb.early_stopping(150, verbose=False)])
    p = mdl.predict(X[te]); yt = y[te]
    pers = X.loc[te, 'censo_l0']; seas = d.censo.shift(24 - h)[te]
    real_sat = yt > umbral; pred_sat = p > umbral
    out[f'h{h}'] = dict(mae_modelo=round(mean_absolute_error(yt,p),2), mae_persistencia=round(mean_absolute_error(yt,pers),2), mae_mismo_hora_ayer=round(mean_absolute_error(yt,seas),2),
        horas_saturadas_test=int(real_sat.sum()), horas_test=int(len(yt)),
        alerta_precision=round(precision_score(real_sat,pred_sat),3), alerta_recall=round(recall_score(real_sat,pred_sat),3),
        persistencia_precision=round(precision_score(real_sat, pers>umbral),3), persistencia_recall=round(recall_score(real_sat, pers>umbral),3))
    if h == 3:
        pd.DataFrame({'real': yt, 'pred_3h': p}).to_parquet('derived/pronostico_censo_3h_test.parquet')
json.dump(out, open('derived/alerta_congestion.json','w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
