"""Por que o índice está onde está (explicabilidade, RNF06).

Duas leituras do mesmo cálculo:
- astronauta: só palavras, sem pesos nem números clínicos;
- equipe de saúde: a composição do índice em pontos (tom, persistência, sensores).
"""
from dataclasses import dataclass

import config
from core.baseline_distance import bad_deviation
from core.risk import risk_components
from models import Analysis
from support.i18n import N_, t

_SENSOR_NAME = {"sleep": N_("o seu sono"), "activity": N_("a sua atividade"), "hr": N_("a sua frequência cardíaca")}
_SENSOR_LABEL = {"sleep": N_("sono"), "activity": N_("atividade"), "hr": N_("frequência cardíaca")}
_SENSOR_DIR = {"sleep": N_("abaixo"), "activity": N_("abaixo"), "hr": N_("acima")}
MILD = 0.5          # abaixo disso o sensor está dentro do padrão
MIN_POINTS = 3.0    # contribuição mínima para ser citada ao astronauta


@dataclass
class Explanation:
    points: dict[str, float]        # tone, persistence, sensors (soma ≈ índice)
    maximum: dict[str, float]       # o máximo de cada componente (35, 35, 30)
    notes: list[str]                # ajustes que mudaram a persistência
    contributors: list[tuple[float, str]]   # (pontos, frase), do que mais pesou ao que menos


def _components(a: Analysis) -> dict[str, float]:
    return risk_components(bad_deviation(a.z), a.persistence, a.confirmed_by, a.themes)


def explain(a: Analysis) -> Explanation:
    bad = bad_deviation(a.z)
    c = _components(a)
    weights = {"tone": config.W_TONE, "persistence": config.W_PERSIST, "sensors": config.W_SENSORS}
    points = {k: 100 * weights[k] * c[k] for k in weights}
    maximum = {k: 100 * w for k, w in weights.items()}

    notes = []
    if a.persistence and not a.themes:
        notes.append(t("Persistência reduzida: hoje o texto não traz tema negativo."))
    if a.confirmed_by:
        notes.append(t("Persistência reforçada: tema confirmado por sensor."))

    contributors: list[tuple[float, str]] = []
    if a.persistence:
        theme, days = max(a.persistence.items(), key=lambda kv: kv[1])
        if days >= 2:
            label = t(config.THEME_LABELS.get(theme, theme))
            contributors.append((points["persistence"],
                                 t("o tema {label} apareceu em {days} dos últimos {window} dias",
                                   label=label, days=days, window=config.WINDOW_DAYS)))
    if bad["polarity"] > MILD:
        contributors.append((points["tone"], t("o tom do seu diário está mais pesado que o seu normal")))
    for sensor, weight in config.SENSOR_WEIGHTS.items():
        if bad[sensor] > MILD:
            pts = 100 * config.W_SENSORS * weight * bad[sensor] / config.Z_CAP
            contributors.append((pts, t("{what} está {dir} do seu padrão", what=t(_SENSOR_NAME[sensor]),
                                        dir=t(_SENSOR_DIR[sensor]))))
    contributors.sort(key=lambda x: -x[0])
    return Explanation(points, maximum, notes, contributors)


def astronaut_text(a: Analysis) -> str:
    """O que mais pesou, em palavras. Sem pesos, pontos ou números clínicos."""
    e = explain(a)
    top = [phrase for pts, phrase in e.contributors if pts >= MIN_POINTS][:2]
    if not top:
        return t("Hoje nada pesou muito no seu índice.") if a.band == "verde" else ""
    text = t("O que mais pesou hoje: {items}.", items=t(" e ").join(top))
    if a.persistence and not a.themes:
        text += " " + t("O seu texto de hoje não traz queixas, e isso ajudou a baixar o índice.")
    return text


def component_text(a: Analysis) -> dict[str, str]:
    """Uma frase por componente do índice, para a equipe de saúde (sem números brutos de sensor)."""
    e = explain(a)
    bad = bad_deviation(a.z)
    tone = e.points["tone"]
    if tone < 3:
        tone_text = t("O tom do diário está dentro do habitual deste tripulante.")
    elif tone < 12:
        tone_text = t("O tom do diário ficou um pouco mais pesado que o habitual.")
    elif tone < 24:
        tone_text = t("O tom do diário ficou mais pesado que o habitual.")
    else:
        tone_text = t("O tom do diário ficou bem mais pesado que o habitual.")
    if e.points["persistence"] < 1 or not a.persistence:
        persist_text = t("Nenhum tema se repetiu o bastante para pesar.")
    else:
        theme, days = max(a.persistence.items(), key=lambda kv: kv[1])
        persist_text = t("O tema {label} apareceu em {days} dos últimos {window} dias.",
                         label=t(config.THEME_LABELS.get(theme, theme)), days=days, window=config.WINDOW_DAYS)
        if a.confirmed_by.get(theme):
            persist_text += " " + t("Foi confirmado por sensor.")
        if not a.themes:
            persist_text += " " + t("Hoje o texto não traz queixas, o que reduziu a persistência.")
    off = [t("{sensor} {dir} do padrão", sensor=t(_SENSOR_LABEL[k]), dir=t(_SENSOR_DIR[k]))
           for k in config.SENSOR_WEIGHTS if bad[k] > MILD]
    sensors_text = (t("Sensores dentro do padrão do tripulante.") if not off
                    else t("Sensores: {items}.", items=", ".join(off)))
    return {"tone": tone_text, "persistence": persist_text, "sensors": sensors_text}
