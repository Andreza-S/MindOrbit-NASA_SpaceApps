import re

import pytest

import demo_seed
import storage
from support import explain as ex
from support import report as r


def _all(crew):
    storage.set_setting("sim_day", "180")
    try:
        return storage.get_history(crew, 180)
    finally:
        storage.set_setting("sim_day", "1")


def test_pontos_somam_o_indice_em_todos_os_dias():
    demo_seed.go_to_day(120, crew_ids=["T1", "T2"])
    analyses = _all("T1") + _all("T2")
    assert analyses
    for a in analyses:
        e = ex.explain(a)
        assert abs(sum(e.points.values()) - a.risk) <= 0.51, (a.crew_id, a.day)
        for k, v in e.points.items():
            assert 0 <= v <= e.maximum[k] + 1e-9


def test_texto_do_astronauta_nao_traz_pesos_nem_pontos():
    demo_seed.go_to_day(120, crew_ids=["T1", "T2"])
    for a in _all("T1") + _all("T2"):
        text = ex.astronaut_text(a)
        assert "pontos" not in text and "%" not in text and "35" not in text
        # só pode haver números na contagem de dias da janela
        assert all(n in {str(i) for i in range(2, 8)} for n in re.findall(r"\d+", text))


def test_t2_vermelho_cita_saudade_e_atividade():
    demo_seed.go_to_day(114, crew_ids=["T2"])
    last = _all("T2")[-1]
    text = ex.astronaut_text(last)
    assert text.startswith("O que mais pesou hoje:") and "saudade" in text
    assert "atividade" in text or "tom do seu diário" in text


def test_dia_de_recuperacao_explica_a_queda():
    demo_seed.go_to_day(70, crew_ids=["T1"])
    day69 = [a for a in _all("T1") if a.day == 69][0]       # T1 sai do episódio
    e = ex.explain(day69)
    assert any("reduzida" in n for n in e.notes)


def test_relatorio_clinico_traz_a_composicao():
    demo_seed.go_to_day(114, crew_ids=["T2"])
    rep = r.build_report("T2")
    assert set(rep.risk_breakdown) == {"tone", "persistence", "sensors"}
    assert abs(sum(rep.risk_breakdown.values()) - rep.risk) <= 1.0
    assert isinstance(rep.breakdown_notes, list)
