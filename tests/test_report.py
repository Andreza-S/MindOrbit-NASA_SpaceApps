import dataclasses
import json

import pytest

import demo_seed
import storage
from models import Analysis
from storage import memory_db
from support import report as r


def _a(day, band):
    return Analysis(day, "T1", day, [], 0.0, {}, {}, [], {}, 80 if band == "vermelho" else 10,
                    band, None, "neutro")


def test_sem_historico_nao_gera_relatorio():
    assert r.build_report("T4") is None


def test_relatorio_sem_texto_sem_numeros_brutos_e_com_pseudonimo():
    demo_seed.go_to_day(112, crew_ids=["T2"])
    rep = r.build_report("T2")
    d = dataclasses.asdict(rep)
    blob = json.dumps(d, ensure_ascii=False)
    assert "T2" not in blob and "2026-" not in blob       # sem código real e sem datas de calendário
    assert rep.pseudonym == r.pseudonym("T2") and rep.pseudonym.startswith("A-")
    assert rep.kind == "imediato" and rep.immediate and rep.band == "vermelho"
    assert rep.period_start_day == 106 and rep.period_end_day == 112 and rep.mission_total_days == 180
    assert set(rep.sensor_dev) == {"sleep", "activity", "hr"}
    assert all(v in {"dentro", "abaixo", "bem abaixo", "acima", "bem acima"} for v in rep.sensor_dev.values())
    assert rep.alert_reasons and all(isinstance(x, str) for x in rep.alert_reasons)
    for s in rep.support:
        assert set(s) == {"title", "days", "answer"}


def test_humor_so_se_confirmado():
    demo_seed.go_to_day(112, crew_ids=["T2"])
    assert r.build_report("T2").mood is None
    last = storage.get_history("T2", 7)[-1]
    last.mood_confirmed = "com saudade"
    assert r.build_report("T2").mood == "com saudade"


def test_niveis_de_sensor():
    assert r.sensor_level("sleep", -2.0) == "bem abaixo"
    assert r.sensor_level("sleep", -1.0) == "abaixo"
    assert r.sensor_level("hr", 1.0) == "acima"
    assert r.sensor_level("activity", 0.3) == "dentro"
    assert r.sensor_phrase("sleep", "bem abaixo") == "sono: bem abaixo do seu padrão"


def test_imediato_so_ao_entrar_no_vermelho():
    assert r.entered_red(_a(5, "vermelho"), [_a(4, "amarelo")])
    assert not r.entered_red(_a(6, "vermelho"), [_a(5, "vermelho")])
    assert r.entered_red(_a(1, "vermelho"), [])
    assert not r.entered_red(_a(5, "amarelo"), [_a(4, "verde")])


def test_semanal_automatico_a_cada_7_dias_uma_vez():
    sent = []
    send = lambda crew, immediate: sent.append((crew, immediate))
    assert r.after_entry("T1", _a(6, "verde"), [], send) == []
    assert r.after_entry("T1", _a(7, "verde"), [], send) == ["semanal"]
    assert r.after_entry("T1", _a(7, "verde"), [], send) == []      # não repete no mesmo dia
    assert r.after_entry("T1", _a(14, "vermelho"), [_a(13, "amarelo")], send) == ["imediato", "semanal"]
    assert sent == [("T1", False), ("T1", True), ("T1", False)]


def test_inicio_da_piora_e_qualidade_dos_dados():
    demo_seed.go_to_day(69, crew_ids=["T1"])
    rep = r.build_report("T1")
    assert rep.band == "verde" and rep.onset_day is None          # T1 já saiu do episódio no dia 69
    assert rep.missing_diary_days == [] and rep.data_days["diario"] == rep.data_days["janela"]
    demo_seed.go_to_day(113, crew_ids=["T2"])
    t2 = r.build_report("T2")
    assert t2.onset_day is not None and 107 <= t2.onset_day <= 111
    assert t2.data_days["sensores"] == 7


def test_dias_sem_entrada_aparecem():
    demo_seed.go_to_day(70, crew_ids=["T1"])
    for a in [a for a in memory_db._analyses.values() if a.crew_id == "T1" and a.day in (68, 69)]:
        del memory_db._analyses[a.entry_id]
    assert r.build_report("T1").missing_diary_days == [68, 69]


