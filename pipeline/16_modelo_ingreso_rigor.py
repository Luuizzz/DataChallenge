"""Rigor del modelo de ingreso:
 (1) sensibilidad a la ventana de prediccion (1, 3 y 6 h tras la llegada),
 (2) comparacion con una regresion logistica interpretable,
 (3) explicabilidad (contribuciones SHAP de LightGBM),
 (4) analisis de decision operativo: si se marca el 20 % de mayor riesgo, cuantos ingresos se anticipan y con cuantas horas.
Mismas reglas que 05b: sin diagnosticos con riesgo de fuga, particion temporal 2023-24 / 2025 / ene-abr 2026."""
import duckdb, os, json, numpy as np, pandas as pd, lightgbm as lgb
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect(); con.execute("SET threads=12; SET memory_limit='10GB'")
EXCL = "cesarean|delivery|deliveries|labor|labour|pregnan|appendectomy|section"
BASE = ['edad', 'sexo', 'hora', 'dow', 'mes', 'censo_urg', 'censo_hosp', 'urg_30d', 'urg_365d', 'ingresos_365d', 'dias_desde_ultima', 'rehab_365d', 'primera_etapa']
rng = np.random.default_rng(7)


def build(W):
    con.execute(f"CREATE OR REPLACE TABLE cohw AS SELECT * FROM feat WHERE h_en_urg >= {W}")
    con.execute(f"""CREATE OR REPLACE TABLE dxw AS SELECT k.episode_id, c.condition_concept_id cid FROM cohw k
      JOIN 'condition_occurrence.parquet' c USING (visit_occurrence_id)
      WHERE c.condition_start_datetime BETWEEN k.llegada - INTERVAL 1 HOUR AND k.llegada + INTERVAL {W} HOUR AND c.condition_concept_id<>0
        AND c.condition_concept_id IN (SELECT concept_id FROM 'concept.parquet' WHERE domain_id='Condition' AND NOT regexp_matches(lower(concept_name),'{EXCL}'))""")
    con.execute(f"""CREATE OR REPLACE TABLE labw AS SELECT k.episode_id, m.measurement_concept_id cid, m.value_as_number v, m.measurement_datetime t FROM cohw k
      JOIN 'measurement.parquet' m USING (visit_occurrence_id)
      WHERE m.measurement_datetime BETWEEN k.llegada - INTERVAL 1 HOUR AND k.llegada + INTERVAL {W} HOUR""")
    top_dx = [r[0] for r in con.execute("SELECT cid FROM dxw GROUP BY 1 ORDER BY count(DISTINCT episode_id) DESC, cid LIMIT 150").fetchall()]
    top_lab = [r[0] for r in con.execute("SELECT cid FROM labw GROUP BY 1 ORDER BY count(DISTINCT episode_id) DESC, cid LIMIT 30").fetchall()]
    dx = con.execute(f"SELECT episode_id, cid FROM dxw WHERE cid IN ({','.join(map(str, top_dx))})").df()
    dx = pd.crosstab(dx.episode_id, dx.cid).clip(upper=1).add_prefix('dx_')
    lab = con.execute(f"SELECT episode_id, cid, count(*) n, arg_min(v, (t, v)) v0 FROM labw WHERE cid IN ({','.join(map(str, top_lab))}) GROUP BY 1,2").df()
    labn = lab.pivot(index='episode_id', columns='cid', values='n').add_prefix('labn_')
    labv = lab.pivot(index='episode_id', columns='cid', values='v0').add_prefix('labv_')
    agg = con.execute("""SELECT k.episode_id, (SELECT count(*) FROM dxw d WHERE d.episode_id=k.episode_id) n_dx,
        (SELECT count(*) FROM labw l WHERE l.episode_id=k.episode_id) n_lab FROM cohw k""").df().set_index('episode_id')
    df = con.execute("SELECT * FROM cohw").df().set_index('episode_id').sort_index()
    df = pd.concat([df, agg, dx, labn, labv], axis=1, join='outer').loc[df.index].copy()
    for c in [c for c in df.columns if c.startswith('dx_') or c.startswith('labn_')]:
        df[c] = df[c].fillna(0)
    df['sexo'] = df['sexo'].astype('category'); df['primera_etapa'] = df['primera_etapa'].astype('category')
    clin = ['n_dx', 'n_lab'] + [c for c in df.columns if c[:3] in ('dx_', 'lab')]
    return df, clin


