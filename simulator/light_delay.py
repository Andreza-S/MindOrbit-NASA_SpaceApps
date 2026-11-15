"""Atraso real do sinal Terra–Marte a partir de dados abertos da NASA/JPL.

Fonte: NASA JPL Solar System Dynamics, "Approximate Positions of the Planets", Tabela 1
(elementos keplerianos e taxas, válidos de 1800 a 2050): https://ssd.jpl.nasa.gov/planets/approx_pos.html

Para cada dia da missão, calcula as posições heliocêntricas da Terra (baricentro Terra-Lua) e de Marte,
a distância entre os dois e o tempo que a luz (o rádio) leva para percorrê-la.

Rodar na raiz do repositório:  python -m simulator.light_delay   (gera data/atraso_terra_marte.csv)
"""
import csv
import math
from datetime import date

import config

# Tabela 1 do JPL: a [au], e, I [graus], L [graus], longitude do periélio [graus], longitude do nodo [graus]
ELEMENTOS_JPL = {
    "terra": ((1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
              (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0)),
    "marte": ((1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
              (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343)),
}
SEGUNDOS_LUZ_POR_AU = 499.004784   # 1 au / velocidade da luz
J2000 = date(2000, 1, 1)           # JD 2451545.0 corresponde a 1/1/2000 12h TT


def _seculos_desde_j2000(d: date) -> float:
    return ((d - J2000).days - 0.5) / 36525.0


def posicao(planeta: str, d: date) -> tuple[float, float, float]:
    """Posição heliocêntrica (x, y, z) em au, na eclíptica J2000, pelo método do JPL."""
    base, taxa = ELEMENTOS_JPL[planeta]
    T = _seculos_desde_j2000(d)
    a, e, inc, L, peri, nodo = (b + r * T for b, r in zip(base, taxa))
    omega = peri - nodo
    M = (L - peri + 180.0) % 360.0 - 180.0
    e_graus = math.degrees(e)
    E = M + e_graus * math.sin(math.radians(M))
    for _ in range(30):
        dM = M - (E - e_graus * math.sin(math.radians(E)))
        dE = dM / (1 - e * math.cos(math.radians(E)))
        E += dE
        if abs(dE) < 1e-8:
            break
    Er = math.radians(E)
    xp = a * (math.cos(Er) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(Er)
    w, O, i = math.radians(omega), math.radians(nodo), math.radians(inc)
    x = (math.cos(w) * math.cos(O) - math.sin(w) * math.sin(O) * math.cos(i)) * xp \
        + (-math.sin(w) * math.cos(O) - math.cos(w) * math.sin(O) * math.cos(i)) * yp
    y = (math.cos(w) * math.sin(O) + math.sin(w) * math.cos(O) * math.cos(i)) * xp \
        + (-math.sin(w) * math.sin(O) + math.cos(w) * math.cos(O) * math.cos(i)) * yp
    z = (math.sin(w) * math.sin(i)) * xp + (math.cos(w) * math.sin(i)) * yp
    return x, y, z


def distancia_terra_marte_au(d: date) -> float:
    t, m = posicao("terra", d), posicao("marte", d)
    return math.dist(t, m)


def atraso_minutos(day: int) -> float:
    """Atraso de ida do sinal (minutos) no dia da missão."""
    d = date.fromisoformat(config.date_for_day(day))
    return distancia_terra_marte_au(d) * SEGUNDOS_LUZ_POR_AU / 60.0


def main(dias: int = 180) -> None:
    caminho = config.DATA_DIR / "atraso_terra_marte.csv"
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["day", "date", "distance_au", "one_way_delay_min"])
        for day in range(1, dias + 1):
            d = date.fromisoformat(config.date_for_day(day))
            dist = distancia_terra_marte_au(d)
            w.writerow([day, d.isoformat(), round(dist, 4), round(dist * SEGUNDOS_LUZ_POR_AU / 60, 2)])
    primeiro, ultimo = atraso_minutos(1), atraso_minutos(dias)
    print(f"Atraso Terra–Marte (NASA/JPL): dia 1 = {primeiro:.1f} min · dia {dias} = {ultimo:.1f} min → {caminho}")


if __name__ == "__main__":
    main()
