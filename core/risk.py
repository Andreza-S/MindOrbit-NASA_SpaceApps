"""Índice de risco de 0 a 100 e faixas verde, amarela e vermelha (RF08)."""
from typing import Optional

import config


def band_for(risk: int) -> str:
    if risk <= config.BAND_GREEN_MAX:
        return "verde"
    if risk <= config.BAND_YELLOW_MAX:
        return "amarelo"
    return "vermelho"


def risk_components(bad_dev: dict[str, float], counts: dict[str, int],
                    confirmed: dict[str, str],
                    today_themes: Optional[list[str]] = None) -> dict[str, float]:
    """Cada componente de 0 a 1.

    today_themes=None: não se sabe (a persistência conta inteira). Lista vazia:
    nenhum tema hoje, e a persistência dos dias anteriores pesa PERSIST_NO_THEME_TODAY.
    """
    tone = bad_dev["polarity"] / config.Z_CAP
    max_count = max(counts.values(), default=0)
    persist = min(1.0, max_count / config.ALERT_DAYS)
    if confirmed:
        persist = min(1.0, persist + config.CONFIRM_BOOST)
    if today_themes is not None and not today_themes:
        persist *= config.PERSIST_NO_THEME_TODAY
    sensors = sum(
        config.SENSOR_WEIGHTS[s] * (bad_dev[s] / config.Z_CAP)
        for s in config.SENSOR_WEIGHTS
    )
    return {"tone": tone, "persistence": persist, "sensors": sensors}


def compute_risk(bad_dev: dict[str, float], counts: dict[str, int],
                 confirmed: dict[str, str],
                 today_themes: Optional[list[str]] = None) -> tuple[int, str]:
    c = risk_components(bad_dev, counts, confirmed, today_themes)
    total = (config.W_TONE * c["tone"]
             + config.W_PERSIST * c["persistence"]
             + config.W_SENSORS * c["sensors"])
    risk = int(round(100 * total))
    risk = max(0, min(100, risk))
    return risk, band_for(risk)
