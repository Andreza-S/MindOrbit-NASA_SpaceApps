"""Orquestra a análise de uma entrada do diário.

Funções puras: entra texto, sensores e padrão pessoal; sai um Analysis.
Não depende de banco, de rede nem da Terra (RNF01, RNF02).
"""
from typing import Optional

from core.baseline_distance import bad_deviation, compute_z
from core.crossing import cross_with_sensors
from core.lexicon import Lexicon
from core.mood import main_theme, mood_label
from core.persistence import alerts_from, persistence_counts
from core.risk import compute_risk
from core.sentiment import polarity
from core.themes import detect_themes, theme_hits
from models import Analysis, Baseline, Entry, SensorDay


def analyze_entry(entry: Entry, history: list[Analysis], baseline: Baseline,
                  sensors: Optional[SensorDay],
                  lexicon: Optional[Lexicon] = None) -> Analysis:
    hits = theme_hits(entry.text, lexicon)
    themes = detect_themes(entry.text, lexicon)
    pol = polarity(entry.text, lexicon)

    z = compute_z(baseline, sensors, pol)
    bad = bad_deviation(z)

    counts = persistence_counts(history, entry.day, themes)
    alerts = alerts_from(counts)
    confirmed = cross_with_sensors(themes, bad)

    risk, band = compute_risk(bad, counts, confirmed, themes)
    theme = main_theme(hits, counts)

    return Analysis(
        entry_id=entry.id or 0,
        crew_id=entry.crew_id,
        day=entry.day,
        themes=themes,
        polarity=pol,
        z=z,
        persistence=counts,
        alerts=alerts,
        confirmed_by=confirmed,
        risk=risk,
        band=band,
        main_theme=theme,
        mood=mood_label(pol, theme),
    )
