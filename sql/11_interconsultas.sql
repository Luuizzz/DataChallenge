-- servicios/interconsultas presentes por visita (solo conceptos de consulta/remision/servicio)
CREATE OR REPLACE TABLE svc AS
SELECT p.visit_occurrence_id, c.concept_name servicio
FROM 'procedure_by_visit.parquet' p JOIN 'concept.parquet' c ON c.concept_id=p.procedure_concept_id
WHERE c.concept_name IN ('Other consultation','Specialized medical examination') OR c.concept_name LIKE '%Consult note'
   OR c.concept_name LIKE 'Seen by%' OR c.concept_name LIKE 'Referral to%' OR c.concept_name LIKE '%consultation%'
GROUP BY 1,2;
SELECT servicio, count(*) visitas FROM svc GROUP BY 1 ORDER BY 2 DESC;
-- ingresados (episodio unico, >=15 min): tiempo hasta hospitalizacion con vs sin cada servicio, + edad media
WITH a AS (SELECT * FROM ep1 WHERE ingresa)
SELECT s.servicio, count(*) n, round(quantile_cont(a.h_en_urg,0.5),1) med_h_con,
  round((SELECT quantile_cont(h_en_urg,0.5) FROM a a2 WHERE a2.visit_occurrence_id NOT IN (SELECT visit_occurrence_id FROM svc s2 WHERE s2.servicio=s.servicio)),1) med_h_sin,
  round(avg(a.edad),0) edad_media, round(100*avg((a.h_en_urg>24)::INT),0) pct_mas24h
FROM a JOIN svc s USING (visit_occurrence_id) GROUP BY 1 HAVING count(*)>=300 ORDER BY med_h_con DESC;
-- numero de servicios distintos por visita (ingresados) vs tiempo
WITH a AS (SELECT a.*, coalesce(k.n_svc,0) n_svc FROM ep1 a LEFT JOIN (SELECT visit_occurrence_id, count(*) n_svc FROM svc GROUP BY 1) k USING (visit_occurrence_id) WHERE a.ingresa)
SELECT least(n_svc,6) n_servicios, count(*) n, round(quantile_cont(h_en_urg,0.5),1) med_h, round(quantile_cont(h_en_urg,0.9),1) p90_h FROM a GROUP BY 1 ORDER BY 1;
