"""Um banco por visitante (hospedagem): sessões não dividem o dia da missão nem os diários."""
import os
import time

import pytest

from storage import db, session_db
from support import i18n


@pytest.fixture
def sessoes(tmp_path, monkeypatch):
    monkeypatch.setenv("MINDORBIT_SESSION_DIR", str(tmp_path / "sessoes"))
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "padrao.db")
    atual = {}
    monkeypatch.setattr(i18n, "session_state", lambda: atual)
    return atual


def _entra(estado, path):
    estado.clear()
    if path:
        estado["db_path"] = str(path)


def test_cada_sessao_tem_o_seu_banco(sessoes):
    a, b = session_db.new_path(), session_db.new_path()
    assert a != b and a.parent == b.parent
    _entra(sessoes, a); db.init_db(backfill=False); db.set_setting("sim_day", "5")
    _entra(sessoes, b); db.init_db(backfill=False)
    assert db.get_setting("sim_day") == "1"          # a outra sessão não mexeu neste
    _entra(sessoes, a)
    assert db.get_setting("sim_day") == "5"
    assert db.current_path() == a


def test_sem_sessao_usa_o_banco_padrao(sessoes, tmp_path):
    _entra(sessoes, None)
    assert db.current_path() == tmp_path / "padrao.db"


def test_limpeza_apaga_so_os_antigos(sessoes):
    velho, novo = session_db.new_path(), session_db.new_path()
    for p in (velho, novo):
        p.write_text("x"); p.with_name(p.name + "-wal").write_text("x")
    antes = time.time() - 13 * 3600
    for p in (velho, velho.with_name(velho.name + "-wal")):
        os.utime(p, (antes, antes))
    assert session_db.cleanup() == 1
    assert not velho.exists() and not velho.with_name(velho.name + "-wal").exists()
    assert novo.exists()


def test_ligado_por_variavel_de_ambiente(monkeypatch):
    monkeypatch.delenv("MINDORBIT_PER_SESSION", raising=False)
    assert not session_db.enabled()
    monkeypatch.setenv("MINDORBIT_PER_SESSION", "1")
    assert session_db.enabled()
