import re
import time

import config
from core.baseline_distance import bad_deviation, compute_z
from core.crossing import cross_with_sensors
from core.persistence import alerts_from, persistence_counts
from core.pipeline import analyze_entry
from core.risk import band_for, compute_risk
from core.sentiment import polarity
from core.themes import detect_themes
from support.feedback import build_feedback, load_texts
from tests.conftest import make_analysis, make_entry


# --- Tom e negação (RF04) ---
def test_negacao_inverte_palavra_positiva():
    assert polarity("estou bem") > 0
    assert polarity("não estou bem") < 0


def test_negacao_vale_por_duas_palavras():
    assert polarity("nunca me senti tão cansado") < 0
    assert polarity("nem estou feliz") < 0


def test_sem_palavra_de_tom_e_zero():
    assert polarity("dia normal") == 0.0


def test_polaridade_fica_entre_menos_um_e_um():
    for t in ["ótimo ótimo ótimo", "péssimo cansado triste", "bem mal"]:
        assert -1.0 <= polarity(t) <= 1.0


# --- Temas (RF03) ---
def test_detecta_tema_de_cansaco():
    assert "cansaco_sono" in detect_themes("estou exausto e não dormi")


def test_detecta_com_acento_e_flexao():
    assert "cansaco_sono" in detect_themes("Acordei CANSADA")
    assert "saudade_isolamento" in detect_themes("sinto saudade da família")


def test_entrada_de_uma_linha_funciona():  # RNF07
    a_themes = detect_themes("tédio")
    assert a_themes == ["monotonia"]


# --- Persistência (RF06) ---
def test_tres_dias_nao_alerta_e_quatro_alerta():
    hist = [make_analysis(d, ["cansaco_sono"]) for d in (7, 8)]
    counts = persistence_counts(hist, 9, ["cansaco_sono"])
    assert counts["cansaco_sono"] == 3 and alerts_from(counts) == []
    hist.append(make_analysis(9, ["cansaco_sono"]))
    counts = persistence_counts(hist, 10, ["cansaco_sono"])
    assert counts["cansaco_sono"] == 4 and alerts_from(counts) == ["cansaco_sono"]


def test_janela_de_sete_dias_ignora_dias_antigos():
    hist = [make_analysis(d, ["ansiedade"]) for d in (1, 2, 3, 4)]
    assert persistence_counts(hist, 20, []).get("ansiedade", 0) == 0


def test_duas_entradas_no_mesmo_dia_contam_um_dia():
    hist = [make_analysis(9, ["conflito"]), make_analysis(9, ["conflito"])]
    assert persistence_counts(hist, 10, [])["conflito"] == 1


# --- Padrão de bem-estar e cruzamento (RF05, RF07) ---
def test_escore_z_contra_o_padrao(baseline, tired_sensors):
    z = compute_z(baseline, tired_sensors, 0.15)
    assert round(z["sleep"], 1) == -2.0
    assert round(z["hr"], 1) == 2.0
    assert round(z["polarity"], 1) == 0.0


def test_desvio_ruim_so_na_direcao_ruim(baseline):
    from models import SensorDay
    good = SensorDay("d", "T1", sleep_h=9.0, activity_min=80, hr_rest=50)
    bad = bad_deviation(compute_z(baseline, good, 0.9))
    assert all(v == 0.0 for v in bad.values())


def test_cruzamento_confirma_cansaco_com_sono_baixo(baseline, tired_sensors):
    bad = bad_deviation(compute_z(baseline, tired_sensors, 0.0))
    assert cross_with_sensors(["cansaco_sono"], bad) == {"cansaco_sono": "sleep"}
    assert cross_with_sensors(["saudade_isolamento"], bad) == {}


# --- Índice e faixas (RF08) ---
def test_limites_das_faixas():
    assert [band_for(r) for r in (0, 33)] == ["verde", "verde"]
    assert [band_for(r) for r in (34, 66)] == ["amarelo", "amarelo"]
    assert [band_for(r) for r in (67, 100)] == ["vermelho", "vermelho"]


def test_indice_zero_e_cem():
    zero = {"sleep": 0, "activity": 0, "hr": 0, "polarity": 0}
    assert compute_risk(zero, {}, {}) == (0, "verde")
    worst = {k: config.Z_CAP for k in zero}
    r, b = compute_risk(worst, {"x": 7}, {"x": "sleep"})
    assert r == 100 and b == "vermelho"


def test_pesos_somam_um():
    assert abs(config.W_TONE + config.W_PERSIST + config.W_SENSORS - 1.0) < 1e-9
    assert abs(sum(config.SENSOR_WEIGHTS.values()) - 1.0) < 1e-9


# --- Pipeline ---
def test_dia_normal_fica_verde(baseline, normal_sensors):
    e = make_entry("Dia tranquilo, treinei e estou bem. Foi um ótimo dia, estou feliz.")
    a = analyze_entry(e, [], baseline, normal_sensors)
    assert a.band == "verde" and a.mood == "bem" and a.main_theme is None


