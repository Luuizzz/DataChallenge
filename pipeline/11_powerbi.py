# Tablas AGREGADAS para Power BI (sin datos por paciente). Grupos con n < 10 se suprimen.
import duckdb, os, json, pandas as pd
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect, SQL_DIR
setup()
con = connect()
OUT = 'powerbi'
os.makedirs(OUT, exist_ok=True)


def save(name, sql):
    df = con.execute(sql).df()
    df.to_csv(f'{OUT}/{name}.csv', index=False, encoding='utf-8')
    print(f'{name:28s} {len(df):>7} filas')
    return df


def save_df(name, df):
    df.to_csv(f'{OUT}/{name}.csv', index=False, encoding='utf-8')
    print(f'{name:28s} {len(df):>7} filas')


FIN = "'2026-05-01'"
INI = "'2023-01-15'"

save('dim_fecha', f"""
SELECT d::DATE fecha, year(d) anio, month(d) mes, strftime(d,'%Y-%m') anio_mes, isodow(d) dia_semana_num,
  ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][isodow(d)] dia_semana, (isodow(d)>=6) fin_de_semana
FROM generate_series(TIMESTAMP {INI}, TIMESTAMP {FIN} - INTERVAL 1 DAY, INTERVAL 1 DAY) t(d)""")

save('f_hora', f"""
WITH lleg AS (SELECT date_trunc('hour', llegada) hr, count(*) llegadas_total, count(*) FILTER (WHERE h_en_urg>=0.25) llegadas_15min,
                     count(*) FILTER (WHERE ingresa) llegadas_que_ingresan FROM ed GROUP BY 1),
ing AS (SELECT date_trunc('hour', t0) hr, count(*) ingresos_hosp FROM ip_merged GROUP BY 1),
alt AS (SELECT date_trunc('hour', t1) hr, count(*) altas_hosp FROM ip_merged GROUP BY 1)
SELECT c.hr fecha_hora, c.hr::DATE fecha, hour(c.hr) hora, c.censo censo_urgencias, cs.censo_hosp censo_hospitalizacion,
  coalesce(l.llegadas_total,0) llegadas_total, coalesce(l.llegadas_15min,0) llegadas_15min, coalesce(l.llegadas_que_ingresan,0) llegadas_que_ingresan,
  coalesce(i.ingresos_hosp,0) ingresos_hosp, coalesce(a.altas_hosp,0) altas_hosp, (c.censo > 287) saturado_urgencias
FROM census_ed15 c LEFT JOIN census cs USING (hr) LEFT JOIN lleg l USING (hr) LEFT JOIN ing i USING (hr) LEFT JOIN alt a USING (hr)
WHERE c.hr >= {INI} AND c.hr < {FIN} ORDER BY 1""")

p = pd.read_parquet('derived/pronostico_censo_3h_test.parquet').reset_index()
p.columns = ['fecha_hora_objetivo', 'censo_real', 'censo_pronosticado_3h']
p['umbral_saturacion'] = 287
p['alerta'] = p.censo_pronosticado_3h > 287
p['saturado_real'] = p.censo_real > 287
save_df('f_pronostico_3h', p)

save('f_kpi_mensual', f"""
SELECT strftime(llegada,'%Y-%m') anio_mes, count(*) FILTER (WHERE h_en_urg>=0.25) episodios_urg_15min, count(*) FILTER (WHERE ingresa) ingresos,
  round(100*avg(ingresa::INT),2) tasa_ingreso_pct,
  round(quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa),1) mediana_h_hasta_hosp,
  round(quantile_cont(h_en_urg,0.9) FILTER (WHERE ingresa),1) p90_h_hasta_hosp,
  round(100*avg((h_en_urg>24)::INT) FILTER (WHERE ingresa),1) pct_ingresados_mas24h,
  round(100*avg((h_en_urg<=4)::INT) FILTER (WHERE h_en_urg>=0.25),1) pct_urg_resuelto_4h,
  round(100*avg((h_en_urg>12)::INT) FILTER (WHERE h_en_urg>=0.25),1) pct_urg_mas12h,
  round(quantile_cont(d_estancia_hosp,0.5) FILTER (WHERE ingresa),2) mediana_estancia_dias
FROM ed WHERE llegada >= {INI} AND llegada < {FIN} GROUP BY 1 ORDER BY 1""")

