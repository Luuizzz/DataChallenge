import duckdb, os, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect()
plt.rcParams.update({'figure.dpi':120,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
nombres = {'Referral to trauma and orthopaedics surgery service':'Ortopedia/trauma','Seen by urology service':'Urología','Anesthesia consultation':'Anestesia',
 'Seen by general surgery service':'Cirugía general','Seen by psychiatrist':'Psiquiatría','Specialized medical examination':'Examen especializado',
 'Other consultation':'Otra interconsulta','Emergency department Consult note':'Nota de interconsulta urg.','Seen by hospital-based dietetics service':'Nutrición',
 'Referral to obstetrics and gynecology service':'Ginecobstetricia','Referral to pediatrician':'Pediatría'}
d = con.execute(open(SQL_DIR / '12_interc_fix.sql', encoding='utf-8').read().split(';')[-2]).df()
d['nombre'] = d.servicio.map(nombres).fillna(d.servicio); d = d.sort_values('med_con')
fig, ax = plt.subplots(figsize=(8,4.5))
ax.barh(d.nombre, d.med_sin, color='#c9d3e0', label='sin esa interconsulta'); ax.scatter(d.med_con, d.nombre, color='#c0392b', zorder=3, label='con esa interconsulta')
ax.set_xlabel('mediana de horas desde llegada hasta hospitalización (ingresados)'); ax.legend(frameon=False, loc='lower right')
ax.set_title('Las interconsultas quirúrgicas son las que más retrasan el ingreso'); fig.tight_layout(); fig.savefig('figs/05_interconsultas.png'); plt.close(fig)
p = pd.read_parquet('derived/pronostico_censo_3h_test.parquet'); w = p.loc['2026-03-01':'2026-03-21']
fig, ax = plt.subplots(figsize=(10,3.8)); ax.plot(w.index, w.real, color='#34495e', lw=1, label='censo real'); ax.plot(w.index, w.pred_3h, color='#e67e22', lw=1, label='pronóstico hecho 3 h antes')
ax.axhline(287, color='#c0392b', ls='--', lw=1); ax.text(w.index[0], 290, 'umbral de saturación (p90)', color='#c0392b', fontsize=9)
ax.set_ylabel('pacientes en urgencias'); ax.legend(frameon=False, loc='lower right'); ax.set_title('Alerta de congestión: pronóstico a 3 h (marzo 2026, datos de prueba)')
fig.tight_layout(); fig.savefig('figs/06_pronostico_censo.png'); plt.close(fig)
print('ok')
