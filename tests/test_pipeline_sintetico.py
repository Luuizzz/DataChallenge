"""El pipeline SQL corre de principio a fin sobre datos sinteticos y respeta las reglas metodologicas clave."""
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def _correr(hasta, env_dirs):
    raw, out = env_dirs
    import os
    env = dict(os.environ, HUN_RAW_DIR=str(raw), HUN_OUT_DIR=str(out), PYTHONPATH=str(ROOT))
    subprocess.run([sys.executable, str(ROOT / "pipeline" / "run_all.py"), "--hasta", hasta], check=True, env=env, cwd=ROOT,
                   capture_output=True)
    return duckdb.connect(str(out / "work.duckdb"), read_only=True)


def test_episodios_se_parten_con_huecos_mayores_a_7_dias(entorno_sintetico):
    con = _correr("01", entorno_sintetico)
    partidos = con.execute("SELECT count(*) FROM (SELECT visit_occurrence_id FROM episode GROUP BY 1 HAVING count(*) > 1)").fetchone()[0]
    sin_partir = con.execute("""SELECT count(*) FROM (
        SELECT visit_occurrence_id, ep_num, max(t1) - min(t0) dur FROM stage_ep GROUP BY 1, 2) WHERE dur > INTERVAL 30 DAY""").fetchone()[0]
    assert partidos > 0          # el artefacto de ~16 dias produce visitas con mas de un episodio
    assert sin_partir == 0       # ningun episodio arrastra el salto artificial


def test_flujo_y_censo_coherentes(entorno_sintetico):
    con = _correr("05", entorno_sintetico)
    tipos = dict(con.execute("SELECT tipo_episodio, count(*) FROM episode GROUP BY 1").fetchall())
    assert {"URG", "URG->HOSP", "REHAB"} <= set(tipos)
    # el tiempo en urgencias nunca es negativo y los ingresados tienen fecha de hospitalizacion
    assert con.execute("SELECT count(*) FROM ed WHERE h_en_urg < 0").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM ed WHERE ingresa AND t_ingreso_hosp IS NULL").fetchone()[0] == 0
    # el censo horario no es negativo y no supera el numero de episodios
    mn, mx = con.execute("SELECT min(censo_urg), max(censo_urg) FROM census").fetchone()
    n_ep = con.execute("SELECT count(*) FROM ed").fetchone()[0]
    assert mn >= 0 and mx <= n_ep


def test_rutas_configurables(entorno_sintetico):
    from hun import config
    raw, out = entorno_sintetico
    assert config.raw_dir() == raw.resolve() and config.out_dir() == out.resolve()
