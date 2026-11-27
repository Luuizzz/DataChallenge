# Data Challenge HUN 2026: flujo de pacientes urgencias → hospitalización

Análisis, predicción y optimización del flujo de pacientes sobre datos OMOP-CDM anonimizados.
**Documento completo:** [`docs/DOCUMENTO_FINAL.md`](docs/DOCUMENTO_FINAL.md)

> **Este repositorio no contiene datos.** Los datasets son propiedad de sus titulares y solo pueden usarse dentro del Data Challenge HUN 2026. `.gitignore` excluye Parquet, CSV, bases DuckDB, archivos `.pbix`, cachés de Power BI y credenciales. Para probar el código sin acceso a la base hay un **generador de datos sintéticos** con el mismo esquema.


## Hallazgos principales

- Mediana de **~23 h** desde la llegada a urgencias hasta la hospitalización; el 67 % de los ingresados supera las 12 h (43 % de todas las atenciones, frente a ~10 % en Inglaterra). La espera ocurre dentro de la atención en urgencias, no en el registro.
- La **capacidad efectiva de camas está saturada** (simulación calibrada: ~269 camas efectivas frente a un censo medio de ~266; supuesto, sin el número real de camas). Las altas se concentran a las 15–18 h (solo un 13 % antes del mediodía).
- Las interconsultas quirúrgicas alargan la espera incluso **ajustando** por edad, horario, año, censos y UCI: ortopedia +22 h, urología +18 h, cirugía +7 h.
- Alerta de congestión a 3 h (precisión 0,80, IC 95 % 0,71–0,87). Modelo de ingreso a las 3 h (AUC 0,71, IC 0,70–0,72): marcando el 20 % de mayor riesgo anticipa ~18 ingresos al día con una mediana de ~20 h de antelación.
- Simulación: altas por la mañana + interconsultas más rápidas ⇒ **−7,3 h de mediana y −14 h de p90** con la capacidad calibrada, casi como +10 camas y sin costo. Al validar con 2026 se mantiene el orden de las medidas (los valores absolutos requieren recalibrar la capacidad). Adelantar altas no aumenta el retorno a urgencias en 72 h (2,3 % tras altas de mañana frente a 2,8 % de tarde).

## Estructura

```
hun/                 utilidades compartidas
  config.py          rutas centralizadas (variables de entorno HUN_RAW_DIR y HUN_OUT_DIR) y conexión DuckDB
  cola.py            núcleo de la simulación: asignación FIFO de camas
  synthetic.py       generador de datos sintéticos con el esquema de la extracción
extract/             extracción desde PostgreSQL a Parquet (DuckDB + extensión postgres)
sql/                 transformaciones: episodios, flujo, censo, interconsultas, insumos de la simulación
pipeline/            pasos en Python (modelos, alerta, simulación, validación, incertidumbre, tablas de Power BI)
  run_all.py         ejecuta todo en orden;  run_sql.py ejecuta un .sql suelto
tests/               pruebas automáticas (pytest) sobre datos sintéticos
powerbi/             proyecto del dashboard (pbip/), generador del informe PBIR y guías
figs/                figuras (solo agregados)
docs/                documento final y verificación de la reproducción
```

## Cómo reproducir

1. **Entorno** (Python 3.11):
   ```bash
   python -m venv .venv && .venv/Scripts/activate      # Windows (en Linux/macOS: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
2. **Pruebas** (no requieren datos reales; generan datos sintéticos en una carpeta temporal):
   ```bash
   python -m pytest -q
   ```
3. **Extracción** (requiere VPN y credenciales del reto). Crear `~/.pg_service.conf` con una sección `[uhn]` (host, port, dbname, user) y `~/.pgpass` con la contraseña. Desde la raíz del repositorio:
   ```bash
   duckdb -c ".read extract/10_dump.sql"      # genera los 8 Parquet en data/raw/
   ```
4. **Pipeline** (unos 20 minutos con los datos reales):
   ```bash
   python pipeline/run_all.py                  # lee data/raw/ y escribe en outputs/
   ```
   Las rutas se cambian con variables de entorno, por ejemplo `HUN_RAW_DIR=D:/extraccion HUN_OUT_DIR=D:/resultados`. Resultado: `outputs/work.duckdb`, `outputs/derived/` (métricas, modelos, simulación), `outputs/figs/` y `outputs/powerbi/` (CSV agregados del dashboard).
   El pipeline es determinista (semillas fijas, LightGBM en modo `deterministic`, consultas con orden total): dos ejecuciones dan salidas idénticas. La comparación con las cifras del documento está en [`docs/VERIFICACION_REPRODUCCION.md`](docs/VERIFICACION_REPRODUCCION.md).
5. **Demo sin datos reales:**
   ```bash
   python -m hun.synthetic data/raw_demo
   HUN_RAW_DIR=data/raw_demo python pipeline/run_all.py --hasta 05   # pasos SQL de episodios, flujo, censo y estándares
   ```

## Decisiones metodológicas clave

| Decisión | Motivo |
|---|---|
| Visitas divididas en episodios si hay > 7 días entre etapas | Artefacto de 15–19 días en el 44 % de las visitas |
| Duraciones calculadas con `visit_detail` | `visit_end_datetime` = inicio en el 100 % |
| Métricas de urgencias sobre episodios de 15 minutos o más | El 64 % de los no ingresados son registros de menos de 15 minutos |
| Partición temporal (2023–24 / 2025 / ene–abr 2026) | Evita fugas de información en el tiempo |
| Mayo–julio de 2026 excluido | Volumen incompleto |
| Diagnósticos con riesgo de fuga excluidos del modelo de ingreso | El hospital indicó que se registran al ingreso y al final |
| Camas efectivas calibradas (269) con sensibilidad entre 249 y 289 y validación en 2026 | No se dispone del número real de camas |

Supuestos y limitaciones completos: `docs/DOCUMENTO_FINAL.md`, secciones 2.2 y 8.

## Dashboard de Power BI

Versión publicada (acceso con cuenta de la universidad): https://app.powerbi.com/links/PKfNZLWjnt?ctid=bab0b679-bd5f-4fe8-b516-c6b8b317c782&pbi_source=linkShare

El proyecto `powerbi/pbip/` lee los CSV agregados desde la carpeta del parámetro **`RutaDatos`** (por defecto `C:\datachallenge\powerbi\`). Para regenerarlo en otro equipo: ejecuta el pipeline, copia `outputs/powerbi/*.csv` a esa carpeta o cambia el parámetro en Power Query (Transformar datos → Administrar parámetros → RutaDatos) y actualiza. El informe se puede regenerar con `python powerbi/13_generar_visuales_v2.py <carpeta modelo.Report>`.

## Equipo

DATACHALLENGE_G12, Data Challenge HUN 2026. Licencia MIT (solo código y documentación; no cubre los datos).
