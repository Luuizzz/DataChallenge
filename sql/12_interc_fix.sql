CREATE OR REPLACE TABLE adm AS SELECT * FROM ep1 WHERE ingresa;
CREATE OR REPLACE TABLE flags AS
SELECT a.visit_occurrence_id, a.h_en_urg, a.edad, s.servicio FROM adm a CROSS JOIN (SELECT DISTINCT servicio FROM svc) s;
SELECT f.servicio,
  count(*) FILTER (WHERE x.visit_occurrence_id IS NOT NULL) n_con,
  round(quantile_cont(f.h_en_urg,0.5) FILTER (WHERE x.visit_occurrence_id IS NOT NULL),1) med_con,
  round(quantile_cont(f.h_en_urg,0.5) FILTER (WHERE x.visit_occurrence_id IS NULL),1) med_sin,
  round(avg(f.edad) FILTER (WHERE x.visit_occurrence_id IS NOT NULL),0) edad_con
FROM flags f LEFT JOIN svc x ON x.visit_occurrence_id=f.visit_occurrence_id AND x.servicio=f.servicio
GROUP BY 1 HAVING n_con>=300 ORDER BY med_con DESC;
