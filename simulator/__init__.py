"""Simulador de dados do MindOrbit (Pessoa B)."""
import json
from functools import lru_cache
from typing import Optional

import config

DIARIOS_PATH = config.DATA_DIR / "diarios_demo.json"


@lru_cache(maxsize=1)
def _diarios(mtime: float) -> dict:
    dados = json.loads(DIARIOS_PATH.read_text(encoding="utf-8"))
    return {(d["crew_id"], int(d["day"])): d["text"] for d in dados}


def demo_text(crew_id: str, day: int) -> Optional[str]:
    """Texto simulado do diário desse tripulante e dia, ou None se não houver."""
    if not DIARIOS_PATH.exists():
        return None
    return _diarios(DIARIOS_PATH.stat().st_mtime).get((crew_id, int(day)))
