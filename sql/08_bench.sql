-- metricas comparables con estandares (periodo 2023-02 a 2026-04)
WITH e AS (SELECT * FROM ed WHERE llegada>='2023-02-01' AND llegada<'2026-05-01')
SELECT 'todos' cohorte, count(*) n, round(100*avg((h_en_urg<=4)::INT),1) pct_4h, round(100*avg((h_en_urg>8)::INT),1) pct_mas8h, round(100*avg((h_en_urg>12)::INT),1) pct_mas12h FROM e
UNION ALL SELECT 'duracion>=15min', count(*), round(100*avg((h_en_urg<=4)::INT),1), round(100*avg((h_en_urg>8)::INT),1), round(100*avg((h_en_urg>12)::INT),1) FROM e WHERE h_en_urg>=0.25
UNION ALL SELECT 'ingresados', count(*), round(100*avg((h_en_urg<=4)::INT),1), round(100*avg((h_en_urg>8)::INT),1), round(100*avg((h_en_urg>12)::INT),1) FROM e WHERE ingresa;
SELECT round(60*quantile_cont(h_en_urg,0.5)) med_min_ingresados FROM ed WHERE ingresa AND llegada>='2023-02-01' AND llegada<'2026-05-01';
-- altas antes de mediodia (estancias fusionadas)
SELECT round(100*avg((hour(t1)<12)::INT),1) pct_altas_antes_12h, round(100*avg((hour(t1) BETWEEN 14 AND 18)::INT),1) pct_altas_14_18h FROM ip_merged WHERE t1<'2026-05-01';
