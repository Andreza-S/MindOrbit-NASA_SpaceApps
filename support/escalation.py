"""Escalonamento local: no vermelho, orientar a procurar o oficial médico (RF12)."""
from support.feedback import load_texts


def should_escalate(band: str) -> bool:
    return band == "vermelho"


def escalation_text() -> str:
    return load_texts()["escalonamento"]
