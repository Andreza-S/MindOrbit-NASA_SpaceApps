"""Setas de navegação: a lógica roda com um Streamlit de mentira (o app real não precisa estar aberto)."""
import sys
import types

import pytest

import demo_seed
import storage


@pytest.fixture
def nav(monkeypatch):
    fake = types.SimpleNamespace(session_state={})
    monkeypatch.setitem(sys.modules, "streamlit", fake)
    monkeypatch.delitem(sys.modules, "ui.day_nav", raising=False)
    import ui.day_nav as mod
    yield mod
    sys.modules.pop("ui.day_nav", None)


def test_voltar_mostra_o_dia_anterior_e_mantem_os_dados(nav):
    demo_seed.go_to_day(40)
    nav.voltar()
    assert int(storage.get_setting("sim_day")) == 39
    assert [a.day for a in storage.get_history("T1", 60)][-1] == 39
    assert len(demo_seed.all_analyses("T1")) == 40


def test_avancar_so_com_o_diario_de_todos(nav):
    demo_seed.go_to_day(20, include_day=False)
    nav.avancar()                                        # falta o diário do dia 20
    assert int(storage.get_setting("sim_day")) == 20
    nav.preencher()
    nav.avancar()
    assert int(storage.get_setting("sim_day")) == 21


def test_voltar_e_avancar_pelos_dias_ja_preenchidos(nav):
    demo_seed.go_to_day(30)
    nav.voltar(); nav.voltar()
    nav.avancar(); nav.avancar()                         # dias antigos já têm diário de todos
    assert int(storage.get_setting("sim_day")) == 30
    nav.avancar()                                        # o dia 31 não existe ainda
    assert int(storage.get_setting("sim_day")) == 31
    nav.avancar()
    assert int(storage.get_setting("sim_day")) == 31     # travado: faltam os diários do dia 31


def test_nao_passa_do_ultimo_dia_nem_antes_do_primeiro(nav):
    demo_seed.go_to_day(180)
    nav.avancar()
    assert int(storage.get_setting("sim_day")) == 180
    demo_seed.go_to_day(1)
    nav.voltar()
    assert int(storage.get_setting("sim_day")) == 1
