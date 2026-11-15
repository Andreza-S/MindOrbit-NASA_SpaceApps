import storage
from ingest import source
from models import SensorDay


def test_sem_banco_usa_o_csv_e_o_padrao_de_exemplo(monkeypatch, tmp_path):
    import config
    monkeypatch.setattr(config, "BASELINE_DIR", tmp_path)     # sem arquivos de padrão: cai no exemplo
    monkeypatch.setattr(storage, "get_sensor_day", None, raising=False)
    monkeypatch.setattr(storage, "get_baseline", None, raising=False)
    s = source.sensor_for("T1", "2026-03-04")
    assert s is not None and s.crew_id == "T1"
    b, is_example = source.baseline_for("T1")
    assert b.crew_id == "T1" and is_example is True


def test_banco_tem_prioridade_sobre_o_csv(monkeypatch):
    from_db = SensorDay("2026-03-04", "T1", 5.0, 10, 70)
    monkeypatch.setattr(storage, "get_sensor_day", lambda c, d: from_db, raising=False)
    assert source.sensor_for("T1", "2026-03-04") is from_db


def test_banco_sem_o_dado_cai_para_o_csv(monkeypatch):
    monkeypatch.setattr(storage, "get_sensor_day", lambda c, d: None, raising=False)
    assert source.sensor_for("T1", "2026-03-04") is not None


def test_padrao_ausente_no_banco_cai_para_o_arquivo(monkeypatch):
    def missing(crew_id):
        raise KeyError(crew_id)
    monkeypatch.setattr(storage, "get_baseline", missing, raising=False)
    b, _ = source.baseline_for("T1")
    assert b.crew_id == "T1"


def test_sem_leitura_em_lugar_nenhum_devolve_none(monkeypatch):
    monkeypatch.setattr(storage, "get_sensor_day", None, raising=False)
    assert source.sensor_for("T1", "2030-01-01") is None
