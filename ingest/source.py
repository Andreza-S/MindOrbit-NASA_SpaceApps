"""Fonte única de sensores e padrões de bem-estar.

Usa o banco da Pessoa B quando ele oferece `get_sensor_day` / `get_baseline`
(storage/db.py) e, se não oferecer ou não tiver o dado, cai para os arquivos
`data/sensores.csv` e `data/baselines/*.json`. A aba do astronauta só chama estas funções.
"""
from functools import lru_cache
from typing import Optional

import storage
from ingest.baseline import load_baseline_or_default
from ingest.sensors import get_sensor_day as _csv_day, load_sensors
from models import Baseline, SensorDay


@lru_cache(maxsize=1)
def _csv() -> dict:
    try:
        return load_sensors()
    except FileNotFoundError:
        return {}


def sensor_for(crew_id: str, date: str) -> Optional[SensorDay]:
    """Leitura do dia: banco primeiro, CSV como reserva, None se não houver."""
    from_db = getattr(storage, "get_sensor_day", None)
    if from_db:
        found = from_db(crew_id, date)
        if found is not None:
            return found
    return _csv_day(_csv(), crew_id, date)


def baseline_for(crew_id: str) -> tuple[Baseline, bool]:
    """(padrão, é_de_exemplo): banco, depois JSON, depois um padrão de exemplo."""
    from_db = getattr(storage, "get_baseline", None)
    if from_db:
        try:
            found = from_db(crew_id)
        except LookupError:
            found = None
        if found is not None:
            return found, False
    return load_baseline_or_default(crew_id)
