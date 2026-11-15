"""Armazenamento em memória, com as MESMAS assinaturas do storage/db.py da Pessoa B.

Serve para a Pessoa A desenvolver sem esperar o SQLite. Quando storage/db.py
existir, o pacote `storage` passa a usá-lo automaticamente (ver storage/__init__.py).
"""
from dataclasses import replace
from typing import Optional

from models import Analysis, CountermeasureLog, Directive, Entry

_entries: dict[int, Entry] = {}
_analyses: dict[int, Analysis] = {}     # chave: entry_id (save_analysis é um "upsert")
_directives: dict[int, Directive] = {}
_settings: dict[str, str] = {"sim_day": "1", "blackout": "0", "delay_seconds": "10", "delay_mode": "jpl"}
_countermeasures: dict[int, CountermeasureLog] = {}
_next = {"entry": 1, "directive": 1, "cm": 1}


def init_db() -> None:
    return None


def reset_demo() -> None:
    """Recomeça a demo: apaga tudo e volta ao dia 1."""
    for d in (_entries, _analyses, _directives, _countermeasures):
        d.clear()
    keep = {k: v for k, v in _settings.items() if k in ("delay_seconds", "delay_mode")}
    _settings.clear()
    _settings.update({"sim_day": "1", "blackout": "0", "delay_seconds": "10", "delay_mode": "jpl"})
    _settings.update(keep)
    _next.update({"entry": 1, "directive": 1, "cm": 1})


def save_entry(e: Entry) -> int:
    entry_id = e.id or _next["entry"]
    _next["entry"] = max(_next["entry"], entry_id) + 1
    _entries[entry_id] = replace(e, id=entry_id)
    return entry_id


def save_analysis(a: Analysis) -> None:
    _analyses[a.entry_id] = a


def get_history(crew_id: str, last_days: int) -> list[Analysis]:
    sim_day = int(get_setting("sim_day"))
    first = sim_day - last_days + 1
    out = [a for a in _analyses.values()
           if a.crew_id == crew_id and first <= a.day <= sim_day]
    return sorted(out, key=lambda a: (a.day, a.entry_id))


def list_entries_text(crew_id: str, day: int) -> str:
    """Só uso local: o texto do diário nunca sai da nave."""
    return "\n".join(e.text for e in _entries.values() if e.crew_id == crew_id and e.day == day)


def get_setting(key: str) -> str:
    return _settings[key]


def set_setting(key: str, value: str) -> None:
    _settings[key] = str(value)


def save_directive(d: Directive) -> int:
    directive_id = d.id or _next["directive"]
    _next["directive"] = max(_next["directive"], directive_id) + 1
    _directives[directive_id] = replace(d, id=directive_id)
    return directive_id


def list_directives(crew_id: str) -> list[Directive]:
    return sorted((d for d in _directives.values() if d.crew_id == crew_id),
                  key=lambda d: d.id or 0, reverse=True)


def mark_read(directive_id: int) -> None:
    if directive_id in _directives:
        _directives[directive_id].read = True


# --- Acompanhamento da contramedida (RF18) ---
def save_countermeasure(c: CountermeasureLog) -> int:
    # Uma contramedida por entrada: reescrever o diário do dia troca a sugestão
    for old_id, old in list(_countermeasures.items()):
        if old.entry_id == c.entry_id and old.crew_id == c.crew_id:
            del _countermeasures[old_id]
    cm_id = c.id or _next["cm"]
    _next["cm"] = max(_next["cm"], cm_id) + 1
    _countermeasures[cm_id] = replace(c, id=cm_id)
    return cm_id


def get_pending_followup(crew_id: str, day: int, max_days: int = 3) -> Optional[CountermeasureLog]:
    """Contramedida mais recente, de um dia anterior, ainda sem resposta."""
    pending = [c for c in _countermeasures.values()
               if c.crew_id == crew_id and c.done is None and 0 < day - c.day <= max_days]
    return max(pending, key=lambda c: (c.day, c.id or 0), default=None)


def record_followup(cm_id: int, done: bool, helped: Optional[bool]) -> None:
    c = _countermeasures.get(cm_id)
    if c:
        c.done, c.helped = done, (helped if done else None)


def list_countermeasures(crew_id: str, last_days: int) -> list[CountermeasureLog]:
    sim_day = int(get_setting("sim_day"))
    return sorted((c for c in _countermeasures.values()
                   if c.crew_id == crew_id and sim_day - last_days < c.day <= sim_day),
                  key=lambda c: (c.day, c.id or 0))
