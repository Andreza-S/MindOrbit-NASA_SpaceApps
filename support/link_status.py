"""Estado do link nave ↔ Terra, em palavras, para o astronauta e para a Terra.

Sem Streamlit e sem SQLite: usa só as configurações (blackout, atraso) e o dia da missão.
O blackout pode ter duração prevista (em dias da missão); sem ela, é "sem previsão de retorno".
"""
from dataclasses import dataclass
from typing import Optional

import storage
from support.i18n import days as _days_i18n, num, t


@dataclass
class LinkStatus:
    active: bool
    one_way_min: float               # tempo real do sinal nave → Terra (ou Terra → nave)
    since_day: Optional[int]         # início do blackout (None se o link está ativo)
    until_day: Optional[int]         # volta prevista (None = sem previsão)
    days_left: Optional[int]         # dias da missão até a volta prevista
    last_contact_day: Optional[int]  # último dia com comunicação antes do blackout

    @property
    def round_trip_min(self) -> float:
        return 2 * self.one_way_min


def _get(key: str) -> Optional[str]:
    try:
        value = str(storage.get_setting(key)).strip()
    except (KeyError, TypeError):
        return None
    return value or None


def _int(key: str) -> Optional[int]:
    value = _get(key)
    try:
        return int(value) if value is not None and int(value) > 0 else None
    except ValueError:
        return None


def start_blackout(duration_days: Optional[int] = None) -> None:
    """Liga o blackout agora. `duration_days` (opcional) dá a volta prevista, em dias da missão."""
    today = int(storage.get_setting("sim_day"))
    storage.set_setting("blackout", "1")
    storage.set_setting("blackout_since_day", str(today))
    storage.set_setting("blackout_until_day", str(today + duration_days) if duration_days else "")


def end_blackout() -> None:
    storage.set_setting("blackout", "0")
    storage.set_setting("blackout_since_day", "")
    storage.set_setting("blackout_until_day", "")


def refresh_blackout() -> bool:
    """Encerra o blackout sozinho quando o dia previsto chega. Devolve True se encerrou agora."""
    if _get("blackout") != "1":
        return False
    until = _int("blackout_until_day")
    if until is not None and int(storage.get_setting("sim_day")) >= until:
        end_blackout()
        return True
    return False


def _one_way_minutes(today: int) -> float:
    if _get("delay_mode") == "manual":      # na demo, 1 s do controle representa 1 min de sinal
        return float(_get("delay_seconds") or 0)
    from simulator.light_delay import atraso_minutos
    return atraso_minutos(today)


def link_status() -> LinkStatus:
    refresh_blackout()
    today = int(storage.get_setting("sim_day"))
    minutes = _one_way_minutes(today)
    if _get("blackout") != "1":
        return LinkStatus(True, minutes, None, None, None, None)
    since, until = _int("blackout_since_day"), _int("blackout_until_day")
    return LinkStatus(False, minutes, since, until,
                      None if until is None else max(0, until - today),
                      None if since is None else max(1, since - 1))


def fmt_minutes(minutes: float) -> str:
    if minutes >= 60:
        return f"{num(minutes / 60)} h"
    return f"{num(minutes)} min"


def _days(n: int) -> str:
    return t("hoje") if n == 0 else _days_i18n(n)


def _return_text(s: LinkStatus) -> str:
    if s.until_day is None:
        return t("Ainda não há previsão de retorno")
    if s.days_left == 0:
        return t("A comunicação deve voltar hoje")
    return t("A previsão é voltar no dia {day} (em {when})", day=s.until_day, when=_days(s.days_left))


def short_text(s: LinkStatus) -> str:
    """Uma linha, para a faixa no topo (vale para as duas abas)."""
    if s.active:
        return t("📡 Link ativo · o sinal leva {one} (ida e volta ≈ {two})",
                 one=fmt_minutes(s.one_way_min), two=fmt_minutes(s.round_trip_min))
    return t("🔴 Sem comunicação · {detail}",
             detail=_return_text(s).lower() if s.until_day else t("sem previsão de retorno"))


def astronaut_text(s: LinkStatus) -> str:
    """Para o astronauta, em tom acolhedor (RNF10)."""
    if s.active:
        return t("Link com a Terra ativo. Uma mensagem leva cerca de {one} para chegar, "
                 "e a resposta pode levar cerca de {two}.",
                 one=fmt_minutes(s.one_way_min), two=fmt_minutes(s.round_trip_min))
    return (t("Sem comunicação com a Terra no momento.") + " " + _return_text(s) + ". "
            + t("Os seus relatórios ficam guardados e seguem quando o link voltar. "
                "O seu apoio a bordo continua funcionando."))


def earth_text(s: LinkStatus) -> str:
    """Para a equipe de saúde."""
    if s.active:
        return t("Link com a nave ativo. Uma mensagem enviada agora chega em cerca de {one}; "
                 "a confirmação de leitura leva cerca de {two} para voltar.",
                 one=fmt_minutes(s.one_way_min), two=fmt_minutes(s.round_trip_min))
    since = t("Sem comunicação com a nave desde o dia {day}.", day=s.since_day) if s.since_day \
        else t("Sem comunicação com a nave.")
    contact = " " + t("Último contato no dia {day}.", day=s.last_contact_day) if s.last_contact_day else ""
    return since + contact + " " + _return_text(s) + ". " + t(
        "Mensagens enviadas ficam na fila e saem quando o link voltar.")


def pending_eta(s: LinkStatus) -> str:
    """Para cada mensagem enviada e ainda sem confirmação."""
    if s.active:
        return t("chega à nave em cerca de {one}", one=fmt_minutes(s.one_way_min))
    return t("retida até o link voltar")
