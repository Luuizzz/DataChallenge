-- V1: llegadas diarias a urgencias (todas / con duracion >= 15 min)
SELECT round(avg(n),0) llegadas_dia, round(avg(n15),0) llegadas_dia_15min, max(n) max_dia FROM (
  SELECT llegada::DATE d, count(*) n, count(*) FILTER (WHERE h_en_urg>=0.25) n15 FROM ed WHERE llegada>='2023-02-01' AND llegada<'2026-05-01' GROUP BY 1);
-- V2: distribucion de h_en_urg en no ingresados con duracion>0
SELECT CASE WHEN h_en_urg<0.25 THEN 'a <15min' WHEN h_en_urg<2 THEN 'b 15min-2h' WHEN h_en_urg<6 THEN 'c 2-6h' WHEN h_en_urg<12 THEN 'd 6-12h'
            WHEN h_en_urg<24 THEN 'e 12-24h' WHEN h_en_urg<72 THEN 'f 24-72h' ELSE 'g >72h' END b, count(*) n, round(100*count(*)/sum(count(*)) OVER (),1) pct
FROM ed WHERE NOT ingresa GROUP BY 1 ORDER BY 1;
-- V3: el inicio de IP coincide exactamente con el fin de la etapa previa? (ingreso administrativo)
SELECT round(100*avg((abs(epoch(t_ingreso_hosp - t_fin_urg))<60)::INT),1) pct_ip_inicia_al_cerrar_urg,
       round(100*avg((t_ingreso_hosp < t_fin_urg)::INT),1) pct_ip_antes_fin_urg FROM ed WHERE ingresa;
-- V4: censo hospitalizacion por personas distintas (fusionando etapas IP solapadas de la misma persona)
CREATE OR REPLACE TABLE ip_p AS SELECT person_id, t0, t1 FROM stage WHERE etapa='IP' AND t1>t0;
CREATE OR REPLACE TABLE ip_merged AS
WITH o AS (SELECT *, max(t1) OVER (PARTITION BY person_id ORDER BY t0 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) pm FROM ip_p),
g AS (SELECT *, sum(CASE WHEN pm IS NULL OR t0>pm THEN 1 ELSE 0 END) OVER (PARTITION BY person_id ORDER BY t0) gid FROM o)
SELECT person_id, gid, min(t0) t0, max(t1) t1 FROM g GROUP BY 1,2;
SELECT (SELECT count(*) FROM ip_p) etapas_ip, (SELECT count(*) FROM ip_merged) estancias_fusionadas,
  (SELECT round(avg(epoch(t1-t0))/86400,2) FROM ip_merged) estancia_media_d,
  (SELECT round(quantile_cont(epoch(t1-t0)/86400,0.5),2) FROM ip_merged) estancia_mediana_d;
-- censo medio aproximado = ingresos/dia * estancia media (ley de Little)
SELECT year(t0) y, count(*) estancias, round(sum(epoch(t1-t0))/86400/365,1) censo_medio_little FROM ip_merged GROUP BY 1 ORDER BY 1;
-- V5: censo urgencias acotando a estancias 15min-72h
SELECT year(llegada) y, round(sum(least(h_en_urg,72))/24/365,1) censo_urg_little_todo,
  round(sum(h_en_urg) FILTER (WHERE h_en_urg BETWEEN 0.25 AND 72)/24/365,1) censo_urg_15m_72h FROM ed GROUP BY 1 ORDER BY 1;
-- V6: tipo de visita origen de episodios URG (rehab? urg?)
SELECT v.visit_concept_id, count(*) n FROM ed e JOIN 'visit_occurrence.parquet' v USING (visit_occurrence_id) GROUP BY 1 ORDER BY 2 DESC;
