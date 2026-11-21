"""Ejecuta el pipeline completo en orden.

Requisitos: los Parquet de la extraccion en HUN_RAW_DIR (por defecto data/raw). Resultados en HUN_OUT_DIR (por defecto outputs/).
Uso:  python pipeline/run_all.py            (todo)
      python pipeline/run_all.py --hasta 08  (solo hasta el paso indicado; util para probar con datos sinteticos)
"""
import argparse, os, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PASOS = [
    ("01", "sql", "sql/01_episodes.sql"),          # etapas y episodios (corte > 7 dias)
    ("02", "sql", "sql/02_flow.sql"),              # metricas urgencias -> hospitalizacion
    ("03", "sql", "sql/03_census.sql"),            # censo horario de urgencias y hospitalizacion
    ("04", "sql", "sql/07_verify.sql"),            # verificaciones + estancias fusionadas (ip_merged)
    ("05", "sql", "sql/08_bench.sql"),             # metricas comparables con estandares
    ("06", "py", "pipeline/04_models.py"),         # modelos base (ingreso, espera > 24 h, estancia)
    ("07", "py", "pipeline/05_models_3h.py"),      # modelo de ingreso a las 3 h
    ("08", "py", "pipeline/05b_models_3h_sin_fuga.py"),  # idem sin diagnosticos con riesgo de fuga
    ("09", "py", "pipeline/06_export_figs.py"),    # figuras y tablas derivadas
    ("10", "sql", "sql/10_proc_flow.sql"),         # servicios por visita (UCI, imagenes, interconsultas)
    ("11", "sql", "sql/11_interconsultas.sql"),
    ("12", "sql", "sql/12_interc_fix.sql"),        # espera con / sin cada interconsulta
    ("13", "py", "pipeline/15_interconsultas_ajustado.py"),  # efecto ajustado (regresion cuantil)
    ("14", "py", "pipeline/07_alerta_congestion.py"),        # pronostico del censo a 1-3 h y alerta
    ("15", "py", "pipeline/08_figs2.py"),
    ("16", "sql", "sql/13_sim_inputs.sql"),
    ("17", "py", "pipeline/09_simulacion.py"),     # simulacion de eventos discretos + escenarios
    ("18", "py", "pipeline/10_sensibilidad.py"),   # sensibilidad a la capacidad
    ("19", "py", "pipeline/17_validacion_simulacion.py"),    # validacion fuera de muestra (2026)
    ("20", "py", "pipeline/14_incertidumbre.py"),  # IC bootstrap y calibracion
    ("21", "py", "pipeline/16_modelo_ingreso_rigor.py"),     # ventanas, logistica, SHAP, analisis de decision
    ("22", "py", "pipeline/18_seguridad_altas.py"),  # retorno a urgencias en 72 h segun la hora del alta
    ("23", "py", "pipeline/19_fig_escenarios.py"),   # figura de escenarios para el documento
    ("24", "py", "pipeline/11_powerbi.py"),        # tablas agregadas para Power BI
]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--hasta", default="99"); a = ap.parse_args()
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    for paso, tipo, f in PASOS:
        if paso > a.hasta:
            break
        print(f"\n=== {paso} · {f} ===", flush=True)
        cmd = [sys.executable, str(ROOT / "pipeline" / "run_sql.py"), f] if tipo == "sql" else [sys.executable, str(ROOT / f)]
        subprocess.run(cmd, check=True, env=env, cwd=ROOT)
    print("\nPipeline completo.")