def test_discordancia_texto_sem_queixa_com_sensor_ruim():
    a = _a(5, "verde")
    a.z = {"sleep": -2.0, "activity": 0.0, "hr": 0.0, "polarity": 0.3}
    assert r._discordance(a, {"sleep": "bem abaixo", "activity": "dentro", "hr": "dentro"}) == [
        "texto sem queixas, mas sono: bem abaixo do seu padrão"]
    a.themes = ["sobrecarga"]
    assert r._discordance(a, {"sleep": "bem abaixo"}) == []


def test_mensagem_da_terra_lida_ou_nao():
    from models import Directive
    demo_seed.go_to_day(10, crew_ids=["T1"])
    assert r.build_report("T1").last_directive_read is None
    memory_db.save_directive(Directive(None, "T1", "Como você está?", "dia 9"))
    assert r.build_report("T1").last_directive_read is False
    memory_db.mark_read(1)
    assert r.build_report("T1").last_directive_read is True


def test_aviso_registra_o_ultimo_envio_por_tipo():
    assert r.last_sent("T1") is None
    r.after_entry("T1", _a(7, "vermelho"), [_a(6, "amarelo")], lambda c, i: None)
    assert (r.last_sent("T1").day, r.last_sent("T1").kind) == (7, "imediato")   # no mesmo dia, o imediato
    assert r.last_sent("T1", "semanal").day == 7
    r.record_sent("T1", 9, "semanal")
    assert (r.last_sent("T1").day, r.last_sent("T1").kind) == (9, "semanal")


def test_proximo_semanal():
    assert r.next_weekly_day("T1", 3) == 7
    assert r.next_weekly_day("T1", 7) == 7                # ainda não enviado: é hoje
    storage.set_setting("weekly_sent_T1", "7")
    assert r.next_weekly_day("T1", 7) == 14
    assert r.next_weekly_day("T1", 10) == 14


def test_textos_do_aviso():
    assert r.notice_text("T1", 3, "verde") == (
        "Nenhum relatório enviado ainda. O próximo segue automaticamente no dia 7 da missão.")
    r.after_entry("T1", _a(7, "verde"), [], lambda c, i: None)
    assert r.notice_text("T1", 7, "verde") == (
        "A equipe de saúde da Terra recebeu o seu relatório semanal hoje (dia 7). O próximo segue no dia 14.")
    assert "no dia 7. O próximo segue no dia 14" in r.notice_text("T1", 9, "verde")
    r.after_entry("T1", _a(10, "vermelho"), [_a(9, "amarelo")], lambda c, i: None)
    assert r.notice_text("T1", 10, "vermelho") == (
        "A equipe de saúde da Terra foi avisada hoje (dia 10) e vai acompanhar você.")
    # na crise, continua mostrando que a Terra foi avisada, mesmo com um semanal mais recente
    r.record_sent("T1", 14, "semanal")
    assert "foi avisada no dia 10" in r.notice_text("T1", 14, "vermelho")


def test_aviso_de_fila_durante_blackout():
    storage.set_setting("blackout", "1")
    try:
        r.after_entry("T1", _a(10, "vermelho"), [_a(9, "amarelo")], lambda c, i: None)
        assert r.notice_text("T1", 10, "vermelho") == (
            "O relatório está na fila e segue assim que o link voltar. "
            "O seu apoio a bordo continua funcionando.")
        storage.set_setting("blackout", "0")             # o link voltou
        assert "foi avisada hoje (dia 10)" in r.notice_text("T1", 10, "vermelho")
    finally:
        storage.set_setting("blackout", "0")


def test_salto_na_missao_simula_os_relatorios_automaticos():
    demo_seed.go_to_day(114, crew_ids=["T1", "T2"])
    imediato, semanal = r.last_sent("T2", "imediato"), r.last_sent("T2", "semanal")
    assert imediato.day == 111                      # T2 entrou no vermelho no dia 111
    assert semanal.day == 112                       # último múltiplo de 7 até o dia 114
    assert "foi avisada no dia 111" in r.notice_text("T2", 114, "vermelho")
    assert r.last_sent("T1", "semanal").day == 112 and r.last_sent("T1", "imediato").day == 65
    assert "recebeu o seu relatório semanal no dia 112" in r.notice_text("T1", 114, "verde")