save('f_espera_hora_dia', f"""
SELECT hour(llegada) hora_llegada, isodow(llegada) dia_semana_num, count(*) ingresados,
  round(quantile_cont(h_en_urg,0.5),1) mediana_h_hasta_hosp, round(quantile_cont(h_en_urg,0.9),1) p90_h_hasta_hosp,
  round(100*avg((h_en_urg>24)::INT),1) pct_mas24h
FROM ed WHERE ingresa AND llegada >= {INI} AND llegada < {FIN} GROUP BY 1,2 HAVING count(*)>=10 ORDER BY 1,2""")

save('f_altas_ingresos_hora', """
SELECT h hora, sum(i) ingresos_hosp, sum(a) altas_hosp
FROM (SELECT hour(t0) h, 1 i, 0 a FROM ip_merged UNION ALL SELECT hour(t1), 0, 1 FROM ip_merged) GROUP BY 1 ORDER BY 1""")

save('f_edad', f"""
SELECT CASE WHEN edad<15 THEN '0-14' WHEN edad<45 THEN '15-44' WHEN edad<65 THEN '45-64' WHEN edad<80 THEN '65-79' ELSE '80+' END grupo_edad,
  count(*) FILTER (WHERE h_en_urg>=0.25) episodios_15min, round(100*avg(ingresa::INT),1) tasa_ingreso_pct,
  round(quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa),1) mediana_h_hasta_hosp
FROM ed WHERE llegada >= {INI} AND llegada < {FIN} AND edad IS NOT NULL GROUP BY 1 ORDER BY 1""")

nombres = {
    'Referral to trauma and orthopaedics surgery service': 'Ortopedia/trauma', 'Seen by urology service': 'Urología',
    'Anesthesia consultation': 'Anestesia', 'Seen by general surgery service': 'Cirugía general',
    'Seen by psychiatrist': 'Psiquiatría', 'Specialized medical examination': 'Examen especializado',
    'Other consultation': 'Otra interconsulta', 'Emergency department Consult note': 'Nota de interconsulta urgencias',
    'Seen by hospital-based dietetics service': 'Nutrición', 'Referral to obstetrics and gynecology service': 'Ginecobstetricia',
    'Referral to pediatrician': 'Pediatría'}
ic = con.execute(open(SQL_DIR / '12_interc_fix.sql', encoding='utf-8').read().split(';')[-2]).df()
ic['servicio'] = ic.servicio.map(nombres).fillna(ic.servicio)
ic['diferencia_h'] = (ic.med_con - ic.med_sin).round(1)
ic = ic.rename(columns={'n_con': 'ingresados_con_interconsulta', 'med_con': 'mediana_h_con', 'med_sin': 'mediana_h_sin', 'edad_con': 'edad_media_con'})
save_df('f_interconsultas', ic)

save('f_n_servicios', """
SELECT least(coalesce(k.n_svc,0),5) n_servicios, count(*) ingresados,
  round(quantile_cont(a.h_en_urg,0.5),1) mediana_h_hasta_hosp, round(quantile_cont(a.h_en_urg,0.9),1) p90_h
FROM ep1 a LEFT JOIN (SELECT visit_occurrence_id, count(*) n_svc FROM svc GROUP BY 1) k USING (visit_occurrence_id)
WHERE a.ingresa GROUP BY 1 ORDER BY 1""")

