import json

import demo_seed
from ingest.source import baseline_for
from models import Analysis
from support import contexts


def _a(day, themes=(), z=None, band="verde"):
    zz = {"sleep": 0.0, "activity": 0.0, "hr": 0.0, "polarity": 0.0}
    zz.update(z or {})
    return Analysis(day, "T1", day, list(themes), 0.0, zz, {}, [], {}, 10, band,
                    themes[0] if themes else None, "neutro")


def _kinds(ctx):
    return [i["kind"] for i in ctx["out_of_norm"]]


def test_tema_recorrente_exige_dois_dias_e_mostra_a_tendencia():
    antes = [_a(d) for d in range(1, 8)]
    semana = [_a(8), _a(9, ["saudade_isolamento"]), _a(10), _a(11, ["saudade_isolamento"]),
              _a(12, ["saudade_isolamento"]), _a(13), _a(14)]
    ctx = contexts.build(antes + semana, 8, 14, ["sobrecarga"])
    assert [r["theme"] for r in ctx["recurring"]] == ["saudade_isolamento"]
    rec = ctx["recurring"][0]
    assert rec["days"] == 3 and rec["of"] == 7 and rec["last_day"] == 12 and rec["trend"] == "novo neste período"
    assert "tema_novo" in _kinds(ctx)


def test_uma_unica_vez_so_aparece_se_foge_do_habitual():
    base = [_a(d) for d in range(1, 8)]
    # tema que NÃO é habitual, uma única vez: aparece como fora do habitual (só categoria e dia)
    ctx = contexts.build(base + [_a(8, ["conflito"])] + [_a(d) for d in range(9, 15)], 8, 14, ["sobrecarga"])
    assert ctx["recurring"] == [] and _kinds(ctx) == ["unica_vez"]
    assert "tensão com a tripulação" in ctx["out_of_norm"][0]["text"].lower() and "dia 8" in ctx["out_of_norm"][0]["text"]
    # tema habitual, uma única vez: é normal para ele, não aparece
    ctx = contexts.build(base + [_a(8, ["sobrecarga"])] + [_a(d) for d in range(9, 15)], 8, 14, ["sobrecarga"])
    assert ctx["recurring"] == [] and ctx["out_of_norm"] == []


def test_tema_habitual_mais_que_o_normal_e_sumico():
    antes = [_a(d, ["sobrecarga"] if d % 4 == 0 else []) for d in range(1, 15)]       # ~25% dos dias
    mais = [_a(d, ["sobrecarga"] if d in (15, 16, 18, 20) else []) for d in range(15, 22)]   # 4 de 7
    assert "mais_que_o_normal" in _kinds(contexts.build(antes + mais, 15, 21, ["sobrecarga"]))
    sem = [_a(d) for d in range(15, 22)]
    assert "sumiu" in _kinds(contexts.build(antes + sem, 15, 21, ["sobrecarga"]))


def test_sensor_e_tom_so_contam_desvio_claro_e_repetido():
    leve = [_a(d, z={"sleep": -0.7}) for d in range(1, 8)]                  # variação normal: não conta
    assert contexts.build(leve, 1, 7, []) ["out_of_norm"] == []
    claro = [_a(d, z={"sleep": -1.5, "polarity": -1.2}) for d in range(1, 5)] + [_a(d) for d in range(5, 8)]
    ctx = contexts.build(claro, 1, 7, [])
    assert set(_kinds(ctx)) == {"sensor", "tom"}
    assert any("Sono abaixo do padrão em 4 de 7 dias" in i["text"] for i in ctx["out_of_norm"])


def test_combinacao_tema_com_sensor_e_silencio():
    dias = [_a(1, ["cansaco_sono"], z={"sleep": -1.5}), _a(2, ["cansaco_sono"], z={"sleep": -1.6}),
            _a(3, ["cansaco_sono"], z={"sleep": -1.4}), _a(5)]
    ctx = contexts.build(dias, 1, 5, [])
    assert any("sono abaixo do padrão em 3 de 3 dias" in c["text"] for c in ctx["combos"])
    assert any(i["kind"] == "silencio" and "1 dia" in i["text"] for i in ctx["out_of_norm"])


def test_nada_do_diario_vai_nos_contextos():
    demo_seed.go_to_day(66, crew_ids=["T1"])
    ctx = contexts.build(demo_seed.all_analyses("T1"), 60, 66, baseline_for("T1")[0].usual_themes)
    blob = json.dumps(ctx, ensure_ascii=False)
    assert "2026-" not in blob and "T1" not in blob
    assert set(ctx) == {"start", "end", "days", "recurring", "out_of_norm", "combos"}
    assert set(ctx["recurring"][0]) == {"theme", "label", "days", "of", "last_day", "trend"}


def test_tripulante_de_controle_quase_nao_e_sinalizado():
    demo_seed.go_to_day(180, crew_ids=["T4", "T2"])
    usual = baseline_for("T4")[0].usual_themes
    an = demo_seed.all_analyses("T4")
    flagged = sum(1 for end in range(7, 181, 7) if contexts.build(an, end - 6, end, usual)["out_of_norm"])
    assert flagged <= 3                                     # em 25 semanas
    t2 = demo_seed.all_analyses("T2")
    ep = contexts.build(t2, 108, 114, baseline_for("T2")[0].usual_themes)
    assert {r["theme"] for r in ep["recurring"]} == {"saudade_isolamento", "humor_baixo"}
    assert ep["out_of_norm"] and ep["combos"]
