"""Dados da aba da Terra, sem Streamlit (fácil de testar).

A Terra só enxerga análises e relatórios, nunca o texto do diário (RNF03).
"""
from contextlib import contextmanager
from typing import Optional

import config
import storage
from models import Analysis, Report
from ingest.source import baseline_for
from support import contexts as contexts_mod
from support import report as report_mod
from support.i18n import N_, t

BAND_ICON = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}
_BAND_ORDER = {"vermelho": 0, "amarelo": 1, "verde": 2}


def _history(crew_id: str, days: int = config.HISTORY_CHART_DAYS) -> list[Analysis]:
    """Histórico do tripulante até o dia da missão (o mesmo para todos)."""
    return storage.get_history(crew_id, days)


def latest_analysis(crew_id: str) -> Optional[Analysis]:
    history = _history(crew_id)
    return history[-1] if history else None


def theme_label(theme: Optional[str]) -> str:
    return t(config.THEME_LABELS.get(theme, theme)) if theme else t("nenhum")


def overview_rows(crew_ids=None) -> list[dict]:
    """Uma linha por tripulante, com quem precisa de atenção primeiro."""
    rows = []
    for crew_id in (crew_ids or config.CREW_IDS):
        a = latest_analysis(crew_id)
        if a is None:
            rows.append({"crew_id": crew_id, "sem_dados": True, "band": "verde", "risk": -1})
            continue
        days = a.persistence.get(a.main_theme, 0) if a.main_theme else 0
        rows.append({
            "crew_id": crew_id, "sem_dados": False, "day": a.day, "risk": a.risk,
            "band": a.band, "main_theme": theme_label(a.main_theme), "mood": a.mood,
            "days_in_theme": days, "alerts": [theme_label(t) for t in a.alerts],
        })
    return sorted(rows, key=lambda r: (_BAND_ORDER[r["band"]], -r["risk"], r["crew_id"]))


def attention_needed(rows: list[dict]) -> list[str]:
    return [r["crew_id"] for r in rows if not r["sem_dados"] and r["band"] == "vermelho"]


def risk_trend(crew_id: str, whole_mission: bool = False) -> list[dict]:
    days = config.MISSION_DAYS if whole_mission else config.HISTORY_CHART_DAYS
    return [{"dia": a.day, "risco": a.risk, "faixa": a.band} for a in _history(crew_id, days)]


def support_rows(crew_id: str, start: Optional[int] = None, end: Optional[int] = None) -> list[dict]:
    """Apoio prestado a bordo, uma linha por sugestão, com os dias e as respostas (RF18).

    Sem texto do diário.
    """
    fn = getattr(storage, "list_countermeasures", None)
    if fn is None:
        return []
    if start is None:
        logs = fn(crew_id, config.HISTORY_CHART_DAYS)
    else:
        logs = [c for c in fn(crew_id, config.MISSION_DAYS) if start <= c.day <= (end or c.day)]
    groups: dict[str, list] = {}
    for c in logs:
        groups.setdefault(c.title, []).append(c)
    rows = []
    for title, items in groups.items():
        days = sorted(c.day for c in items)
        span = f"{days[0]}" if len(days) == 1 else (
            t("{a} a {b}", a=days[0], b=days[-1]) if days == list(range(days[0], days[-1] + 1))
            else ", ".join(str(d) for d in days))
        counts: dict[str, int] = {}
        for c in items:
            counts[_answer(c)] = counts.get(_answer(c), 0) + 1
        rows.append({"contramedida": t(title), "dias": span,
                     "respostas": ", ".join(f"{n} {k}" for k, n in counts.items()),
                     "_first": days[0]})
    rows.sort(key=lambda r: r["_first"])
    for r in rows:
        del r["_first"]
    return rows


def _answer(c) -> str:
    if c.done is None:
        return t("sem resposta")
    if not c.done:
        return t("não fez")
    return t("fez e ajudou") if c.helped else t("fez, mas não ajudou")


def clinical_report(crew_id: str) -> Optional[Report]:
    """Relatório clínico do tripulante no dia da missão (o que a equipe de saúde recebe)."""
    return report_mod.build_report(crew_id)


# ---------------------------------------------------------------- períodos de visualização
PRESETS = [(7, N_("Semanal (7 dias)")), (15, N_("15 dias")), (30, N_("30 dias")), (60, N_("60 dias")), (90, N_("90 dias"))]


def view_options(today: int) -> dict[str, str]:
    """Só as visões que cabem nos dias que existem de fato (chave -> rótulo)."""
    options = {str(n): t(label) for n, label in PRESETS if today >= n}
    options["all"] = t("Histórico completo (dia 1 ao dia {today})", today=today)
    if today >= 2:
        options["range"] = t("Intervalo")
        options["day"] = t("Dia específico")
    return options


def resolve_view(key: str, today: int, first: int = 1, last: int = 0, day: int = 0) -> tuple[int, int, str]:
    """(dia inicial, dia final, rótulo) da visão escolhida. Nunca passa do dia atual da missão."""
    if key in ("all",) or key not in {str(n) for n, _ in PRESETS} | {"range", "day"}:
        return 1, today, t("histórico completo, dia 1 ao dia {today}", today=today)
    if key == "range":
        a = max(1, min(first or 1, today))
        b = max(a, min(last or today, today))
        return a, b, t("intervalo, dia {a} ao dia {b}", a=a, b=b)
    if key == "day":
        d = max(1, min(day or today, today))
        return max(1, d - 14), d, t("dia {d} em foco", d=d)
    n = int(key)
    return max(1, today - n + 1), today, t(dict(PRESETS)[n]).lower()


def _all(crew_id: str) -> list[Analysis]:
    return storage.get_history(crew_id, config.MISSION_DAYS)


def risk_range(crew_id: str, start: int, end: int) -> list[dict]:
    return [{"dia": a.day, "risco": a.risk, "faixa": a.band} for a in _all(crew_id) if start <= a.day <= end]


def period_stats(crew_id: str, start: int, end: int) -> Optional[dict]:
    return report_mod._week_stats([a for a in _all(crew_id) if start <= a.day <= end])


def contexts_for(crew_id: str, start: int, end: int) -> dict:
    return contexts_mod.build(_all(crew_id), start, end, baseline_for(crew_id)[0].usual_themes)


@contextmanager
def at_day(day: int):
    """Consulta ao histórico: dentro do bloco o banco responde como no dia pedido. O dia da missão não muda."""
    current = storage.get_setting("sim_day")
    try:
        storage.set_setting("sim_day", str(day))
        yield
    finally:
        storage.set_setting("sim_day", current)


def report_at(crew_id: str, day: int) -> Optional[Report]:
    """O relatório clínico como estava no dia pedido (a semana que termina nele)."""
    with at_day(day):
        return report_mod.build_report(crew_id)
