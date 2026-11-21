-- Episodios: una visita se parte cuando entre etapas consecutivas hay > 7 dias
CREATE OR REPLACE TABLE stage AS
SELECT d.visit_detail_id, d.visit_occurrence_id, v.person_id,
       CASE d.visit_detail_concept_id WHEN 9203 THEN 'ER' WHEN 3045729 THEN 'TRIAGE' WHEN 9201 THEN 'IP' WHEN 581479 THEN 'REHAB' ELSE 'OTRO' END AS etapa,
       d.visit_detail_start_datetime AS t0, d.visit_detail_end_datetime AS t1
FROM 'visit_detail.parquet' d
JOIN 'visit_occurrence.parquet' v USING (visit_occurrence_id);

CREATE OR REPLACE TABLE stage_ep AS
WITH o AS (
  SELECT *, max(t1) OVER (PARTITION BY visit_occurrence_id ORDER BY t0, visit_detail_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_max_end
  FROM stage)
SELECT *, sum(CASE WHEN prev_max_end IS NULL OR t0 - prev_max_end > INTERVAL 7 DAY THEN 1 ELSE 0 END)
            OVER (PARTITION BY visit_occurrence_id ORDER BY t0, visit_detail_id) AS ep_num
FROM o;

CREATE OR REPLACE TABLE episode AS
SELECT visit_occurrence_id, ep_num, visit_occurrence_id::BIGINT*100 + ep_num AS episode_id, any_value(person_id) person_id,
       min(t0) t_inicio, max(t1) t_fin, count(*) n_etapas,
       string_agg(etapa, '>' ORDER BY t0, visit_detail_id) secuencia,
       bool_or(etapa='ER') has_er, bool_or(etapa='TRIAGE') has_triage, bool_or(etapa='IP') has_ip, bool_or(etapa='REHAB') has_rehab,
       min(t0) FILTER (WHERE etapa IN ('ER','TRIAGE')) t_llegada_urg,
       max(t1) FILTER (WHERE etapa IN ('ER','TRIAGE') ) t_fin_urg,
       min(t0) FILTER (WHERE etapa='IP') t_ingreso_hosp,
       max(t1) FILTER (WHERE etapa='IP') t_alta_hosp,
       max(t1) FILTER (WHERE etapa IN ('ER','TRIAGE') ) AS _x
FROM stage_ep GROUP BY 1,2;
ALTER TABLE episode DROP COLUMN _x;

CREATE OR REPLACE TABLE episode AS
SELECT *,
  CASE WHEN has_er OR has_triage THEN (CASE WHEN has_ip THEN 'URG->HOSP' ELSE 'URG' END)
       WHEN has_ip THEN 'HOSP_DIRECTA' WHEN has_rehab THEN 'REHAB' ELSE 'OTRO' END AS tipo_episodio
FROM episode;

SELECT tipo_episodio, count(*) n, round(100*count(*)/sum(count(*)) OVER (),1) pct FROM episode GROUP BY 1 ORDER BY 2 DESC;
SELECT count(*) visitas, sum(k>1::INT) visitas_multi_ep, max(k) max_ep FROM (SELECT visit_occurrence_id, max(ep_num) k FROM episode GROUP BY 1);
-- validacion: huecos internos residuales
SELECT quantile_cont(epoch(t_fin - t_inicio)/86400, [0.5,0.9,0.99,0.999]) span_dias, tipo_episodio FROM episode GROUP BY 2;
-- secuencias top en episodios de urgencias
SELECT secuencia, count(*) n FROM episode WHERE tipo_episodio LIKE 'URG%' GROUP BY 1 ORDER BY 2 DESC LIMIT 15;
