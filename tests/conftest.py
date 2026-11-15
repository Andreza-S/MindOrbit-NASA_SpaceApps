import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["MINDORBIT_BACKEND"] = "memory"   # testes unitários: armazenamento em memória

import pytest

from models import Analysis, Baseline, Entry, SensorDay


@pytest.fixture
def baseline() -> Baseline:
    return Baseline(
        crew_id="T1", sleep_mean=7.2, sleep_std=0.6, activity_mean=48, activity_std=12,
        hr_mean=58, hr_std=3, polarity_mean=0.15, polarity_std=0.2, usual_themes=["sobrecarga"],
    )


@pytest.fixture
def normal_sensors() -> SensorDay:
    return SensorDay(date="2026-03-10", crew_id="T1", sleep_h=7.2, activity_min=48, hr_rest=58)


@pytest.fixture
def tired_sensors() -> SensorDay:
    # sono 2 desvios abaixo, frequência cardíaca 2 desvios acima
    return SensorDay(date="2026-03-10", crew_id="T1", sleep_h=6.0, activity_min=36, hr_rest=64)


def make_entry(text: str, day: int = 10, crew: str = "T1") -> Entry:
    return Entry(id=day, crew_id=crew, day=day, date=f"2026-03-{day:02d}", text=text)


def make_analysis(day: int, themes: list[str]) -> Analysis:
    return Analysis(
        entry_id=day, crew_id="T1", day=day, themes=themes, polarity=-0.5,
        z={"sleep": 0.0, "activity": 0.0, "hr": 0.0, "polarity": 0.0},
        persistence={}, alerts=[], confirmed_by={}, risk=50, band="amarelo",
        main_theme=themes[0] if themes else None, mood="neutro",
    )


@pytest.fixture(autouse=True)
def memoria_limpa():
    """O armazenamento em memória é global: cada teste começa do zero (só vale no modo memória)."""
    from storage import memory_db
    if os.environ.get("MINDORBIT_BACKEND") == "memory":
        for d in (memory_db._entries, memory_db._analyses, memory_db._directives, memory_db._countermeasures):
            d.clear()
        for k in [k for k in memory_db._settings if k.startswith(("day_", "weekly_sent_", "last_report_"))]:
            del memory_db._settings[k]
        memory_db._settings.update({"sim_day": "1", "blackout": "0"})
        memory_db._next.update({"entry": 1, "directive": 1, "cm": 1})
    yield
