"""Banco SQLite do MindOrbit (Pessoa B).

Mesmas assinaturas do storage/memory_db.py da Pessoa A, mais as funções novas
do briefing (tripulação, padrão de bem-estar e sensores). Uma conexão por chamada,
porque o Streamlit reexecuta o script a cada clique.
"""
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import config
from models import Analysis, Baseline, CountermeasureLog, Directive, Entry, SensorDay

DB_PATH = Path(os.environ.get("MINDORBIT_DB", config.DATA_DIR / "mindorbit.db"))
SCHEMA = Path(__file__).with_name("schema.sql")
DEFAULT_SETTINGS = {"sim_day": "1", "blackout": "0", "delay_seconds": str(config.DEFAULT_DELAY_SECONDS),
                    "delay_mode": "jpl"}   # jpl = atraso real Terra–Marte (dados NASA/JPL); manual = slider
JSON_COLUMNS = ("themes", "z", "persistence", "alerts", "confirmed_by")
ANALYSIS_COLUMNS = ("entry_id", "crew_id", "day", "themes", "polarity", "z", "persistence", "alerts",
                    "confirmed_by", "risk", "band", "main_theme", "mood", "mood_confirmed")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def current_path() -> Path:
    """Banco em uso. Na hospedagem (MINDORBIT_PER_SESSION=1) cada visitante tem o seu, guardado na sessão
    do Streamlit; fora dela, é o arquivo padrão (MINDORBIT_DB ou data/mindorbit.db)."""
    from support.i18n import session_state
    state = session_state()
    if state is not None and state.get("db_path"):
        return Path(state["db_path"])
    return DB_PATH


def connect() -> sqlite3.Connection:
    path = current_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode = WAL")      # gravações bem mais rápidas (o seed fica em segundos)
    con.execute("PRAGMA synchronous = NORMAL")
    return con


def pseudonym_for(crew_id: str) -> str:
    """Um só pseudônimo na nave inteira: o mesmo do relatório da Terra (support/report.py)."""
    from support.report import pseudonym
    return pseudonym(crew_id)


def init_db(backfill: bool = True) -> None:
    """Pode ser chamado várias vezes: não apaga nada e só grava padrões que ainda não existem."""
    with connect() as con:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        cols = {r["name"] for r in con.execute("PRAGMA table_info(directives)")}
        if "ref" not in cols:          # bancos criados antes do aviso de leitura
            con.execute("ALTER TABLE directives ADD COLUMN ref INTEGER")
        for key, value in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        for crew_id in config.CREW_IDS:
            con.execute("INSERT OR IGNORE INTO crew (crew_id, pseudonym) VALUES (?, ?)",
                        (crew_id, pseudonym_for(crew_id)))
    if backfill and config.SENSORS_CSV.exists():
        from simulator import feed
        feed.backfill_until(int(get_setting("sim_day")))


# Configurações (sim_day, blackout, delay_seconds)
def get_setting(key: str) -> str:
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        if key in DEFAULT_SETTINGS:
            return DEFAULT_SETTINGS[key]
        raise KeyError(key)
    return row["value"]


def set_setting(key: str, value) -> None:
    with connect() as con:
        con.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))


def reset_demo() -> None:
    """Recomeça a demo: apaga diários, análises, contramedidas, mensagens, fila do link e o dia da missão.

    Mantém os padrões de bem-estar (baselines) e a tripulação. Os sensores são apagados e voltam a chegar
    dia a dia, como na missão. O atraso e o modo de atraso escolhidos na barra lateral são preservados.
    """
    with connect() as con:
        for table in ("entries", "analyses", "countermeasures", "directives", "link_queue",
                      "earth_reports", "earth_messages", "sensor_readings"):
            con.execute(f"DELETE FROM {table}")
        keep = ("delay_seconds", "delay_mode")
        con.execute("DELETE FROM settings WHERE key NOT IN (?, ?)", keep)
        for key, value in DEFAULT_SETTINGS.items():
            con.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    init_db()


