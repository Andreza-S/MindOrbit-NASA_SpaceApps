"""Contextos que merecem atenção: o que mais se repete e o que foge do habitual do tripulante.

Feito para a equipe de saúde entender o que se passa SEM ferir o sigilo do astronauta:
- só usa as categorias do catálogo de temas (config.THEME_LABELS), contagens de dias e níveis de sensor
  em palavras. Nunca palavras, frases ou qualquer trecho do diário (RNF03);
- um tema que se repete exige pelo menos MIN_DAYS dias. Uma única vez só aparece quando foge do habitual
  do próprio tripulante (tema que não é dos habituais dele), e mesmo assim só como categoria e dia.
"""
from collections import Counter
from math import ceil
from typing import Iterable

import config
from core.baseline_distance import bad_deviation
from models import Analysis
from support.i18n import days as _dias, t
from support.report import SENSOR_LABELS, sensor_label

MIN_DAYS = 2            # um tema só "se repete" a partir de 2 dias
MIN_HISTORY = 7         # dias de missão anteriores para comparar com o normal do tripulante
CLEAR = config.SENSOR_CONFIRM_Z    # desvio claro (1 desvio-padrão do próprio tripulante); abaixo disso é variação normal


def _label(theme: str) -> str:
    return t(config.THEME_LABELS.get(theme, theme))


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _off(a: Analysis, key: str) -> bool:
    """Sensor claramente fora do padrão do próprio tripulante naquele dia (o que é variação normal não conta)."""
    return bad_deviation(a.z)[key] >= CLEAR


def _direction(key: str) -> str:
    return t("acima") if key == "hr" else t("abaixo")


def _share(analyses: list[Analysis], theme: str) -> float:
    return sum(1 for a in analyses if theme in a.themes) / len(analyses) if analyses else 0.0


def build(all_analyses: Iterable[Analysis], start: int, end: int, usual_themes: Iterable[str]) -> dict:
    """Contextos do período [start, end] (dias da missão), comparados ao período anterior de mesmo tamanho
    e ao histórico anterior do próprio tripulante."""
    every = sorted(all_analyses, key=lambda a: a.day)
    usual = set(usual_themes)
    period = [a for a in every if start <= a.day <= end]
    n = len(period)
    out = {"start": start, "end": end, "days": n, "recurring": [], "out_of_norm": [], "combos": []}
    if n == 0:
        return out
    length = end - start + 1
    prev = [a for a in every if start - length <= a.day < start]
    before = [a for a in every if a.day < start]

    counts = Counter(t for a in period for t in set(a.themes))
    last_day = {t: max(a.day for a in period if t in a.themes) for t in counts}

    # ---- o que mais se repete
    for theme, c in counts.most_common():
        if c < MIN_DAYS:
            continue
        trend = None
        if prev:
            before_n = sum(1 for a in prev if theme in a.themes)
            if before_n == 0:
                trend = t("novo neste período")
            else:
                diff = c / n - before_n / len(prev)
                trend = t("aumentando") if diff > 0.15 else (t("diminuindo") if diff < -0.15 else t("estável"))
        out["recurring"].append({"theme": theme, "label": _label(theme), "days": c, "of": n,
                                 "last_day": last_day[theme], "trend": trend})

    # ---- o que foge do habitual do próprio tripulante
    items = out["out_of_norm"]
    for theme, c in counts.items():
        if theme in usual:
            continue
        if c == 1:
            items.append({"kind": "unica_vez", "text": t(
                "{label} apareceu uma única vez (dia {day}), fora dos temas habituais deste tripulante.",
                label=_cap(_label(theme)), day=last_day[theme])})
        else:
            items.append({"kind": "tema_novo", "text": t(
                "{label} apareceu em {span} e não faz parte dos temas habituais deste tripulante.",
                label=_cap(_label(theme)), span=_dias(c))})
    if len(before) >= MIN_HISTORY:
        for theme in usual:
            base, now = _share(before, theme), counts.get(theme, 0) / n
            if counts.get(theme, 0) >= MIN_DAYS and now >= max(2 * base, base + 0.3):
                items.append({"kind": "mais_que_o_normal", "text": t(
                    "{label}, um tema habitual, apareceu em {span}, mais que o normal deste tripulante.",
                    label=_cap(_label(theme)), span=_dias(counts[theme]))})
            elif n >= MIN_HISTORY and base >= 0.2 and counts.get(theme, 0) == 0:
                items.append({"kind": "sumiu", "text": t(
                    "{label}, um tema habitual, não apareceu neste período, ao contrário do normal deste tripulante.",
                    label=_cap(_label(theme)))})
    floor = max(3, ceil(n / 2))
    for key in SENSOR_LABELS:
        off = sum(1 for a in period if _off(a, key))
        if off >= floor:
            items.append({"kind": "sensor", "text": t(
                "{sensor} {dir} do padrão em {off} de {n} dias.",
                sensor=_cap(sensor_label(key)), dir=_direction(key), off=off, n=n)})
    heavy = sum(1 for a in period if bad_deviation(a.z)["polarity"] >= CLEAR)
    if heavy >= floor:
        items.append({"kind": "tom", "text": t("O tom do diário ficou mais pesado que o habitual em {heavy} de {n} dias.",
                                          heavy=heavy, n=n)})
    silent = [d for d in range(start, end + 1) if d not in {a.day for a in period}]
    if silent:
        items.append({"kind": "silencio", "text": t("Sem diário em {span}.", span=_dias(len(silent)))})

    # ---- combinações: o tema veio junto de um sensor fora do padrão
    for rec in out["recurring"]:
        days = [a for a in period if rec["theme"] in a.themes]
        for key in SENSOR_LABELS:
            off = sum(1 for a in days if _off(a, key))
            if off >= MIN_DAYS and off / len(days) >= 0.6:
                out["combos"].append({"text": t(
                    "{label} veio junto de {sensor} {dir} do padrão em {off} de {n} dias.",
                    label=_cap(rec["label"]), sensor=sensor_label(key), dir=_direction(key), off=off, n=len(days))})
    return out
