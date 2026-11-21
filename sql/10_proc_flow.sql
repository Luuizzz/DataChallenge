-- solo visitas con un unico episodio (los procedimientos no tienen fecha; asi se asignan sin ambiguedad)
CREATE OR REPLACE TABLE ep1 AS SELECT e.* FROM ed_c e WHERE e.visit_occurrence_id IN (SELECT visit_occurrence_id FROM episode GROUP BY 1 HAVING count(*)=1) AND e.llegada<'2026-05-01' AND e.h_en_urg>=0.25;
CREATE OR REPLACE TABLE vflags AS
SELECT p.visit_occurrence_id,
  bool_or(c.concept_name IN ('Other consultation','Specialized medical examination') OR c.concept_name LIKE '%Consult note' OR c.concept_name LIKE 'Seen by%' OR c.concept_name LIKE 'Referral to%') interconsulta,
  bool_or(c.concept_name LIKE 'CT %' OR c.concept_name LIKE 'MRI%' OR c.concept_name LIKE 'MR %') tac_rm,
  bool_or(c.concept_name LIKE 'XR %' OR c.concept_name LIKE '%ultrasound%' OR c.concept_name LIKE 'US %') rx_eco,
  bool_or(c.concept_name LIKE 'Admission to%intensive care%') uci,
  bool_or(c.domain_id='Measurement') laboratorio
FROM 'procedure_by_visit.parquet' p JOIN 'concept.parquet' c ON c.concept_id=p.procedure_concept_id GROUP BY 1;
SELECT ingresa, coalesce(interconsulta,false) interconsulta, count(*) n, round(quantile_cont(h_en_urg,0.5),1) med_h, round(quantile_cont(h_en_urg,0.9),1) p90_h
FROM ep1 LEFT JOIN vflags USING (visit_occurrence_id) GROUP BY ALL ORDER BY 1,2;
SELECT ingresa, coalesce(tac_rm,false) tac_rm, count(*) n, round(quantile_cont(h_en_urg,0.5),1) med_h FROM ep1 LEFT JOIN vflags USING (visit_occurrence_id) GROUP BY ALL ORDER BY 1,2;
SELECT coalesce(uci,false) uci, count(*) n, round(quantile_cont(h_en_urg,0.5),1) med_h_hasta_hosp, round(quantile_cont(d_estancia_hosp,0.5),1) med_estancia_d
FROM ep1 LEFT JOIN vflags USING (visit_occurrence_id) WHERE ingresa GROUP BY ALL ORDER BY 1;
