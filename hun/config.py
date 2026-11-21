"""Rutas del proyecto, centralizadas y configurables por variables de entorno.

HUN_RAW_DIR  carpeta con los 8 Parquet extraidos de la base OMOP (por defecto <repo>/data/raw)
HUN_OUT_DIR  carpeta de trabajo y resultados: work.duckdb, derived/, figs/, powerbi/ (por defecto <repo>/outputs)
"""
import os
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"


def raw_dir() -> Path:
    return Path(os.environ.get("HUN_RAW_DIR", ROOT / "data" / "raw")).resolve()


def out_dir() -> Path:
    return Path(os.environ.get("HUN_OUT_DIR", ROOT / "outputs")).resolve()


def setup() -> Path:
    """Crea las carpetas de salida y se ubica en la carpeta de resultados (las rutas relativas de los scripts parten de ahi)."""
    out = out_dir()
    for sub in ("derived", "figs", "powerbi"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    os.chdir(out)
    return out


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Conexion a la base de trabajo. Los Parquet crudos se leen por su nombre ('person.parquet') gracias a file_search_path."""
    con = duckdb.connect(str(out_dir() / "work.duckdb"), read_only=read_only)
    con.execute(f"SET file_search_path='{raw_dir().as_posix()}'")
    return con