def split(df):
    return df[df.llegada < '2025-01-01'], df[(df.llegada >= '2025-01-01') & (df.llegada < '2026-01-01')], df[df.llegada >= '2026-01-01']


def lgbm(tr, va, feats):
    m = lgb.LGBMClassifier(n_estimators=3000, learning_rate=0.03, num_leaves=63, min_child_samples=50, subsample=0.8, subsample_freq=1,
                           colsample_bytree=0.5, verbose=-1, random_state=1, deterministic=True, force_row_wise=True)
    m.fit(tr[feats], tr.ingresa, eval_set=[(va[feats], va.ingresa)], callbacks=[lgb.early_stopping(150, verbose=False)])
    return m


def auc_ci(y, p, B=300):
    v = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        v.append(roc_auc_score(y[i], p[i]))
    return [round(float(np.quantile(v, .025)), 3), round(float(np.quantile(v, .975)), 3)]


out = {"ventanas": {}}
names = dict(con.execute("SELECT concept_id, concept_name FROM 'concept.parquet'").fetchall())
for W in [1, 3, 6]:
    df, clin = build(W)
    tr, va, te = split(df)
    feats = BASE + clin
    m = lgbm(tr, va, feats)
    p = m.predict_proba(te[feats])[:, 1]; y = te.ingresa.astype(int).values
    out["ventanas"][f"{W}h"] = dict(n_test=int(len(te)), prevalencia=round(float(y.mean()), 3), auc=round(float(roc_auc_score(y, p)), 3),
                                    auc_ic95=auc_ci(y, p), ap=round(float(average_precision_score(y, p)), 3))
    print(W, out["ventanas"][f"{W}h"], flush=True)
    if W == 3:
        # (2) regresion logistica interpretable con las mismas variables
        num = [c for c in feats if c not in ('sexo', 'primera_etapa')]
        def prep(d):
            X = d[num].copy()
            X['sexo_f'] = (d.sexo.astype(str) == '8532').astype(int)
            for e in ['ER', 'TRIAGE', 'REHAB']:
                X['primera_' + e] = (d.primera_etapa.astype(str) == e).astype(int)
            return X
        lr = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), LogisticRegression(max_iter=2000, C=0.1))
        lr.fit(prep(tr), tr.ingresa.astype(int))
        pl = lr.predict_proba(prep(te))[:, 1]
        out["logistica_3h"] = dict(auc=round(float(roc_auc_score(y, pl)), 3), auc_ic95=auc_ci(y, pl), ap=round(float(average_precision_score(y, pl)), 3))
        # (3) explicabilidad: contribuciones SHAP medias absolutas
        contrib = m.predict(te[feats], pred_contrib=True)[:, :-1]
        imp = pd.Series(np.abs(contrib).mean(0), index=feats).sort_values(ascending=False).head(15)
        def lbl(f):
            for pref, txt in (('dx_', 'Diagnóstico: '), ('labn_', 'N.º de pruebas: '), ('labv_', 'Valor: ')):
                if f.startswith(pref):
                    return txt + names.get(int(f[len(pref):]), f)[:50]
            return f
        out["shap_top15"] = [(lbl(f), round(float(v), 4)) for f, v in imp.items()]
        # (4) analisis de decision: marcar el 20 % de mayor riesgo
        te2 = te.assign(p=p)
        thr = np.quantile(p, 0.8)
        flag = te2.p >= thr
        tp = te2[flag & (te2.ingresa)]
        dias = (te2.llegada.max() - te2.llegada.min()).days + 1
        out["decision_top20"] = dict(
            umbral_prob=round(float(thr), 3), ppv=round(float(te2[flag].ingresa.mean()), 3), sensibilidad=round(float(flag[te2.ingresa].mean()), 3),
            marcados_por_dia=round(float(flag.sum() / dias), 1), ingresos_anticipados_por_dia=round(float(len(tp) / dias), 1),
            horas_de_anticipacion_mediana=round(float((tp.h_en_urg - 3).median()), 1),
            horas_de_anticipacion_p25_p75=[round(float((tp.h_en_urg - 3).quantile(q)), 1) for q in (0.25, 0.75)])
        print(out["logistica_3h"], out["decision_top20"], flush=True)
json.dump(out, open("derived/modelo_ingreso_rigor.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
