import config
import storage
import demo_seed
from core.pipeline import analyze_entry
from ingest.source import baseline_for, sensor_for
from models import CountermeasureLog, Entry
from storage import memory_db
from ui import earth_data


def test_agrupa_apoio_por_sugestao():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    rows = earth_data.support_rows("T1")
    titles = [r["contramedida"] for r in rows]
    assert len(titles) == len(set(titles))          # uma linha por sugestão
    assert all(set(r) == {"contramedida", "dias", "respostas"} for r in rows)


def test_contramedida_da_mesma_entrada_e_substituida():
    storage.set_setting("sim_day", "3")
    storage.save_countermeasure(CountermeasureLog(None, 5, "T1", 3, "sono", "Rotina de sono"))
    storage.save_countermeasure(CountermeasureLog(None, 5, "T1", 3, "geral", "Pausa curta"))
    logs = storage.list_countermeasures("T1", 14)
    assert [c.title for c in logs] == ["Pausa curta"]
