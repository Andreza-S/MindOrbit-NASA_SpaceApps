"""Preenchimento da demo com os diários simulados da Pessoa B (data/diarios_demo.json).

Tudo passa pelo mesmo caminho do app: análise de cada dia em ordem, com sensores, histórico acumulado,
contramedida e envio automático de relatórios. Funciona com o SQLite e com o armazenamento em memória.
"""
from typing import Iterable, Optional

import config
import storage
from core.pipeline import analyze_entry
from ingest.source import baseline_for, sensor_for
from models import Analysis, CountermeasureLog, Entry
from simulator import demo_text
from support import report as report_mod
from support.feedback import build_feedback
from ui import _compat


def _real_send(crew: str, immediate: bool) -> None:
    _compat.send_report(crew, immediate=immediate)


def all_analyses(crew_id: str) -> list[Analysis]:
    """Todas as análises do tripulante, de qualquer dia (a janela do banco acompanha o sim_day)."""
    current = storage.get_setting("sim_day")
    try:
        storage.set_setting("sim_day", str(config.MISSION_DAYS))
        return storage.get_history(crew_id, config.MISSION_DAYS)
    finally:
        storage.set_setting("sim_day", current)


def has_entry(crew_id: str, day: int) -> bool:
    return any(a.day == day for a in all_analyses(crew_id))


def missing_crews(day: int, crew_ids: Optional[Iterable[str]] = None) -> list[str]:
    """Quem ainda não escreveu o diário do dia (o diário é obrigatório para avançar)."""
    return [c for c in (crew_ids or config.CREW_IDS) if not has_entry(c, day)]


def ingest(day: int) -> None:
    """Chegada dos sensores desse dia ao banco (só no SQLite; o dia não pode passar do sim_day)."""
    if hasattr(storage.backend, "connect"):
        from simulator import feed
        feed.ingest_day(day)


def write_day(crew_id: str, day: int, text: str, send=None) -> Analysis:
    """Analisa e grava um dia, como o app faz ao salvar o diário. `send` dispara os relatórios automáticos."""
    previous = storage.get_setting("sim_day")
    storage.set_setting("sim_day", str(day))
    try:
        ingest(day)
        existing = next((a.entry_id for a in storage.get_history(crew_id, 1) if a.day == day), None)
        entry = Entry(existing, crew_id, day, config.date_for_day(day), text)
        entry.id = storage.save_entry(entry)
        history = [a for a in storage.get_history(crew_id, config.WINDOW_DAYS) if a.day != day]
        baseline, _ = baseline_for(crew_id)
        analysis = analyze_entry(entry, history, baseline, sensor_for(crew_id, entry.date))
        storage.save_analysis(analysis)
        feedback = build_feedback(analysis)
        if feedback.countermeasure and storage.save_countermeasure:
            storage.save_countermeasure(CountermeasureLog(
                None, entry.id, crew_id, day, feedback.countermeasure.theme, feedback.countermeasure.title))
        if send:
            report_mod.after_entry(crew_id, analysis, history, send)
        return analysis
    finally:
        storage.set_setting("sim_day", previous)


def fill_missing(day: int, crew_ids: Optional[Iterable[str]] = None) -> list[str]:
    """Escreve o diário da demo de quem faltou no dia. Os relatórios automáticos saem de verdade."""
    done = []
    for crew_id in missing_crews(day, crew_ids):
        text = demo_text(crew_id, day)
        if text:
            write_day(crew_id, day, text, send=_real_send)
            done.append(crew_id)
    return done


def _rebuild_report_state(crew_id: str, upto: int) -> None:
    """Refaz o registro de envios como se os relatórios até `upto` já tivessem saído (sem pôr nada na fila)."""
    analyses = [a for a in all_analyses(crew_id) if a.day <= upto]
    weekly = (upto // report_mod.WEEK) * report_mod.WEEK
    immediate, before = None, []
    for a in analyses:
        if report_mod.entered_red(a, before):
            immediate = a.day
        before.append(a)
    storage.set_setting(f"weekly_sent_{crew_id}", str(weekly))
    storage.set_setting(f"last_report_semanal_{crew_id}", f"{weekly}:0" if weekly else "-")
    storage.set_setting(f"last_report_imediato_{crew_id}", f"{immediate}:0" if immediate else "-")


def go_to_day(day: int, include_day: bool = True, crew_ids: Optional[Iterable[str]] = None) -> dict:
    """Leva a missão inteira ao dia `day`, com o histórico dos diários da demo até lá.

    Com `include_day`, o diário do próprio dia já vem analisado e os relatórios que ele dispara
    saem de verdade. Sem ele, o dia fica em branco para o astronauta escrever. Os dias de antes
    são histórico simulado: não geram relatórios retroativos. Voltar no tempo não apaga nada.
    """
    day = max(1, min(int(day), config.MISSION_DAYS))
    crews = list(crew_ids or config.CREW_IDS)
    last = day if include_day else day - 1
    created: dict[str, set[int]] = {}
    existing = {c: {a.day for a in all_analyses(c)} for c in crews}
    for d in range(1, last + 1):
        for crew_id in crews:
            if d in existing[crew_id]:
                continue
            text = demo_text(crew_id, d)
            if text:
                write_day(crew_id, d, text)
                created.setdefault(crew_id, set()).add(d)
    sent_today = include_day and last >= 1
    for crew_id in crews:
        new_last = last in created.get(crew_id, set())
        _rebuild_report_state(crew_id, last - 1 if (sent_today and new_last) else last)
    storage.set_setting("sim_day", str(day))
    ingest(day)
    if sent_today:
        for crew_id in crews:
            if last in created.get(crew_id, set()):
                analysis = next(a for a in all_analyses(crew_id) if a.day == last)
                before = [a for a in all_analyses(crew_id) if a.day < last][-config.WINDOW_DAYS:]
                report_mod.after_entry(crew_id, analysis, before, _real_send)
    return {c: len(days) for c, days in created.items()}
