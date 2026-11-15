"""As telas rodam sem erro em vários dias, períodos e tripulantes (sem precisar do Streamlit instalado)."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "ui_smoke_script.py"


def _run(tmp_path, memory: bool):
    env = {k: v for k, v in os.environ.items() if k != "MINDORBIT_BACKEND"}
    env["PYTHONPATH"] = str(ROOT)
    env["MINDORBIT_DB"] = str(tmp_path / "ui.db")
    if memory:
        env["MINDORBIT_BACKEND"] = "memory"
    r = subprocess.run([sys.executable, str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0 and "smoke ok" in r.stdout, r.stderr[-2500:]


def test_telas_em_memoria(tmp_path):
    _run(tmp_path, memory=True)


def test_telas_com_sqlite_e_link(tmp_path):
    _run(tmp_path, memory=False)