# Diário e análises (mesmas assinaturas do memory_db)
def save_entry(e: Entry) -> int:
    with connect() as con:
        if e.id:
            con.execute("INSERT OR REPLACE INTO entries (id, crew_id, day, date, text, created_at) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (e.id, e.crew_id, e.day, e.date, e.text, _now()))
            return e.id
        cur = con.execute("INSERT INTO entries (crew_id, day, date, text, created_at) VALUES (?, ?, ?, ?, ?)",
                          (e.crew_id, e.day, e.date, e.text, _now()))
        return cur.lastrowid


def save_analysis(a: Analysis) -> None:
    """Upsert pelo entry_id: a correção do humor regrava a mesma análise."""
    values = [json.dumps(getattr(a, c), ensure_ascii=False) if c in JSON_COLUMNS else getattr(a, c)
              for c in ANALYSIS_COLUMNS]
    cols = ", ".join(ANALYSIS_COLUMNS)
    marks = ", ".join("?" for _ in ANALYSIS_COLUMNS)
    updates = ", ".join(f"{c} = excluded.{c}" for c in ANALYSIS_COLUMNS if c != "entry_id")
    with connect() as con:
        con.execute(f"INSERT INTO analyses ({cols}) VALUES ({marks}) "
                    f"ON CONFLICT(entry_id) DO UPDATE SET {updates}", values)


def _analysis(row) -> Analysis:
    d = dict(row)
    for c in JSON_COLUMNS:
        d[c] = json.loads(d[c])
    return Analysis(**{c: d[c] for c in ANALYSIS_COLUMNS})


def get_history(crew_id: str, last_days: int) -> list[Analysis]:
    """Análises dos dias sim_day - last_days + 1 até sim_day, em ordem de day (como o memory_db)."""
    sim_day = int(get_setting("sim_day"))
    with connect() as con:
        rows = con.execute("SELECT * FROM analyses WHERE crew_id = ? AND day BETWEEN ? AND ? "
                           "ORDER BY day, entry_id", (crew_id, sim_day - last_days + 1, sim_day)).fetchall()
    return [_analysis(r) for r in rows]


def list_entries_text(crew_id: str, day: int) -> str:
    """Só uso local: o texto do diário nunca sai da nave."""
    with connect() as con:
        rows = con.execute("SELECT text FROM entries WHERE crew_id = ? AND day = ? ORDER BY id",
                           (crew_id, day)).fetchall()
    return "\n".join(r["text"] for r in rows)


# Direcionamentos da Terra
def save_directive(d: Directive) -> int:
    with connect() as con:
        if d.id:
            con.execute("INSERT OR REPLACE INTO directives (id, crew_id, text, sent_at, read, ref) "
                        "VALUES (?, ?, ?, ?, ?, ?)", (d.id, d.crew_id, d.text, d.sent_at, int(d.read), d.ref))
            return d.id
        return con.execute("INSERT INTO directives (crew_id, text, sent_at, read, ref) VALUES (?, ?, ?, ?, ?)",
                           (d.crew_id, d.text, d.sent_at, int(d.read), d.ref)).lastrowid


def list_directives(crew_id: str) -> list[Directive]:
    with connect() as con:
        rows = con.execute("SELECT * FROM directives WHERE crew_id = ? ORDER BY id DESC", (crew_id,)).fetchall()
    return [Directive(id=r["id"], crew_id=r["crew_id"], text=r["text"], sent_at=r["sent_at"], read=bool(r["read"]),
                      ref=r["ref"])
            for r in rows]


def get_directive(directive_id: int) -> Optional[Directive]:
    with connect() as con:
        r = con.execute("SELECT * FROM directives WHERE id = ?", (directive_id,)).fetchone()
    return None if r is None else Directive(id=r["id"], crew_id=r["crew_id"], text=r["text"],
                                            sent_at=r["sent_at"], read=bool(r["read"]), ref=r["ref"])


def mark_read(directive_id: int) -> None:
    with connect() as con:
        con.execute("UPDATE directives SET read = 1 WHERE id = ?", (directive_id,))


# Acompanhamento da contramedida (RF18): mesmas assinaturas do memory_db
def _cm(r) -> CountermeasureLog:
    return CountermeasureLog(id=r["id"], entry_id=r["entry_id"], crew_id=r["crew_id"], day=r["day"],
                             theme=r["theme"], title=r["title"],
                             done=None if r["done"] is None else bool(r["done"]),
                             helped=None if r["helped"] is None else bool(r["helped"]))


def save_countermeasure(c: CountermeasureLog) -> int:
    """Uma contramedida por entrada: reescrever o diário do dia troca a sugestão."""
    with connect() as con:
        con.execute("DELETE FROM countermeasures WHERE entry_id = ? AND crew_id = ?", (c.entry_id, c.crew_id))
        done = None if c.done is None else int(c.done)
        helped = None if c.helped is None else int(c.helped)
        if c.id:
            con.execute("INSERT OR REPLACE INTO countermeasures (id, entry_id, crew_id, day, theme, title, done, helped)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (c.id, c.entry_id, c.crew_id, c.day, c.theme, c.title, done, helped))
            return c.id
        return con.execute("INSERT INTO countermeasures (entry_id, crew_id, day, theme, title, done, helped)"
                           " VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (c.entry_id, c.crew_id, c.day, c.theme, c.title, done, helped)).lastrowid


def get_pending_followup(crew_id: str, day: int, max_days: int = 3) -> Optional[CountermeasureLog]:
    """Contramedida mais recente, de um dia anterior, ainda sem resposta."""
    with connect() as con:
        r = con.execute("SELECT * FROM countermeasures WHERE crew_id = ? AND done IS NULL "
                        "AND ? - day > 0 AND ? - day <= ? ORDER BY day DESC, id DESC LIMIT 1",
                        (crew_id, day, day, max_days)).fetchone()
    return _cm(r) if r else None


def record_followup(cm_id: int, done: bool, helped: Optional[bool]) -> None:
    with connect() as con:
        con.execute("UPDATE countermeasures SET done = ?, helped = ? WHERE id = ?",
                    (int(done), int(helped) if (done and helped is not None) else None, cm_id))


def list_countermeasures(crew_id: str, last_days: int) -> list[CountermeasureLog]:
    sim_day = int(get_setting("sim_day"))
    with connect() as con:
        rows = con.execute("SELECT * FROM countermeasures WHERE crew_id = ? AND day > ? AND day <= ? "
                           "ORDER BY day, id", (crew_id, sim_day - last_days, sim_day)).fetchall()
    return [_cm(r) for r in rows]


# Tripulação e padrão de bem-estar (novas)
def list_crew() -> list[str]:
    with connect() as con:
        return [r["crew_id"] for r in con.execute("SELECT crew_id FROM crew ORDER BY crew_id")]


def get_pseudonym(crew_id: str) -> Optional[str]:
    with connect() as con:
        r = con.execute("SELECT pseudonym FROM crew WHERE crew_id = ?", (crew_id,)).fetchone()
    return r["pseudonym"] if r else None


def save_baseline(b: Baseline, source: str = "simulated") -> None:
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO crew (crew_id, pseudonym) VALUES (?, ?)", (b.crew_id, pseudonym_for(b.crew_id)))
        con.execute(
            """INSERT INTO baselines (crew_id, sleep_mean, sleep_std, activity_mean, activity_std, hr_mean, hr_std,
                                      polarity_mean, polarity_std, usual_themes, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(crew_id) DO UPDATE SET
                 sleep_mean = excluded.sleep_mean, sleep_std = excluded.sleep_std,
                 activity_mean = excluded.activity_mean, activity_std = excluded.activity_std,
                 hr_mean = excluded.hr_mean, hr_std = excluded.hr_std,
                 polarity_mean = excluded.polarity_mean, polarity_std = excluded.polarity_std,
                 usual_themes = excluded.usual_themes, source = excluded.source, created_at = excluded.created_at""",
            (b.crew_id, b.sleep_mean, b.sleep_std, b.activity_mean, b.activity_std, b.hr_mean, b.hr_std,
             b.polarity_mean, b.polarity_std, json.dumps(list(b.usual_themes), ensure_ascii=False), source, _now()))


def get_baseline(crew_id: str) -> Baseline:
    with connect() as con:
        r = con.execute("SELECT * FROM baselines WHERE crew_id = ?", (crew_id,)).fetchone()
    if r is None:
        raise KeyError(f"Sem padrão de bem-estar para {crew_id}. Rode: python -m simulator.generate")
    return Baseline(crew_id=r["crew_id"], sleep_mean=r["sleep_mean"], sleep_std=r["sleep_std"],
                    activity_mean=r["activity_mean"], activity_std=r["activity_std"],
                    hr_mean=r["hr_mean"], hr_std=r["hr_std"],
                    polarity_mean=r["polarity_mean"], polarity_std=r["polarity_std"],
                    usual_themes=json.loads(r["usual_themes"]))


# Sensores (novas). sensor_readings é de uso só da nave.
def _sensor(r) -> SensorDay:
    return SensorDay(date=r["date"], crew_id=r["crew_id"], sleep_h=r["sleep_h"],
                     activity_min=r["activity_min"], hr_rest=r["hr_rest"])


def save_sensor_day(s: SensorDay, day: int, source: str = "simulated") -> None:
    """Upsert por (crew_id, date)."""
    with connect() as con:
        con.execute(
            """INSERT INTO sensor_readings (crew_id, day, date, sleep_h, activity_min, hr_rest, source, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(crew_id, date) DO UPDATE SET
                 day = excluded.day, sleep_h = excluded.sleep_h, activity_min = excluded.activity_min,
                 hr_rest = excluded.hr_rest, source = excluded.source, received_at = excluded.received_at""",
            (s.crew_id, day, s.date, s.sleep_h, s.activity_min, s.hr_rest, source, _now()))


def insert_sensor_day_if_absent(s: SensorDay, day: int, source: str = "simulated") -> bool:
    """Usado pelo feed (INSERT OR IGNORE). True se gravou uma linha nova."""
    with connect() as con:
        cur = con.execute(
            """INSERT OR IGNORE INTO sensor_readings
               (crew_id, day, date, sleep_h, activity_min, hr_rest, source, received_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (s.crew_id, day, s.date, s.sleep_h, s.activity_min, s.hr_rest, source, _now()))
        return cur.rowcount == 1


def get_sensor_day(crew_id: str, date: str) -> Optional[SensorDay]:
    with connect() as con:
        r = con.execute("SELECT * FROM sensor_readings WHERE crew_id = ? AND date = ?", (crew_id, date)).fetchone()
    return _sensor(r) if r else None


def list_sensor_days(crew_id: str, first_day: int, last_day: int) -> list[SensorDay]:
    with connect() as con:
        rows = con.execute("SELECT * FROM sensor_readings WHERE crew_id = ? AND day BETWEEN ? AND ? ORDER BY day",
                           (crew_id, first_day, last_day)).fetchall()
    return [_sensor(r) for r in rows]


def last_sensor_received(up_to_day: Optional[int] = None) -> Optional[dict]:
    """Opcional na barra lateral: a última leitura recebida (até o dia pedido, se for dado)."""
    with connect() as con:
        r = con.execute("SELECT day, received_at FROM sensor_readings WHERE day <= ? "
                        "ORDER BY day DESC LIMIT 1", (up_to_day if up_to_day is not None else 10**6,)).fetchone()
    return dict(r) if r else None
