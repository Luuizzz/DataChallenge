# Figura de escenarios de la simulacion (agregada): delta de mediana y p90 por escenario
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup
setup()
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
ETQ = {'altas_am_30pct': 'Altas a.m. 30 %', 'altas_am_50pct': 'Altas a.m. 50 %', 'interconsulta_quir_-25pct': 'Interconsultas quir. −25 %',
       'interconsulta_quir_-50pct': 'Interconsultas quir. −50 %', 'combinado_altas30_quir25': 'Combinado 30 % / −25 %',
       'combinado_altas50_quir50': 'Combinado 50 % / −50 %', 'referencia_+10_camas': 'Referencia: +10 camas'}
d = pd.read_csv('derived/simulacion_escenarios.csv')
d = d[d.escenario.isin(ETQ)].assign(nombre=lambda x: x.escenario.map(ETQ)).sort_values('delta_p90_h', ascending=False)
fig, ax = plt.subplots(figsize=(10.8, 4.8), dpi=100)
y = range(len(d))
ax.barh([i + 0.2 for i in y], d.delta_mediana_h, height=0.4, color='#0F7C8C', label='Δ mediana (h)')
ax.barh([i - 0.2 for i in y], d.delta_p90_h, height=0.4, color='#E07A1F', label='Δ percentil 90 (h)')
for i, (m, p) in enumerate(zip(d.delta_mediana_h, d.delta_p90_h)):
    ax.text(m - 0.2, i + 0.2, f"{m:.1f}".replace('.', ','), va='center', ha='right', fontsize=9)
    ax.text(p - 0.2, i - 0.2, f"{p:.1f}".replace('.', ','), va='center', ha='right', fontsize=9)
ax.set_yticks(list(y)); ax.set_yticklabels(d.nombre); ax.set_xlim(-17, 0)
ax.set_xlabel('cambio en horas hasta hospitalización (negativo = menos espera)')
ax.set_title('Escenarios simulados con 269 camas efectivas (30 réplicas por escenario)')
ax.spines[['top', 'right']].set_visible(False); ax.legend(loc='lower left', frameon=False)
plt.tight_layout(); plt.savefig('figs/07_escenarios.png'); print('ok figs/07_escenarios.png')
