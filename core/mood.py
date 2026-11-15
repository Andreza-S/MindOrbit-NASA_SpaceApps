"""Humor do dia a partir do sentimento e do tema principal (RF20)."""
from typing import Optional

import config


def main_theme(hits: dict[str, int], counts: dict[str, int]) -> Optional[str]:
    """Tema com mais acertos hoje; empate: o mais persistente na janela."""
    if not hits:
        return None
    return sorted(hits, key=lambda t: (-hits[t], -counts.get(t, 0), t))[0]


def mood_label(polarity: float, theme: Optional[str]) -> str:
    if theme is None:
        return "bem" if polarity >= config.MOOD_GOOD_POLARITY else "neutro"
    return config.MOOD_BY_THEME.get(theme, "neutro")
