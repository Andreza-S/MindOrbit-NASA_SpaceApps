"""Pontos de contato com os módulos da Pessoa B (comms/, simulator/).

Enquanto eles não existem, ficam funções de reserva, para a aba do astronauta
funcionar sozinha. Quando a Pessoa B entregar, o código dela passa a ser usado.
"""
from typing import Optional

import storage
from models import Directive

try:  # Pessoa B: comms/__init__.py (precisa do SQLite; com o armazenamento em memória usa a reserva)
    if not hasattr(storage.backend, "connect"):
        raise ImportError("comms precisa do banco SQLite")
    from comms import acknowledge_read, pull_directives, send_report
    COMMS_AVAILABLE = True
except ImportError:
    COMMS_AVAILABLE = False
    SENT_REPORTS: list[tuple[str, bool]] = []

    def send_report(crew_id: str, immediate: bool) -> None:
        """Reserva: só registra que o relatório seria enviado."""
        SENT_REPORTS.append((crew_id, immediate))

    def pull_directives(crew_id: str) -> list[Directive]:
        return []

    def acknowledge_read(directive_id: int) -> bool:
        return False

try:  # Pessoa B: simulator/__init__.py
    from simulator import demo_text
except ImportError:
    def demo_text(crew_id: str, day: int) -> Optional[str]:
        return None
