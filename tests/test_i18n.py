"""Português/inglês: nenhuma frase fica sem tradução e o texto gerado sai inteiro no idioma escolhido."""
import json
import re
import sys
from pathlib import Path

import pytest

import config
import storage
from support import i18n
from support.i18n import t
from support.i18n_en import EN

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import i18n_scan  # noqa: E402

PLACEHOLDER = re.compile(r"\{(\w+)\}")
PORTUGUESE_HINTS = re.compile(r"\b(padrão|tripulante|semana|dias|diário|nave|hoje|apareceu|habitual|sensores)\b",
                              re.IGNORECASE)


@pytest.fixture(autouse=True)
def volta_ao_portugues():
    yield
    i18n.set_lang("pt")


def test_todo_texto_marcado_tem_traducao():
    faltam = [k for k in i18n_scan.keys_in_code() if k not in EN]
    assert not faltam, f"sem tradução em support/i18n_en.py: {faltam[:5]}"


def test_variaveis_iguais_nos_dois_idiomas():
    for pt, en in EN.items():
        assert set(PLACEHOLDER.findall(pt)) == set(PLACEHOLDER.findall(en)), pt
        assert en.strip(), pt


def test_valores_internos_tem_traducao():
    internos = (list(config.THEME_LABELS.values()) + config.MOOD_LABELS + list(config.MOOD_BY_THEME.values())
                + ["verde", "amarelo", "vermelho", "amarela", "vermelha", "dentro", "acima", "abaixo", "bem acima",
                   "bem abaixo", "semanal", "imediato", "lida", "ainda não lida"])
    assert not [x for x in internos if x not in EN]


def _walk(pt, en, path=""):
    assert type(pt) is type(en), path
    if isinstance(pt, dict):
        assert pt.keys() == en.keys(), path
        for k in pt:
            _walk(pt[k], en[k], f"{path}/{k}")
    else:
        assert set(PLACEHOLDER.findall(pt)) == set(PLACEHOLDER.findall(en)), path


def test_textos_de_devolutiva_com_a_mesma_estrutura():
    pt = json.loads(config.SUPPORT_TEXTS.read_text(encoding="utf-8"))
    en = json.loads(config.SUPPORT_TEXTS_EN.read_text(encoding="utf-8"))
    _walk(pt, en)


def test_idioma_padrao_do_codigo_e_portugues_e_troca():
    assert t("Salvar entrada") == "Salvar entrada"
    i18n.set_lang("en")
    assert t("Salvar entrada") == "Save entry"
    assert t("Dia {day} da missão", day=3) == "Mission day 3"
    assert t("texto sem tradução") == "texto sem tradução"      # o que não está no catálogo passa direto
    assert i18n.days(1) == "1 day" and i18n.days(3) == "3 days"
    assert i18n.num(1.5) == "1.5"
    i18n.set_lang("pt")
    assert i18n.num(1.5) == "1,5"


def _textos_gerados(dia: int) -> list[str]:
    import demo_seed
    from support import link_status
    from support import report as report_mod
    from support.explain import astronaut_text, component_text
    from support.feedback import build_feedback
    demo_seed.go_to_day(dia)
    out = []
    for crew in config.CREW_IDS:
        history = storage.get_history(crew, config.MISSION_DAYS)
        if not history:
            continue
        a = history[-1]
        rep = report_mod.build_report(crew)
        fb = build_feedback(a)
        out += [rep.summary, *rep.alert_reasons, *rep.breakdown_why.values(), *rep.breakdown_notes,
                *rep.discordance, *(i["text"] for i in rep.contexts["out_of_norm"]),
                *(i["text"] for i in rep.contexts["combos"]), *(r["trend"] or "" for r in rep.contexts["recurring"]),
                fb.text, fb.reason, astronaut_text(a), report_mod.notice_text(crew, dia, a.band),
                *component_text(a).values()]
        if fb.countermeasure:
            out += [fb.countermeasure.title, *fb.countermeasure.steps]
    status = link_status.link_status()
    out += [link_status.short_text(status), link_status.astronaut_text(status), link_status.earth_text(status)]
    return [x for x in out if x]


@pytest.mark.parametrize("dia", [7, 25, 60, 114])
def test_textos_gerados_saem_em_ingles(dia):
    i18n.set_lang("en")
    sobras = [x for x in _textos_gerados(dia) if PORTUGUESE_HINTS.search(x)]
    assert not sobras, sobras[:3]


def test_textos_gerados_em_portugues_continuam_iguais():
    textos = _textos_gerados(25)
    assert any("Dias" in x and "da missão" in x for x in textos)
    assert not any(x.startswith("Mission days") for x in textos)


def test_visoes_da_terra_nos_dois_idiomas():
    from ui import earth_data
    i18n.set_lang("en")
    options = earth_data.view_options(40)
    assert options["7"] == "Weekly (7 days)" and options["range"] == "Range"
    assert earth_data.resolve_view("30", 40)[2] == "30 days"
    i18n.set_lang("pt")
    assert earth_data.view_options(40)["range"] == "Intervalo"
