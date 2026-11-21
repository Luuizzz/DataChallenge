import duckdb, os, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect()
for t in ['episode','stage_ep','ed_c','census']:
    con.execute(f"COPY {t} TO 'derived/{t}.parquet' (FORMAT parquet, COMPRESSION zstd)")
plt.rcParams.update({'figure.dpi':120,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
# 1 hora de llegada: llegadas y tiempo hasta piso
d = con.execute("""SELECT hour(llegada) h, count(*) n, quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa) med_piso,
  quantile_cont(h_en_urg,0.9) FILTER (WHERE ingresa) p90_piso FROM ed_c WHERE llegada<'2026-05-01' GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9,4)); ax.bar(d.h, d.n/1000, color='#c9d3e0'); ax.set_ylabel('llegadas a urgencias (miles)'); ax.set_xlabel('hora de llegada')
ax2 = ax.twinx(); ax2.plot(d.h, d.med_piso, color='#c0392b', marker='o', label='mediana'); ax2.plot(d.h, d.p90_piso, color='#c0392b', ls='--', label='p90')
ax2.set_ylabel('horas desde llegada hasta subir a piso', color='#c0392b'); ax2.legend(loc='upper left', frameon=False); ax2.spines['top'].set_visible(False)
ax.set_title('Pacientes que ingresan: espera hasta piso según la hora de llegada'); fig.tight_layout(); fig.savefig('figs/01_espera_piso_por_hora.png'); plt.close(fig)
# 2 altas vs ingresos a piso por hora
d = con.execute("""SELECT h, sum(i) ingresos, sum(a) altas FROM (SELECT hour(t0) h, 1 i, 0 a FROM ip_int UNION ALL SELECT hour(t1),0,1 FROM ip_int) GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9,4)); w=0.4
ax.bar(d.h-w/2, d.altas/1000, w, label='altas de hospitalización', color='#2e86de'); ax.bar(d.h+w/2, d.ingresos/1000, w, label='ingresos a hospitalización', color='#e67e22')
ax.set_xlabel('hora del día'); ax.set_ylabel('eventos 2023–2026 (miles)'); ax.legend(frameon=False); ax.set_title('Las camas se liberan por la tarde; los ingresos se acumulan de noche')
fig.tight_layout(); fig.savefig('figs/02_altas_vs_ingresos_por_hora.png'); plt.close(fig)
# 3 tendencia mensual
d = con.execute("""SELECT date_trunc('month', hr) m, avg(censo_hosp) hosp, avg(censo_urg) urg FROM census WHERE hr>='2023-02-01' AND hr<'2026-05-01' GROUP BY 1 ORDER BY 1""").df()
e = con.execute("""SELECT date_trunc('month', llegada) m, quantile_cont(h_en_urg,0.9) p90 FROM ed_c WHERE llegada>='2023-02-01' AND llegada<'2026-05-01' GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9,4)); ax.plot(d.m, d.hosp, label='censo medio hospitalización', color='#2e86de'); ax.plot(d.m, d.urg, label='censo medio urgencias', color='#e67e22')
ax.set_ylabel('pacientes simultáneos'); ax2 = ax.twinx(); ax2.plot(e.m, e.p90, color='#7f8c8d', ls=':', label='p90 horas en urgencias'); ax2.set_ylabel('p90 horas en urgencias', color='#7f8c8d')
ax.legend(loc='upper left', frameon=False); ax.set_title('Ocupación y tiempos en urgencias, por mes (hasta abr-2026)'); fig.tight_layout(); fig.savefig('figs/03_tendencia_mensual.png'); plt.close(fig)
# 4 artefacto 16 dias
d = con.execute("""SELECT floor(epoch(t0 - prev_max_end)/86400)::INT dias, count(*) n FROM stage_ep WHERE prev_max_end IS NOT NULL AND t0-prev_max_end > INTERVAL 1 DAY AND t0-prev_max_end < INTERVAL 40 DAY GROUP BY 1 ORDER BY 1""").df()
fig, ax = plt.subplots(figsize=(9,3.5)); ax.bar(d.dias, d.n/1000, color='#8e44ad'); ax.axvline(7, color='k', ls='--', lw=1); ax.text(7.3, ax.get_ylim()[1]*0.8, 'corte de episodio (7 días)')
ax.set_xlabel('días entre etapas consecutivas de una misma visita'); ax.set_ylabel('miles'); ax.set_title('Artefacto: saltos de 15–19 días dentro de la misma visita'); fig.tight_layout(); fig.savefig('figs/04_artefacto_16_dias.png'); plt.close(fig)
print(os.listdir('figs'), os.listdir('derived'))
