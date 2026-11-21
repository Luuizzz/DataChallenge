# Modelo a las 3 h de la llegada (pacientes que siguen en urgencias): diagnosticos y laboratorios disponibles hasta ese momento
import duckdb, os, numpy as np, pandas as pd, lightgbm as lgb, json
from sklearn.metrics import roc_auc_score, average_precision_score
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect(); con.execute("SET threads=12; SET memory_limit='10GB'")
con.execute("CREATE OR REPLACE TABLE coh AS SELECT * FROM feat WHERE h_en_urg >= 3")
con.execute("""CREATE OR REPLACE TABLE dx3 AS SELECT k.episode_id, c.condition_concept_id cid FROM coh k
  JOIN 'condition_occurrence.parquet' c USING (visit_occurrence_id)
  WHERE c.condition_start_datetime BETWEEN k.llegada - INTERVAL 1 HOUR AND k.llegada + INTERVAL 3 HOUR AND c.condition_concept_id<>0 AND c.condition_concept_id IN (SELECT concept_id FROM 'concept.parquet' WHERE domain_id='Condition' AND NOT regexp_matches(lower(concept_name),'cesarean|delivery|deliveries|labor|labour|pregnan|appendectomy|section'))""")
con.execute("""CREATE OR REPLACE TABLE lab3 AS SELECT k.episode_id, m.measurement_concept_id cid, m.value_as_number v, m.measurement_datetime t FROM coh k
  JOIN 'measurement.parquet' m USING (visit_occurrence_id)
  WHERE m.measurement_datetime BETWEEN k.llegada - INTERVAL 1 HOUR AND k.llegada + INTERVAL 3 HOUR""")
top_dx = [r[0] for r in con.execute("SELECT cid FROM dx3 GROUP BY 1 ORDER BY count(DISTINCT episode_id) DESC, cid LIMIT 150").fetchall()]
top_lab = [r[0] for r in con.execute("SELECT cid FROM lab3 GROUP BY 1 ORDER BY count(DISTINCT episode_id) DESC, cid LIMIT 30").fetchall()]
dxw = con.execute(f"SELECT episode_id, cid FROM dx3 WHERE cid IN ({','.join(map(str,top_dx))})").df()
dxw = pd.crosstab(dxw.episode_id, dxw.cid).clip(upper=1).add_prefix('dx_')
labw = con.execute(f"""SELECT episode_id, cid, count(*) n, arg_min(v, (t, v)) v0 FROM lab3 WHERE cid IN ({','.join(map(str,top_lab))}) GROUP BY 1,2""").df()
labn = labw.pivot(index='episode_id', columns='cid', values='n').add_prefix('labn_')
labv = labw.pivot(index='episode_id', columns='cid', values='v0').add_prefix('labv_')
agg = con.execute("""SELECT k.episode_id, (SELECT count(*) FROM dx3 d WHERE d.episode_id=k.episode_id) n_dx3,
   (SELECT count(*) FROM lab3 l WHERE l.episode_id=k.episode_id) n_lab3 FROM coh k""").df().set_index('episode_id')
df = con.execute("SELECT * FROM coh").df().set_index('episode_id').sort_index()
df = df.join(agg).join(dxw).join(labn).join(labv)
for c in [c for c in df.columns if c.startswith('dx_') or c.startswith('labn_')]: df[c] = df[c].fillna(0)
df['sexo'] = df['sexo'].astype('category'); df['primera_etapa'] = df['primera_etapa'].astype('category')
base = ['edad','sexo','hora','dow','mes','censo_urg','censo_hosp','urg_30d','urg_365d','ingresos_365d','dias_desde_ultima','rehab_365d','primera_etapa']
clin = ['n_dx3','n_lab3'] + [c for c in df.columns if c[:3] in ('dx_','lab')]
tr = df[df.llegada < '2025-01-01']; va = df[(df.llegada >= '2025-01-01') & (df.llegada < '2026-01-01')]; te = df[df.llegada >= '2026-01-01']
names = dict(con.execute("SELECT concept_id, concept_name FROM 'concept.parquet'").fetchall())
def lbl(f):
    for p in ('dx_','labn_','labv_'):
        if f.startswith(p): return p + names.get(int(f[len(p):]), f)[:60]
    return f
out = {'cohorte': 'episodios de urgencias que siguen en urgencias a las 3 h de la llegada', 'n_total': len(df), 'n_test': len(te), 'prevalencia_test': float(te.ingresa.mean())}
for nombre, feats in [('solo_llegada', base), ('llegada+clinica_3h', base+clin)]:
    m = lgb.LGBMClassifier(n_estimators=3000, learning_rate=0.03, num_leaves=63, min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.5, verbose=-1, random_state=42, deterministic=True, force_row_wise=True)
    m.fit(tr[feats], tr.ingresa, eval_set=[(va[feats], va.ingresa)], callbacks=[lgb.early_stopping(150, verbose=False)])
    p = m.predict_proba(te[feats])[:,1]
    pd.DataFrame({'y': te.ingresa.astype(int).values, 'p': p}).to_parquet(f"derived/pred_3h_{os.path.basename(__file__)[:3]}_{nombre.replace('+','_')}.parquet")
    imp = sorted(zip(feats, m.booster_.feature_importance('gain')), key=lambda x:-x[1])[:20]
    out[nombre] = dict(auc=round(float(roc_auc_score(te.ingresa,p)),4), ap=round(float(average_precision_score(te.ingresa,p)),4),
                       top_variables=[(lbl(f), int(g)) for f,g in imp])
    if nombre != 'solo_llegada':
        te_ = te.assign(p=p); te_['decil'] = pd.qcut(te_.p.rank(method='first'), 10, labels=False)+1
        out[nombre]['tasa_ingreso_por_decil'] = te_.groupby('decil').ingresa.mean().round(3).tolist()
# sensibilidad a posible fuga residual: los diagnosticos pueden registrarse en lote al ingreso
dxc = [c for c in clin if c.startswith('dx_')]
for nombre, feats in [('sin_n_dx', [f for f in base + clin if f != 'n_dx3']),
                      ('sin_diagnosticos', [f for f in base + clin if f != 'n_dx3' and f not in dxc])]:
    m = lgb.LGBMClassifier(n_estimators=3000, learning_rate=0.03, num_leaves=63, min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.5, verbose=-1, random_state=42, deterministic=True, force_row_wise=True)
    m.fit(tr[feats], tr.ingresa, eval_set=[(va[feats], va.ingresa)], callbacks=[lgb.early_stopping(150, verbose=False)])
    p = m.predict_proba(te[feats])[:,1]
    out.setdefault('sensibilidad_fuga', {})[nombre] = dict(auc=round(float(roc_auc_score(te.ingresa, p)), 4), ap=round(float(average_precision_score(te.ingresa, p)), 4))
json.dump(out, open('derived/model_3h_sin_fuga.json','w'), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
