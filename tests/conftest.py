import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def entorno_sintetico(tmp_path, monkeypatch):
    """Datos sinteticos en un directorio temporal y salidas aisladas (nunca toca data/ ni outputs/ reales)."""
    from hun import synthetic
    raw = synthetic.generar(tmp_path / "raw", visitas=1500, semilla=1)
    out = tmp_path / "outputs"
    monkeypatch.setenv("HUN_RAW_DIR", str(raw))
    monkeypatch.setenv("HUN_OUT_DIR", str(out))
    import hun.config
    importlib.reload(hun.config)
    yield raw, out
    monkeypatch.chdir(ROOT)