def test_desgaste_fica_amarelo_ou_vermelho(baseline, tired_sensors):
    hist = [make_analysis(d, ["cansaco_sono"]) for d in (6, 7, 8, 9)]
    e = make_entry("Estou exausto, não consegui dormir de novo e acordei cansado.")
    a = analyze_entry(e, hist, baseline, tired_sensors)
    assert a.band in ("amarelo", "vermelho")
    assert a.main_theme == "cansaco_sono" and a.mood == "cansado"
    assert a.confirmed_by == {"cansaco_sono": "sleep"}
    assert "cansaco_sono" in a.alerts


def test_analise_leva_menos_de_um_segundo(baseline, tired_sensors):  # RNF05
    e = make_entry("Estou exausto e preocupado, o clima na tripulação está tenso." * 5)
    hist = [make_analysis(d, ["cansaco_sono"]) for d in range(3, 10)]
    analyze_entry(e, hist, baseline, tired_sensors)  # aquece o cache do léxico
    t0 = time.perf_counter()
    analyze_entry(e, hist, baseline, tired_sensors)
    assert time.perf_counter() - t0 < 1.0


def test_sem_sensor_no_dia_usa_so_o_texto(baseline):
    a = analyze_entry(make_entry("estou cansado"), [], baseline, None)
    assert a.z["sleep"] == 0.0 and a.main_theme == "cansaco_sono"


# --- Devolutiva (RF09, RF10, RF12, RNF06, RNF10) ---
def test_retorno_amarelo_cita_tema_e_sensor_e_tem_contramedida(baseline, tired_sensors):
    hist = [make_analysis(d, ["cansaco_sono"]) for d in (7, 8, 9)]
    a = analyze_entry(make_entry("Estou cansado e dormi pouco."), hist, baseline, tired_sensors)
    fb = build_feedback(a)
    assert "cansaço" in fb.reason.lower() and "sono" in fb.reason.lower()
    assert fb.countermeasure is not None and fb.countermeasure.steps


def test_vermelho_escala_para_oficial_medico():
    a = make_analysis(10, ["ansiedade"])
    a.band, a.risk, a.persistence = "vermelho", 80, {"ansiedade": 5}
    fb = build_feedback(a)
    assert fb.escalate and "oficial médico" in fb.text
    assert fb.countermeasure is not None


def test_verde_nao_escala():
    a = make_analysis(10, [])
    a.band, a.risk, a.polarity = "verde", 10, 0.5
    fb = build_feedback(a)
    assert not fb.escalate and fb.text


def _all_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _all_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_strings(v)


def test_textos_sem_rotulos_clinicos():  # RNF10
    forbidden = re.compile(r"depress|transtorno|ansiedade|psiquiatr|diagn[oó]stic|patolog|doen[cç]a|sintoma",
                           re.IGNORECASE)
    texts = list(_all_strings(load_texts()))
    from support.countermeasures import CATALOG
    for c in CATALOG.values():
        texts += [c.title, *c.steps]
    bad = [t for t in texts if forbidden.search(t)]
    assert bad == []


def test_todo_tema_e_toda_faixa_tem_texto():
    t = load_texts()
    for theme in config.THEMES:
        assert theme in t["amarelo_tema"] and theme in t["vermelho_tema"]


# --- Recuperação: índice amarelo vindo só da persistência (RNF06) ---
def test_amarelo_so_por_persistencia_explica_o_motivo():
    a = make_analysis(10, [])
    a.band, a.risk, a.polarity = "amarelo", 40, 0.8
    a.persistence = {"cansaco_sono": 5}
    fb = build_feedback(a)
    assert "cansaço" in fb.reason.lower() and "5" in fb.reason
    assert fb.countermeasure is not None and fb.countermeasure.theme == "cansaco_sono"
    assert "melhor" in fb.text


def test_monotonia_tem_humor_proprio():
    a = analyze_entry(make_entry("Tudo igual todos os dias, o tédio pesa."), [],
                      __import__("ingest.baseline", fromlist=["x"]).default_baseline("T1"), None)
    assert a.mood == "entediado"


def test_rotina_neutra_nao_marca_monotonia():
    assert detect_themes("Rotina normal, tudo certo.") == []


# --- Recuperação: persistência pesa menos quando o tema não aparece mais (RF08) ---
def test_persistencia_pesa_menos_sem_tema_hoje():
    zero = {"sleep": 0, "activity": 0, "hr": 0, "polarity": 0}
    counts = {"cansaco_sono": 6}
    com_tema, _ = compute_risk(zero, counts, {}, ["cansaco_sono"])
    sem_tema, band = compute_risk(zero, counts, {}, [])
    assert com_tema == 35 and sem_tema == 18 and band == "verde"
    assert compute_risk(zero, counts, {}) == (35, "amarelo")  # sem a informação, conta inteira


def test_recuperacao_volta_ao_verde(baseline, normal_sensors):
    hist = [make_analysis(d, ["cansaco_sono"]) for d in (3, 4, 5, 6, 7, 8)]
    a = analyze_entry(make_entry("Dia leve, treinei e estou animado.", day=9), hist, baseline, normal_sensors)
    assert a.band == "verde"
