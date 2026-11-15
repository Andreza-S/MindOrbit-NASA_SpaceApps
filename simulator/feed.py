"""Chegada dos sensores "em tempo real" (Pessoa B).

O data/sensores.csv faz o papel da fonte da missão. Cada dia só é copiado para o banco
quando o dia da missão chega a ele: a aba do astronauta nunca vê dias futuros.
"""
import csv
from functools import lru_cache

import config
from models import SensorDay
from storage import db

CSV_PATH = config.SENSORS_CSV
ULTIMO_DIA = 180


@lru_cache(maxsize=1)
def _por_data(mtime: float) -> dict:
    linhas = {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = SensorDay(date=r["date"], crew_id=r["crew_id"], sleep_h=float(r["sleep_h"]),
                          activity_min=float(r["activity_min"]), hr_rest=float(r["hr_rest"]))
            linhas.setdefault(s.date, []).append(s)
    return linhas


def ingest_day(day: int) -> int:
    """Grava as leituras do dia. Idempotente. Nunca grava dia maior que sim_day. Devolve quantas gravou."""
    if day < 1 or day > min(int(db.get_setting("sim_day")), ULTIMO_DIA):
        return 0
    leituras = _por_data(CSV_PATH.stat().st_mtime).get(config.date_for_day(day), [])
    return sum(db.insert_sensor_day_if_absent(s, day) for s in leituras)


def backfill_until(day: int) -> None:
    """Garante que os dias 1..day (limitado a sim_day) existam no banco."""
    for d in range(1, min(day, int(db.get_setting("sim_day")), ULTIMO_DIA) + 1):
        ingest_day(d)


def advance_day() -> int:
    """Botão "Avançar dia": sim_day + 1 e chegada das leituras desse dia. Devolve o novo sim_day."""
    novo = min(int(db.get_setting("sim_day")) + 1, ULTIMO_DIA)
    db.set_setting("sim_day", novo)
    ingest_day(novo)
    return novo


def go_to_episode(crew_id: str) -> int:
    """Botão "Ir para o episódio": 3 dias antes do início do episódio do tripulante."""
    from simulator.generate import EPISODES
    ep = EPISODES.get(crew_id)
    if not ep:
        return int(db.get_setting("sim_day"))
    dia = max(1, ep["start"] - 3)
    db.set_setting("sim_day", dia)
    backfill_until(dia)
    return dia
