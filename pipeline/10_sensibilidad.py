# Sensibilidad: los efectos (deltas) de cada escenario se mantienen si cambian camas efectivas C y fraccion de estudio k?
import importlib.util, os, json, itertools, numpy as np, pandas as pd, sys, io, contextlib
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
src = open(pathlib.Path(__file__).with_name('09_simulacion.py'), encoding='utf-8').read().split('# --- calibracion (grid) ---')[0]
ns = {'__file__': str(pathlib.Path(__file__).with_name('09_simulacion.py'))}; exec(src, ns)
simular, resumen = ns['simular'], ns['resumen']
filas = []
for C, k in itertools.product([249, 259, 269, 279, 289], [0.45, 0.55, 0.65]):
    out = {}
    for nombre, kw in {'base':{}, 'altas_am_30pct':dict(f_alta_am=0.3), 'interconsulta_quir_-50pct':dict(r_quir=0.5), 'combinado_altas50_quir50':dict(f_alta_am=0.5, r_quir=0.5), 'referencia_+10_camas':dict(extra_camas=10)}.items():
        out[nombre] = np.mean([resumen(*simular(C, k, 0.8, seed=200+j, **kw))['med'] for j in range(3)])
    filas.append(dict(C=C, k=k, base_med=round(out['base'],1), **{f'delta_{n}': round(v-out['base'],1) for n, v in out.items() if n!='base'}))
t = pd.DataFrame(filas); print(t.to_string(index=False))
print(t.filter(like='delta').describe().loc[['min','mean','max']].round(1).to_string())
t.to_csv('derived/simulacion_sensibilidad.csv', index=False)
