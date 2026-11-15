"""Persistência de temas na janela de 7 dias (RF06)."""
from collections import defaultdict

import config
from models import Analysis


def persistence_counts(history: list[Analysis], today_day: int,
                       today_themes: list[str]) -> dict[str, int]:
    """Em quantos dias distintos da janela (hoje incluído) cada tema apareceu."""
    first_day = today_day - config.WINDOW_DAYS + 1
    days: dict[str, set[int]] = defaultdict(set)
    for a in history:
        if first_day <= a.day <= today_day:
            for t in a.themes:
                days[t].add(a.day)
    for t in today_themes:
        days[t].add(today_day)
    return {t: len(d) for t, d in days.items()}


def alerts_from(counts: dict[str, int]) -> list[str]:
    """Temas presentes em ALERT_DAYS ou mais dias, do mais persistente ao menos."""
    hot = [t for t, n in counts.items() if n >= config.ALERT_DAYS]
    return sorted(hot, key=lambda t: (-counts[t], t))
