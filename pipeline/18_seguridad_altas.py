# Limite de seguridad de las altas tempranas: retorno a urgencias en 72 h segun la franja horaria del alta
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from hun.config import setup, connect
setup()
con = connect(read_only=True)
df = con.execute("""
WITH alta AS (SELECT person_id, t_alta_hosp t, hour(t_alta_hosp) h FROM ed
              WHERE ingresa AND t_alta_hosp >= '2023-02-01' AND t_alta_hosp < '2026-04-27'),
r AS (SELECT a.*, EXISTS (SELECT 1 FROM ed e WHERE e.person_id = a.person_id AND e.llegada > a.t
                          AND e.llegada <= a.t + INTERVAL 72 HOUR AND e.h_en_urg >= 0.25) re72 FROM alta a)
SELECT CASE WHEN h BETWEEN 6 AND 11 THEN 'manana_6_12' WHEN h BETWEEN 12 AND 17 THEN 'tarde_12_18' ELSE 'noche_18_6' END franja,
       count(*) n, round(100 * avg(re72::INT), 2) pct_retorno_urg_72h
FROM r GROUP BY 1 ORDER BY 1""").df()
out = {'definicion': 'altas de hospitalizacion de pacientes ingresados por urgencias; retorno = nuevo episodio de urgencias >= 15 min en las 72 h siguientes',
       'por_franja': df.to_dict(orient='records')}
json.dump(out, open('derived/seguridad_altas.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(df.to_string(index=False))
