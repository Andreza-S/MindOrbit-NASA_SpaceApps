"""Um banco SQLite por visitante, para a demonstração hospedada.

Sem isso, todos os visitantes dividiriam o mesmo dia da missão, os mesmos diários e a mesma fila do link.
Cada sessão do navegador ganha um arquivo temporário que nasce no dia 1. Arquivos antigos são apagados
quando uma nova sessão começa. Ligue com a variável de ambiente MINDORBIT_PER_SESSION=1.
"""
import os
import tempfile
import time
import uuid
from pathlib import Path

MAX_AGE_HOURS = 12


def enabled() -> bool:
    return os.environ.get("MINDORBIT_PER_SESSION") == "1"


def folder() -> Path:
    return Path(os.environ.get("MINDORBIT_SESSION_DIR", Path(tempfile.gettempdir()) / "mindorbit_sessions"))


def cleanup(max_age_hours: float = MAX_AGE_HOURS, now: float | None = None) -> int:
    """Apaga bancos de sessões antigas (e os arquivos -wal/-shm). Devolve quantos bancos removeu."""
    now = time.time() if now is None else now
    removed = 0
    if not folder().exists():
        return 0
    for path in folder().glob("session_*.db*"):
        try:
            if now - path.stat().st_mtime > max_age_hours * 3600:
                path.unlink()
                removed += path.suffix == ".db"
        except OSError:
            pass
    return removed


def new_path() -> Path:
    cleanup()
    folder().mkdir(parents=True, exist_ok=True)
    return folder() / f"session_{uuid.uuid4().hex}.db"
