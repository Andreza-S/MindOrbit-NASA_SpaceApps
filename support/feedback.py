"""Devolutiva imediata ao astronauta: o que foi observado, o motivo e o que fazer
(RF09, RNF06, RNF10)."""
import json
from functools import lru_cache
from typing import Optional

import config
from core.baseline_distance import bad_deviation
from models import Analysis, Feedback
from support.countermeasures import get_countermeasure, theme_from_sensors
from support.i18n import get_lang, t


@lru_cache(maxsize=2)
def _load(lang: str) -> dict:
    path = config.SUPPORT_TEXTS_EN if lang == "en" else config.SUPPORT_TEXTS
    return json.loads(path.read_text(encoding="utf-8"))


def load_texts() -> dict:
    """Textos de devolutiva no idioma da tela (texts.json em português, texts_en.json em inglês)."""
    return _load(get_lang())


def _lingering_theme(a: Analysis) -> Optional[str]:
    """Tema que ainda pesa na janela de 7 dias (2+ dias), mesmo sem aparecer hoje."""
    if not a.persistence:
        return None
    theme, n = max(a.persistence.items(), key=lambda kv: (kv[1], kv[0]))
    return theme if n >= 2 else None


def _sensor_phrase(sensor: str) -> str:
    return load_texts()["motivo"]["sensor"][sensor]


def build_reason(a: Analysis) -> str:
    """Frase que cita o tema ou o sensor que gerou o retorno (RNF06)."""
    m = load_texts()["motivo"]
    parts: list[str] = []

    if a.main_theme:
        label = t(config.THEME_LABELS.get(a.main_theme, a.main_theme))
        head = m["tema"].format(tema=label)
        n = a.persistence.get(a.main_theme, 0)
        if n >= 2:
            head += " " + m["persistencia"].format(n=n)
        parts.append(head)
        sensor = a.confirmed_by.get(a.main_theme)
        if sensor:
            parts.append(_sensor_phrase(sensor))
    else:
        bad = bad_deviation(a.z)
        if bad["polarity"] > config.SENSOR_CONFIRM_Z:
            parts.append(m["tom"])
        for sensor in ("sleep", "hr", "activity"):
            if bad[sensor] > config.SENSOR_CONFIRM_Z:
                parts.append(_sensor_phrase(sensor))
        lingering = _lingering_theme(a)
        if lingering:  # o índice veio da persistência: diga qual tema e quantos dias
            label = t(config.THEME_LABELS.get(lingering, lingering))
            parts.append(m["persistencia_sem_tema"].format(tema=label, n=a.persistence[lingering]))

    if not parts:
        return ""
    text = parts[0]
    if len(parts) > 1:
        text += t(", e ") + ", ".join(parts[1:])
    return text[0].upper() + text[1:] + "."


def build_feedback(a: Analysis) -> Feedback:
    txt = load_texts()
    reason = build_reason(a)
    countermeasure = None
    escalate = False

    if a.band == "verde":
        text = txt["verde_positivo"] if a.polarity >= config.MOOD_GOOD_POLARITY else txt["verde_neutro"]
    elif a.band == "amarelo":
        if a.main_theme:
            text = txt["amarelo_tema"][a.main_theme]
            countermeasure = get_countermeasure(a.main_theme)
        else:
            lingering = _lingering_theme(a)
            if lingering and a.polarity >= config.MOOD_GOOD_POLARITY:
                label = t(config.THEME_LABELS.get(lingering, lingering))
                text = txt["amarelo_recuperacao"].format(tema=label)
                countermeasure = get_countermeasure(lingering)
            else:
                text = txt["amarelo_geral"]
                countermeasure = get_countermeasure(theme_from_sensors(bad_deviation(a.z)))
    else:  # vermelho
        base = txt["vermelho_tema"].get(a.main_theme, txt["vermelho_geral"]) if a.main_theme else txt["vermelho_geral"]
        text = f"{base} {txt['escalonamento']}"
        escalate = True
        theme = a.main_theme or theme_from_sensors(bad_deviation(a.z))
        countermeasure = get_countermeasure(theme)

    return Feedback(text=text, reason=reason, countermeasure=countermeasure, escalate=escalate)