save('f_flujo_transiciones', f"""
WITH o AS (SELECT etapa, lead(etapa) OVER (PARTITION BY visit_occurrence_id, ep_num ORDER BY t0, visit_detail_id) sig, t0 FROM stage_ep),
m AS (SELECT
  CASE etapa WHEN 'ER' THEN 'Registro o triage' WHEN 'TRIAGE' THEN 'Atención en urgencias'
             WHEN 'IP' THEN 'Hospitalización' ELSE 'Rehabilitación ambulatoria' END origen,
  CASE coalesce(sig,'FIN') WHEN 'ER' THEN 'Registro o triage' WHEN 'TRIAGE' THEN 'Atención en urgencias'
             WHEN 'IP' THEN 'Hospitalización' WHEN 'FIN' THEN 'Egreso' ELSE 'Rehabilitación ambulatoria' END destino
  FROM o WHERE t0 >= {INI} AND t0 < {FIN})
SELECT origen, destino, count(*) n FROM m WHERE origen <> destino OR destino='Egreso' GROUP BY 1,2 HAVING count(*)>=10 ORDER BY 3 DESC""")

ETQ = {'base': 'Línea base', 'altas_am_30pct': 'Altas a.m. 30 %', 'altas_am_50pct': 'Altas a.m. 50 %',
       'interconsulta_quir_-25pct': 'Interconsultas quir. −25 %', 'interconsulta_quir_-50pct': 'Interconsultas quir. −50 %',
       'combinado_altas30_quir25': 'Combinado 30 % / −25 %', 'combinado_altas50_quir50': 'Combinado 50 % / −50 %',
       'referencia_+10_camas': 'Referencia: +10 camas'}
se_ = pd.read_csv('derived/simulacion_escenarios.csv')
se_['escenario'] = se_.escenario.map(ETQ)
se_ = se_[['escenario', 'mediana_h', 'p90_h', 'pct_mas24h', 'espera_cama_mediana_h', 'delta_mediana_h', 'delta_p90_h', 'horas_paciente_ahorradas_anio', 'censo_esperando_cama']]
save_df('f_simulacion_escenarios', se_)
save_df('f_simulacion_sensibilidad', pd.read_csv('derived/simulacion_sensibilidad.csv'))

m3 = json.load(open('derived/model_3h_sin_fuga.json', encoding='utf-8'))
al = json.load(open('derived/alerta_congestion.json', encoding='utf-8'))
save_df('f_modelo_ingreso_deciles', pd.DataFrame({'decil_riesgo': range(1, 11), 'tasa_ingreso_real': m3['llegada+clinica_3h']['tasa_ingreso_por_decil']}))
filas = [dict(modelo='Ingreso a hospitalización (a las 3 h)', metrica='AUC', valor=m3['llegada+clinica_3h']['auc']),
         dict(modelo='Ingreso a hospitalización (a las 3 h)', metrica='AP', valor=m3['llegada+clinica_3h']['ap'])]
filas += [dict(modelo=f'Alerta congestión a {h[1]} h', metrica=k, valor=v) for h in ['h1', 'h2', 'h3'] for k, v in al[h].items()]
inc = json.load(open('derived/incertidumbre.json', encoding='utf-8'))
mi, a3 = inc['ingreso_llegada_clinica_3h'], inc['alerta_3h']
filas += [dict(modelo='Ingreso a hospitalización (a las 3 h)', metrica='AUC IC95 inferior', valor=mi['auc_ic95'][0]),
          dict(modelo='Ingreso a hospitalización (a las 3 h)', metrica='AUC IC95 superior', valor=mi['auc_ic95'][1]),
          dict(modelo='Ingreso a hospitalización (a las 3 h)', metrica='Brier (referencia ' + str(mi['brier_referencia']) + ')', valor=mi['brier']),
          dict(modelo='Alerta congestión a 3 h', metrica='precisión IC95 inferior', valor=a3['precision_ic95'][0]),
          dict(modelo='Alerta congestión a 3 h', metrica='precisión IC95 superior', valor=a3['precision_ic95'][1]),
          dict(modelo='Alerta congestión a 3 h', metrica='recall IC95 inferior', valor=a3['recall_ic95'][0]),
          dict(modelo='Alerta congestión a 3 h', metrica='recall IC95 superior', valor=a3['recall_ic95'][1])]
save_df('f_modelos_metricas', pd.DataFrame(filas))

