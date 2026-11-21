CREATE OR REPLACE TABLE svc_grp AS
SELECT visit_occurrence_id,
  bool_or(servicio IN ('Referral to trauma and orthopaedics surgery service','Seen by urology service','Anesthesia consultation','Seen by general surgery service')) quir,
  count(*) n_svc FROM svc GROUP BY 1;
CREATE OR REPLACE TABLE sim_in AS
SELECT e.episode_id, e.llegada, e.h_en_urg AS t_obs_h, e.d_estancia_hosp AS los_d, e.t_alta_hosp,
  CASE WHEN coalesce(v.uci,false) THEN 'UCI' WHEN coalesce(g.quir,false) THEN 'QUIR' WHEN g.n_svc>0 THEN 'OTRA_IC' ELSE 'SIN_IC' END grupo
FROM ed e LEFT JOIN vflags v USING (visit_occurrence_id) LEFT JOIN svc_grp g USING (visit_occurrence_id)
WHERE e.ingresa AND e.d_estancia_hosp > 0 AND e.h_en_urg >= 0 AND e.llegada >= '2024-01-01' AND e.llegada < '2026-01-01';
SELECT grupo, count(*) n, round(quantile_cont(t_obs_h,0.5),1) med_t, round(stddev(ln(t_obs_h+0.5)),2) sd_log, round(quantile_cont(los_d,0.5),2) med_los,
  round(100*avg((hour(t_alta_hosp)<12)::INT),1) pct_alta_am FROM sim_in GROUP BY 1 ORDER BY 2 DESC;
SELECT CASE WHEN hour(llegada) BETWEEN 0 AND 6 THEN 'noche 0-6' WHEN hour(llegada) BETWEEN 9 AND 17 THEN 'dia 9-17' ELSE 'otro' END franja,
  count(*) n, round(quantile_cont(t_obs_h,0.5),1) med_t FROM sim_in WHERE grupo<>'UCI' AND llegada>='2025-01-01' GROUP BY 1;
SELECT round(quantile_cont(t_obs_h,0.5),1) med_t_2025, round(quantile_cont(t_obs_h,0.9),1) p90_2025, round(100*avg((t_obs_h>24)::INT),1) pct24 FROM sim_in WHERE grupo<>'UCI' AND llegada>='2025-01-01';
