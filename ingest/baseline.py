"""Leitura do padrão de bem-estar de cada astronauta (RF05)."""
import json
from pathlib import Path
from typing import Optional

import config
from models import Baseline

FIELDS = [
    "crew_id", "sleep_mean", "sleep_std", "activity_mean", "activity_std",
    "hr_mean", "hr_std", "polarity_mean", "polarity_std",
]


def load_baseline(crew_id: str, directory: Optional[Path] = None) -> Baseline:
    path = Path(directory or config.BASELINE_DIR) / f"{crew_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Padrão de bem-estar não encontrado: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    missing = [f for f in FIELDS if f not in raw]
    if missing:
        raise ValueError(f"{path.name} sem os campos: {', '.join(missing)}")
    return Baseline(
        crew_id=raw["crew_id"],
        sleep_mean=float(raw["sleep_mean"]), sleep_std=float(raw["sleep_std"]),
        activity_mean=float(raw["activity_mean"]), activity_std=float(raw["activity_std"]),
        hr_mean=float(raw["hr_mean"]), hr_std=float(raw["hr_std"]),
        polarity_mean=float(raw["polarity_mean"]), polarity_std=float(raw["polarity_std"]),
        usual_themes=list(raw.get("usual_themes", [])),
    )


def default_baseline(crew_id: str) -> Baseline:
    """Padrão de exemplo, usado só enquanto data/baselines/ não existir (desenvolvimento)."""
    return Baseline(
        crew_id=crew_id, sleep_mean=7.2, sleep_std=0.6, activity_mean=48, activity_std=12,
        hr_mean=58, hr_std=3, polarity_mean=0.15, polarity_std=0.2, usual_themes=[],
    )


def load_baseline_or_default(crew_id: str) -> tuple[Baseline, bool]:
    """(padrão, é_de_exemplo). Não esconde o erro de um JSON mal formado."""
    try:
        return load_baseline(crew_id), False
    except FileNotFoundError:
        return default_baseline(crew_id), True
