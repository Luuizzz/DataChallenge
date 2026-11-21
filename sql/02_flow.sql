CREATE OR REPLACE TABLE ed AS
SELECT e.episode_id, e.visit_occurrence_id, e.person_id, e.tipo_episodio, e.secuencia, e.n_etapas,
  e.has_ip AS ingresa,
  e.t_llegada_urg AS llegada,
  e.t_fin_urg,
  e.t_ingreso_hosp, e.t_alta_hosp,
  epoch(coalesce(e.t_ingreso_hosp, e.t_fin_urg) - e.t_llegada_urg)/3600 AS h_en_urg,      -- hasta salir de urgencias o subir a piso
  epoch(e.t_ingreso_hosp - e.t_fin_urg)/3600 AS h_gap_urg_hosp,
  epoch(e.t_alta_hosp - e.t_ingreso_hosp)/24/3600 AS d_estancia_hosp,
  year(e.t_llegada_urg) - p.year_of_birth AS edad, p.gender_concept_id AS sexo
FROM episode e LEFT JOIN 'person.parquet' p USING (person_id)
WHERE e.tipo_episodio LIKE 'URG%';

SELECT tipo_episodio, count(*) n,
  quantile_cont(h_en_urg,[0.25,0.5,0.75,0.9,0.95]) h_en_urg_q,
  round(avg((h_en_urg>6)::INT)*100,1) pct_mas6h, round(avg((h_en_urg>24)::INT)*100,1) pct_mas24h
FROM ed GROUP BY 1;
SELECT quantile_cont(h_gap_urg_hosp,[0.05,0.25,0.5,0.75,0.95]) gap_q, quantile_cont(d_estancia_hosp,[0.25,0.5,0.75,0.9]) estancia_dias_q FROM ed WHERE ingresa;
SELECT round(100*avg(ingresa::INT),2) tasa_ingreso_pct FROM ed;
-- por hora de llegada
SELECT hour(llegada) h, count(*) n, round(quantile_cont(h_en_urg,0.5),2) med_h, round(quantile_cont(h_en_urg,0.9),2) p90_h,
       round(100*avg(ingresa::INT),1) pct_ingreso, round(quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa),2) med_h_hasta_piso
FROM ed GROUP BY 1 ORDER BY 1;
-- por dia de semana
SELECT dayofweek(llegada) dow, dayname(llegada) dia, count(*) n, round(quantile_cont(h_en_urg,0.5),2) med_h, round(quantile_cont(h_en_urg,0.9),2) p90_h,
       round(quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa),2) med_h_hasta_piso
FROM ed GROUP BY 1,2 ORDER BY 1;
-- por mes
SELECT date_trunc('month', llegada)::DATE mes, count(*) n, round(quantile_cont(h_en_urg,0.5),2) med_h, round(quantile_cont(h_en_urg,0.9),2) p90_h,
       round(quantile_cont(h_en_urg,0.5) FILTER (WHERE ingresa),2) med_h_hasta_piso, count(*) FILTER (WHERE ingresa) ingresos
FROM ed GROUP BY 1 ORDER BY 1;
-- edad
SELECT CASE WHEN edad<15 THEN '0-14' WHEN edad<45 THEN '15-44' WHEN edad<65 THEN '45-64' WHEN edad<80 THEN '65-79' ELSE '80+' END grupo,
  count(*) n, round(100*avg(ingresa::INT),1) pct_ingreso, round(quantile_cont(h_en_urg,0.5),2) med_h
FROM ed GROUP BY 1 ORDER BY 1;
