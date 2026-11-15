from models import CountermeasureLog
from storage import memory_db as db


def _log(day, crew="T9"):
    return CountermeasureLog(None, 1, crew, day, "ansiedade", "Respiração guiada de 3 minutos")


def test_pergunta_no_dia_seguinte_e_some_depois_de_responder():
    cm_id = db.save_countermeasure(_log(day=5))
    assert db.get_pending_followup("T9", 5) is None          # no mesmo dia, não pergunta
    pend = db.get_pending_followup("T9", 6)
    assert pend is not None and pend.id == cm_id
    db.record_followup(cm_id, True, True)
    assert db.get_pending_followup("T9", 6) is None
    db.set_setting("sim_day", "6")
    feito = [c for c in db.list_countermeasures("T9", 3) if c.id == cm_id][0]
    assert feito.done is True and feito.helped is True


def test_para_de_perguntar_depois_de_alguns_dias():
    db.save_countermeasure(_log(day=20, crew="T8"))
    assert db.get_pending_followup("T8", 23) is not None
    assert db.get_pending_followup("T8", 24) is None


def test_nao_fiz_nao_registra_ajuda():
    cm_id = db.save_countermeasure(_log(day=30, crew="T7"))
    db.record_followup(cm_id, False, True)
    c = db._countermeasures[cm_id]
    assert c.done is False and c.helped is None