save_df('f_calidad_datos', pd.DataFrame([
    ('Saltos de ~16 días dentro de una visita', '44 % de visitas con etapas', 'Se parte en episodios si el hueco > 7 días'),
    ('visit_end_datetime = inicio', '100 % de visitas', 'Duraciones calculadas con visit_detail'),
    ('procedure_date vacío', '47 M filas', 'Procedimientos usados solo a nivel de visita'),
    ('Episodios de urgencias < 15 min', '64 % de no ingresados', 'Métricas sobre episodios >= 15 min'),
    ('Diagnósticos con fecha 2027-2033', '76 filas, sin visita', 'Excluidos'),
    ('Mediciones duplicadas SNOMED/LOINC', 'muchos analitos', 'Deduplicar antes de contar'),
    ('Diagnósticos sin concepto (0)', '14,6 M filas (38 %)', 'Excluidos de variables clínicas'),
    ('provider_id constante', '1 valor', 'No usado'),
    ('Caídas bruscas de censo (cierres por lotes)', 'varios días', 'Señalado; pendiente de confirmar'),
    ('Mayo-julio 2026 incompleto', 'volumen cae a la mitad', 'Excluido de tendencias'),
], columns=['problema', 'alcance', 'tratamiento']))
print('ok')

# ---- tablas de rigor y robustez (pagina 6) ----
ia = pd.read_csv('derived/interconsultas_ajustado.csv')
NOMB = {'ortopedia': 'Ortopedia/trauma', 'urologia': 'Urología', 'nota_interconsulta_urg': 'Nota de interconsulta urg.', 'cirugia': 'Cirugía general',
        'psiquiatria': 'Psiquiatría', 'examen_especializado': 'Examen especializado', 'anestesia': 'Anestesia', 'nutricion': 'Nutrición',
        'otra_interconsulta': 'Otra interconsulta', 'ginecobstetricia': 'Ginecobstetricia', 'pediatria': 'Pediatría'}
ia['servicio'] = ia.servicio.map(NOMB)
save_df('f_interconsultas_ajustado', ia[['servicio', 'n', 'crudo_h', 'ajustado_h', 'ic95_inf', 'ic95_sup']])
rig = json.load(open('derived/modelo_ingreso_rigor.json', encoding='utf-8'))
filas = [dict(modelo=f'LightGBM a {w}', auc=v['auc'], ic95_inf=v['auc_ic95'][0], ic95_sup=v['auc_ic95'][1], orden=i) for i, (w, v) in enumerate(rig['ventanas'].items())]
filas.append(dict(modelo='Logística a 3h', auc=rig['logistica_3h']['auc'], ic95_inf=rig['logistica_3h']['auc_ic95'][0], ic95_sup=rig['logistica_3h']['auc_ic95'][1], orden=3))
save_df('f_modelo_ventanas', pd.DataFrame(filas))
dec = rig['decision_top20']
save_df('f_decision', pd.DataFrame([
    dict(metrica='Ingresos anticipados por día', valor=dec['ingresos_anticipados_por_dia'], orden=1),
    dict(metrica='Horas de antelación (mediana)', valor=dec['horas_de_anticipacion_mediana'], orden=2),
    dict(metrica='% de marcados que ingresa', valor=round(100 * dec['ppv'], 1), orden=3),
    dict(metrica='% de ingresos captados', valor=round(100 * dec['sensibilidad'], 1), orden=4),
    dict(metrica='Pacientes marcados por día', valor=dec['marcados_por_dia'], orden=5)]))
val = pd.read_csv('derived/validacion_simulacion_2026.csv')
rec = json.load(open('derived/recalibracion_2026.json', encoding='utf-8'))
NI = {'mediana': 'Mediana (h)', 'dia': 'Llegada de día (h)', 'madrugada': 'Llegada de madrugada (h)', 'pct24': '% > 24 h'}
save_df('f_validacion_2026', pd.DataFrame([dict(indicador=NI[r.indicador], observado_2026=r.observado_2026, simulado_C269=r.simulado,
                                                simulado_C260=rec['ajuste_2026'][r.indicador]) for r in val.itertuples()]))
print('ok rigor')
