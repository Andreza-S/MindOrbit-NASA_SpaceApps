"""Cruzamento do diário com os sensores (RF07)."""
import config


def cross_with_sensors(themes: list[str], bad_dev: dict[str, float]) -> dict[str, str]:
    """tema -> sensor que o confirma (desvio ruim acima do limite).

    Ex.: "cansaço" no texto junto com sono abaixo do normal.
    """
    confirmed: dict[str, str] = {}
    for theme in themes:
        sensor = config.THEME_SENSOR.get(theme)
        if sensor and bad_dev.get(sensor, 0.0) > config.SENSOR_CONFIRM_Z:
            confirmed[theme] = sensor
    return confirmed
