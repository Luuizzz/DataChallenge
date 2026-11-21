# Incertidumbre: IC 95 % bootstrap para el modelo de ingreso (3 h) y la alerta de congestion; calibracion; dispersion de la simulacion.
import os, json, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, precision_score, recall_score
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
rng = np.random.default_rng(42)
B = 1000
out = {}

# 1) Modelo de ingreso a las 3 h (bootstrap por paciente-episodio)
for nombre in ['solo_llegada', 'llegada_clinica_3h']:
    d = pd.read_parquet(f'derived/pred_3h_05b_{nombre}.parquet')
    y, p = d.y.values, d.p.values
    aucs, aps = [], []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() == y[i].max():
            continue
        aucs.append(roc_auc_score(y[i], p[i])); aps.append(average_precision_score(y[i], p[i]))
    out[f'ingreso_{nombre}'] = dict(n=len(y), prevalencia=round(float(y.mean()), 3),
        auc=round(float(roc_auc_score(y, p)), 3), auc_ic95=[round(float(np.quantile(aucs, q)), 3) for q in (0.025, 0.975)],
        ap=round(float(average_precision_score(y, p)), 3), ap_ic95=[round(float(np.quantile(aps, q)), 3) for q in (0.025, 0.975)],
        brier=round(float(brier_score_loss(y, p)), 4), brier_referencia=round(float(brier_score_loss(y, np.full(len(y), y.mean()))), 4))
    if nombre == 'llegada_clinica_3h':
        d['decil'] = pd.qcut(d.p.rank(method='first'), 10, labels=False) + 1
        cal = d.groupby('decil').agg(prob_predicha=('p', 'mean'), tasa_real=('y', 'mean'), n=('y', 'size')).round(3).reset_index()
        cal.to_csv('derived/calibracion_modelo_ingreso.csv', index=False)
        out['calibracion_por_decil'] = cal.to_dict('records')

# 2) Alerta de congestion a 3 h (bootstrap por bloques de dia, respeta autocorrelacion horaria)
pr = pd.read_parquet('derived/pronostico_censo_3h_test.parquet')
pr.columns = ['real', 'pred']
pr['dia'] = pr.index.normalize()
U = 287
dias = pr.dia.unique()
grp = {k: g for k, g in pr.groupby('dia')}
precs, recs, maes = [], [], []
for _ in range(B):
    s = pd.concat([grp[k] for k in rng.choice(dias, len(dias))])
    rs, ps = s.real > U, s.pred > U
    if ps.sum() == 0 or rs.sum() == 0:
        continue
    precs.append(precision_score(rs, ps)); recs.append(recall_score(rs, ps)); maes.append(float((s.real - s.pred).abs().mean()))
rs, ps = pr.real > U, pr.pred > U
out['alerta_3h'] = dict(precision=round(float(precision_score(rs, ps)), 3), precision_ic95=[round(float(np.quantile(precs, q)), 3) for q in (0.025, 0.975)],
                        recall=round(float(recall_score(rs, ps)), 3), recall_ic95=[round(float(np.quantile(recs, q)), 3) for q in (0.025, 0.975)],
                        mae=round(float((pr.real - pr.pred).abs().mean()), 2), mae_ic95=[round(float(np.quantile(maes, q)), 2) for q in (0.025, 0.975)],
                        nota='bootstrap por bloques de dia (1000 remuestreos)')
json.dump(out, open('derived/incertidumbre.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in out.items() if k != 'calibracion_por_decil'}, indent=1, ensure_ascii=False))
print(pd.DataFrame(out['calibracion_por_decil']).to_string(index=False))