def test_voltar_no_tempo_ajusta_o_aviso():
    demo_seed.go_to_day(114, crew_ids=["T2"])
    demo_seed.go_to_day(30, crew_ids=["T2"])
    assert r.last_sent("T2", "imediato") is None
    assert r.last_sent("T2", "semanal").day == 28
    assert "no dia 28" in r.notice_text("T2", 30, "verde")


def test_resumo_em_linguagem_clara_sem_datas_nem_codigo():
    demo_seed.go_to_day(114, crew_ids=["T2"])
    rep = r.build_report("T2")
    assert rep.summary.startswith("Dias 108 a 114 da missão: índice 83, faixa vermelha.")
    assert "A piora começou no dia 111" in rep.summary and "mais alto" in rep.summary
    assert "2026-" not in rep.summary and "T2" not in rep.summary
    demo_seed.go_to_day(30, crew_ids=["T4"])
    verde = r.build_report("T4")
    assert "faixa verde" in verde.summary and "Sem piora em curso." in verde.summary
    assert "Nenhum episódio no vermelho até agora" in verde.summary


def test_semana_em_perspectiva():
    demo_seed.go_to_day(114, crew_ids=["T2"])
    rep = r.build_report("T2")
    assert len(rep.trend) == len(rep.trend_days) == len(rep.trend_bands) == 7
    assert rep.week["worst"] == 83 and rep.week["worst_day"] == 114
    assert sum(rep.week["bands"].values()) == rep.week["days"] == 7
    assert rep.prev_week["bands"]["verde"] == 7 and rep.week["mean"] > rep.prev_week["mean"]
    demo_seed.go_to_day(5, crew_ids=["T3"])
    assert r.build_report("T3").prev_week is None            # ainda não existe semana anterior


def test_tendencia_dos_sensores_e_composicao_em_palavras():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    rep = r.build_report("T1")
    assert set(rep.sensor_days_off) == {"sleep", "activity", "hr"} and rep.sensor_days_off["sleep"] >= 5
    assert all(0 <= n <= 7 for n in rep.sensor_days_off.values())
    assert set(rep.breakdown_why) == {"tone", "persistence", "sensors"}
    assert "cansaço e sono" in rep.breakdown_why["persistence"]
    assert all(isinstance(t, str) and t for t in rep.breakdown_why.values())


def test_contexto_da_missao_lista_episodios():
    demo_seed.go_to_day(180, crew_ids=["T2"])
    ctx = r.build_report("T2").mission_context
    assert ctx["days_total"] == 180 and ctx["days_not_green"] >= 8
    assert len(ctx["episodes"]) == 1
    ep = ctx["episodes"][0]
    assert 108 <= ep["start"] <= 112 and ep["end"] >= 118 and ep["peak"] >= 80 and not ep["ongoing"]
    assert "1 episódio anterior" in r.build_report("T2").summary
    demo_seed.go_to_day(114, crew_ids=["T1"])
    demo_seed.go_to_day(114, crew_ids=["T2"])
    assert r.build_report("T2").mission_context["episodes"][-1]["ongoing"]


def test_tema_habitual_e_marcado():
    demo_seed.go_to_day(30, crew_ids=["T1"])
    a = r.build_report("T1")
    assert isinstance(a.habitual_themes, list)
    assert set(a.habitual_themes) <= set(a.theme_days)


def test_relatorio_traz_os_contextos_e_o_resumo_cita_o_que_foge_do_habitual():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    rep = r.build_report("T1")
    assert rep.contexts["recurring"][0]["theme"] == "cansaco_sono"
    assert any(i["kind"] == "tema_novo" for i in rep.contexts["out_of_norm"])
    assert "Fora do habitual: Cansaço e sono apareceu em 7 dias" in rep.summary
    blob = json.dumps(rep.contexts, ensure_ascii=False)
    assert "2026-" not in blob and "T1" not in blob
