-- censo horario de hospitalizacion (etapas IP) y de urgencias (episodios URG con duracion>0)
CREATE OR REPLACE TABLE ip_int AS SELECT t0, t1 FROM stage WHERE etapa='IP' AND t1>t0;
CREATE OR REPLACE TABLE ed_int AS SELECT llegada t0, coalesce(t_ingreso_hosp, t_fin_urg) t1 FROM ed WHERE coalesce(t_ingreso_hosp, t_fin_urg) > llegada;
CREATE OR REPLACE TABLE hours AS SELECT unnest(generate_series(TIMESTAMP '2023-01-01', TIMESTAMP '2026-07-31 23:00:00', INTERVAL 1 HOUR)) AS hr;
CREATE OR REPLACE TABLE census AS
WITH ev AS (
  SELECT t0 t, 1 d, 'ip' k FROM ip_int UNION ALL SELECT t1, -1, 'ip' FROM ip_int
  UNION ALL SELECT t0, 1, 'ed' FROM ed_int UNION ALL SELECT t1, -1, 'ed' FROM ed_int),
c AS (SELECT k, t, sum(d) OVER (PARTITION BY k ORDER BY t ROWS UNBOUNDED PRECEDING) n FROM ev),
ipc AS (SELECT h.hr, c.n FROM hours h ASOF LEFT JOIN (SELECT * FROM c WHERE k='ip') c ON h.hr >= c.t),
edc AS (SELECT h.hr, c.n FROM hours h ASOF LEFT JOIN (SELECT * FROM c WHERE k='ed') c ON h.hr >= c.t)
SELECT ipc.hr, coalesce(ipc.n,0) censo_hosp, coalesce(edc.n,0) censo_urg FROM ipc JOIN edc USING (hr);

SELECT year(hr) y, round(avg(censo_hosp),1) hosp_media, max(censo_hosp) hosp_max, round(avg(censo_urg),1) urg_media, max(censo_urg) urg_max
FROM census WHERE hr >= '2023-02-01' GROUP BY 1 ORDER BY 1;
SELECT hour(hr) h, round(avg(censo_hosp),1) hosp, round(avg(censo_urg),1) urg FROM census WHERE hr>='2023-02-01' AND hr<'2026-05-01' GROUP BY 1 ORDER BY 1;
-- altas e ingresos a piso por hora
SELECT h, sum(ingresos) ingresos_piso, sum(altas) altas_piso FROM (
  SELECT hour(t0) h, 1 ingresos, 0 altas FROM ip_int UNION ALL SELECT hour(t1), 0, 1 FROM ip_int) GROUP BY 1 ORDER BY 1;
-- tiempo hasta piso vs censo de hospitalizacion a la llegada (quintiles)
CREATE OR REPLACE TABLE ed_c AS SELECT e.*, c.censo_hosp, c.censo_urg FROM ed e ASOF LEFT JOIN census c ON e.llegada >= c.hr;
SELECT q, min(censo_hosp) desde, max(censo_hosp) hasta, count(*) n, round(quantile_cont(h_en_urg,0.5),1) med_h_hasta_piso, round(quantile_cont(h_en_urg,0.9),1) p90
FROM (SELECT *, ntile(5) OVER (ORDER BY censo_hosp) q FROM ed_c WHERE ingresa AND llegada<'2026-05-01') GROUP BY 1 ORDER BY 1;
SELECT q, min(censo_urg) desde, max(censo_urg) hasta, count(*) n, round(quantile_cont(h_en_urg,0.5),2) med_h, round(quantile_cont(h_en_urg,0.9),1) p90
FROM (SELECT *, ntile(5) OVER (ORDER BY censo_urg) q FROM ed_c WHERE NOT ingresa AND h_en_urg>0.25 AND llegada<'2026-05-01') GROUP BY 1 ORDER BY 1;
