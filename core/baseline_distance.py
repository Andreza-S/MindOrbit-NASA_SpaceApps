"""Distância do dia em relação ao padrão de bem-estar pessoal (RF05)."""
from typing import Optional

import config
from models import Baseline, SensorDay


def zscore(value: float, mean: float, std: float) -> float:
    return (value - mean) / max(std, config.STD_FLOOR)


def compute_z(baseline: Baseline, sensors: Optional[SensorDay], pol: float) -> dict[str, float]:
    """Escore-z com sinal para sono, atividade, frequência cardíaca e tom.

    Sem leitura de sensor no dia, os três sensores ficam em 0 (sem desvio).
    """
    z = {
        "sleep": 0.0, "activity": 0.0, "hr": 0.0,
        "polarity": zscore(pol, baseline.polarity_mean, baseline.polarity_std),
    }
    if sensors is not None:
        z["sleep"] = zscore(sensors.sleep_h, baseline.sleep_mean, baseline.sleep_std)
        z["activity"] = zscore(sensors.activity_min, baseline.activity_mean, baseline.activity_std)
        z["hr"] = zscore(sensors.hr_rest, baseline.hr_mean, baseline.hr_std)
    return z


def bad_deviation(z: dict[str, float]) -> dict[str, float]:
    """Só a direção ruim, entre 0 e Z_CAP.

    Ruim = sono, atividade e tom abaixo do normal; frequência cardíaca acima.
    """
    raw = {
        "sleep": -z["sleep"],
        "activity": -z["activity"],
        "hr": z["hr"],
        "polarity": -z["polarity"],
    }
    return {k: min(max(v, 0.0), config.Z_CAP) for k, v in raw.items()}
