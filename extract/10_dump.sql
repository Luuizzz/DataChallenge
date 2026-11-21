.read extract/00_attach.sql
.timer on
SET preserve_insertion_order=false;
-- nucleo de flujo: completo (provider_id se omite: es constante)
COPY (SELECT visit_occurrence_id, person_id, visit_concept_id, visit_start_datetime FROM h.uninorte_omop.visit_occurrence)
  TO 'data/raw/visit_occurrence.parquet' (FORMAT parquet, COMPRESSION zstd);
COPY (SELECT visit_detail_id, visit_occurrence_id, visit_detail_concept_id, visit_detail_start_datetime, visit_detail_end_datetime FROM h.uninorte_omop.visit_detail)
  TO 'data/raw/visit_detail.parquet' (FORMAT parquet, COMPRESSION zstd);
COPY (SELECT * FROM h.uninorte_omop.person)
  TO 'data/raw/person.parquet' (FORMAT parquet, COMPRESSION zstd);
COPY (SELECT * FROM h.uninorte_omop.cups)
  TO 'data/raw/cups.parquet' (FORMAT parquet, COMPRESSION zstd);
-- diagnosticos: sin condition_type_concept_id (siempre 0)
COPY (SELECT condition_occurrence_id, person_id, visit_occurrence_id, condition_concept_id, condition_start_datetime FROM h.uninorte_omop.condition_occurrence)
  TO 'data/raw/condition_occurrence.parquet' (FORMAT parquet, COMPRESSION zstd);
-- procedimientos: sin fecha en origen -> agregados por visita y concepto
COPY (SELECT * FROM postgres_query('h', $$
   SELECT visit_occurrence_id, person_id, procedure_concept_id, count(*)::int4 n
   FROM uninorte_omop.procedure_occurrence GROUP BY 1,2,3$$))
  TO 'data/raw/procedure_by_visit.parquet' (FORMAT parquet, COMPRESSION zstd);
-- mediciones: sin el texto libre (800 chars/fila, 15 GB, riesgo de datos sensibles)
COPY (SELECT measurement_id, person_id, visit_occurrence_id, measurement_concept_id, measurement_datetime, value_as_number::DOUBLE AS value_as_number FROM h.uninorte_omop.measurement)
  TO 'data/raw/measurement.parquet' (FORMAT parquet, COMPRESSION zstd);
-- vocabulario: solo conceptos usados
COPY (SELECT * FROM postgres_query('h', $$
   SELECT c.* FROM uninorte_omop.concept c WHERE c.concept_id IN (
     SELECT visit_concept_id FROM uninorte_omop.visit_occurrence UNION SELECT visit_detail_concept_id FROM uninorte_omop.visit_detail
     UNION SELECT condition_concept_id FROM uninorte_omop.condition_occurrence UNION SELECT procedure_concept_id FROM uninorte_omop.procedure_occurrence
     UNION SELECT measurement_concept_id FROM uninorte_omop.measurement
     UNION SELECT gender_concept_id FROM uninorte_omop.person UNION SELECT race_concept_id FROM uninorte_omop.person UNION SELECT ethnicity_concept_id FROM uninorte_omop.person)$$))
  TO 'data/raw/concept.parquet' (FORMAT parquet, COMPRESSION zstd);
