"""Leitura do CSV de sensores (contrato de entrada, RF01)."""
from pathlib import Path
from typing import Optional

import pandas as pd

import config
from models import SensorDay

REQUIRED_COLUMNS = ["date", "crew_id", "sleep_h", "activity_min", "hr_rest"]


def load_sensors(path: Optional[Path] = None) -> dict[tuple[str, str], SensorDay]:
    """Devolve {(crew_id, date): SensorDay}. Erro claro se faltar coluna."""
    path = Path(path or config.SENSORS_CSV)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de sensores não encontrado: {path}")
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV de sensores sem as colunas: {', '.join(missing)}")
    out: dict[tuple[str, str], SensorDay] = {}
    for row in df.itertuples(index=False):
        sd = SensorDay(
            date=str(row.date),
            crew_id=str(row.crew_id),
            sleep_h=float(row.sleep_h),
            activity_min=float(row.activity_min),
            hr_rest=float(row.hr_rest),
        )
        out[(sd.crew_id, sd.date)] = sd
    return out


def get_sensor_day(sensors: dict, crew_id: str, date: str) -> Optional[SensorDay]:
    return sensors.get((crew_id, date))
