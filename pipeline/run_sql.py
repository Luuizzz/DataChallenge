"""Ejecuta un archivo .sql sobre la base de trabajo (work.duckdb) e imprime el resultado de cada SELECT.
Uso: python pipeline/run_sql.py sql/01_episodes.sql"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import duckdb
from hun.config import setup, connect, ROOT


def run(sql_file: str, quiet: bool = False) -> None:
    path = pathlib.Path(sql_file)
    if not path.is_absolute():
        path = ROOT / path
    setup()
    con = connect()
    con.execute("SET threads=12; SET memory_limit='10GB'")
    for st in duckdb.extract_statements(path.read_text(encoding="utf-8")):
        r = con.execute(st)
        if st.type == duckdb.StatementType.SELECT and not quiet:
            print(r.df().to_string(max_colwidth=90)); print()
    con.close()


if __name__ == "__main__":
    run(sys.argv[1])
