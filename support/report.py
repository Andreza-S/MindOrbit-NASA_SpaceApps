"""Relatório para a Terra (RF13/RF17). Definição: docs do projeto "Definição do relatório".

Nunca contém texto do diário nem dados brutos de sensores (RNF03).
"""
import hashlib
from dataclasses import dataclass
from typing import Callable, Optional

import config
import storage
from ingest.source import baseline_for, sensor_for
from models import Analysis, Report
from support.explain import component_text, explain
from support.i18n import N_, days as _dias, t

SENSOR_LABELS = {"sleep": N_("sono"), "activity": N_("atividade"), "hr": N_("frequência cardíaca")}   # texto-fonte; traduza com sensor_label()
STRONG_Z = config.SENSOR_CONFIRM_Z + 0.5     # a partir daí: "bem abaixo" / "bem acima"
MILD_Z = 0.5
WEEK = config.WINDOW_DAYS
NOTICE_CATEGORIES = N_("faixa do índice, temas, sensores e apoio prestado")   # traduza com t()


def sensor_label(key: str) -> str:
    return t(SENSOR_LABELS[key])


def pseudonym(crew_id: str) -> str:
    """Fixo durante a missão. Só o bordo sabe a quem corresponde."""
    digest = hashlib.sha256((config.PSEUDONYM_SALT + crew_id).encode()).hexdigest()
    return "A-" + digest[:6].upper()


def sensor_level(key: str, z: float) -> str:
    """z vem com sinal: sono e atividade ruins são negativos; frequência cardíaca ruim é positiva."""
    bad = z if key == "hr" else -z
    if bad < MILD_Z:
        return "dentro"
    direction = "acima" if key == "hr" else "abaixo"
    return f"bem {direction}" if bad >= STRONG_Z else direction


def sensor_phrase(key: str, level: str) -> str:
    if level == "dentro":
        return t("{sensor}: dentro do seu padrão", sensor=sensor_label(key))
    return t("{sensor}: {level} do seu padrão", sensor=sensor_label(key), level=t(level))


def _answer(done: Optional[bool], helped: Optional[bool]) -> str:
    if done is None:
        return t("sem resposta")
    if not done:
        return t("não fez")
    return t("fez e ajudou") if helped else t("fez, mas não ajudou")


def _span(days: list[int]) -> str:
    days = sorted(days)
    if len(days) == 1:
        return str(days[0])
    if days == list(range(days[0], days[-1] + 1)):
        return t("{a} a {b}", a=days[0], b=days[-1])
    return ", ".join(str(d) for d in days)


def _support(crew_id: str, last_day: int) -> list[dict]:
    list_cm = getattr(storage, "list_countermeasures", None)
    if not list_cm:
        return []
    groups: dict[str, list] = {}
    for c in list_cm(crew_id, config.MISSION_DAYS):
        if last_day - WEEK < c.day <= last_day:
            groups.setdefault(c.title, []).append(c)
    out = []
    for title, items in groups.items():
        answers: dict[str, int] = {}
        for c in items:
            a = _answer(c.done, c.helped)
            answers[a] = answers.get(a, 0) + 1
        out.append({"title": t(title), "days": _span([c.day for c in items]),
                    "answer": ", ".join(f"{n} {k}" for k, n in answers.items()),
                    "_first": min(c.day for c in items)})
    out.sort(key=lambda r: r["_first"])
    for r in out:
        del r["_first"]
    return out


def alert_reasons(a: Analysis) -> list[str]:
    """Qual tema ou sensor gerou o alerta (RNF06), só com rótulos do catálogo."""
    reasons = []
    for theme in a.alerts:
        label = t(config.THEME_LABELS.get(theme, theme))
        sensor = a.confirmed_by.get(theme)
        text = t("{label} há {n} dias", label=label, n=a.persistence.get(theme, 0))
        if sensor in SENSOR_LABELS:
            text += t(", confirmado por {sensor}", sensor=sensor_label(sensor))
        reasons.append(text)
    for theme, sensor in a.confirmed_by.items():
        if theme not in a.alerts and sensor in SENSOR_LABELS:
            label = t(config.THEME_LABELS.get(theme, theme))
            reasons.append(t("{label} hoje, confirmado por {sensor}", label=label, sensor=sensor_label(sensor)))
    return reasons


def _onset_day(all_history: list[Analysis]) -> Optional[int]:
    """Dia em que começou a sequência atual de dias fora do verde (None se hoje é verde)."""
    by_day = {a.day: a for a in all_history}
    days = sorted(by_day)
    if not days or by_day[days[-1]].band == "verde":
        return None
    onset = days[-1]
    for d in reversed(days[:-1]):
        if by_day[d].band == "verde":
            break
        onset = d
    return onset


def _data_quality(crew_id: str, last_day: int, analyzed: set[int]) -> tuple[list[int], dict[str, int]]:
    window = list(range(max(1, last_day - WEEK + 1), last_day + 1))
    missing = [d for d in window if d not in analyzed]
    sensors = sum(1 for d in window if sensor_for(crew_id, config.date_for_day(d)) is not None)
    return missing, {"janela": len(window), "diario": len(window) - len(missing), "sensores": sensors}


def _discordance(a: Analysis, levels: dict[str, str]) -> list[str]:
    """O texto não reclama, mas um sensor desvia muito: pode ser minimização ou cansaço não percebido."""
    if a.themes or a.z.get("polarity", 0.0) < -MILD_Z:
        return []
    return [t("texto sem queixas, mas {phrase}", phrase=sensor_phrase(k, lv))
            for k, lv in levels.items() if lv.startswith("bem")]


def _last_directive_read(crew_id: str) -> Optional[bool]:
    directives = storage.list_directives(crew_id)
    return directives[0].read if directives else None


def _week_stats(analyses: list[Analysis]) -> Optional[dict]:
    if not analyses:
        return None
    worst = max(analyses, key=lambda a: (a.risk, a.day))
    bands = {b: sum(1 for a in analyses if a.band == b) for b in ("verde", "amarelo", "vermelho")}
    return {"mean": round(sum(a.risk for a in analyses) / len(analyses)), "worst": worst.risk,
            "worst_day": worst.day, "bands": bands, "days": len(analyses)}


def _episodes(all_history: list[Analysis]) -> list[dict]:
    """Sequências de dias fora do verde que chegaram ao vermelho (só dias da missão)."""
    runs, current = [], []
    for a in sorted(all_history, key=lambda a: a.day):
        if a.band != "verde" and (not current or a.day == current[-1].day + 1):
            current.append(a)
            continue
        if current:
            runs.append(current)
        current = [a] if a.band != "verde" else []
    if current:
        runs.append(current)
    last_day = max((a.day for a in all_history), default=0)
    return [{"start": r[0].day, "end": r[-1].day, "peak": max(a.risk for a in r),
             "ongoing": r[-1].day == last_day} for r in runs if any(a.band == "vermelho" for a in r)]


def _habitual_themes(crew_id: str, themes: list[str]) -> list[str]:
    usual = set(baseline_for(crew_id)[0].usual_themes)
    return [t for t in themes if t in usual]


_BAND_F = {"verde": N_("verde"), "amarelo": N_("amarela"), "vermelho": N_("vermelha")}


def _summary(rep: Report) -> str:
    """Parágrafo-resumo para a equipe de saúde. Sem datas de calendário e sem o texto do diário."""
    w, prev = rep.week, rep.prev_week
    parts = [t("Dias {a} a {b} da missão: índice {risk}, faixa {band}.", a=rep.period_start_day,
               b=rep.period_end_day, risk=rep.risk, band=t(_BAND_F.get(rep.band, rep.band)))]
    if prev:
        delta = w["mean"] - prev["mean"]
        rel = t("estável") if abs(delta) <= 5 else (t("mais alto") if delta > 0 else t("mais baixo"))
        parts.append(t("A média da semana é {mean}, {rel} em relação à semana anterior ({prev}).",
                       mean=w["mean"], rel=rel, prev=prev["mean"]))
    else:
        parts.append(t("A média da semana é {mean}; ainda não há semana anterior para comparar.", mean=w["mean"]))
    if rep.onset_day is not None:
        n = rep.period_end_day - rep.onset_day + 1
        parts.append(t("A piora começou no dia {day} ({span} seguidos fora do verde)", day=rep.onset_day, span=_dias(n))
                     + (": " + "; ".join(rep.alert_reasons) + "." if rep.alert_reasons else "."))
    else:
        parts.append(t("Sem piora em curso."))
    if rep.theme_days:
        names = []
        for th, n in sorted(rep.theme_days.items(), key=lambda kv: -kv[1]):
            label = t(config.THEME_LABELS.get(th, th))
            names.append(f"{label} ({_dias(n)}" + (t(", habitual para este tripulante") if th in rep.habitual_themes
                                                   else "") + ")")
        parts.append(t("Temas na semana: {items}.", items=", ".join(names)))
    else:
        parts.append(t("Nenhum tema de queixa nos {span} analisados.", span=_dias(w["days"])))
    now_off = [sensor_phrase(k, v) for k, v in rep.sensor_dev.items() if v != "dentro"]
    trend_off = [t("{sensor} fora do padrão em {span}", sensor=sensor_label(k).lower(), span=_dias(n))
                 for k, n in rep.sensor_days_off.items() if n]
    if now_off:
        parts.append(t("Sensores hoje: {items}.", items="; ".join(now_off)))
    elif trend_off:
        parts.append(t("Sensores dentro do padrão hoje (na semana: {items}).", items=", ".join(trend_off)))
    else:
        parts.append(t("Sensores dentro do padrão hoje, e em nenhum dia da semana."))
    if rep.missing_diary_days:
        parts.append(t("Sem diário em {days} (dias da missão).", days=", ".join(str(d) for d in rep.missing_diary_days)))
    else:
        parts.append(t("Diário preenchido em todos os dias."))
    eps = rep.mission_context["episodes"]
    past = [e for e in eps if not e["ongoing"]]
    if past:
        last = past[-1]
        count = t("1 episódio anterior") if len(past) == 1 else t("{n} episódios anteriores", n=len(past))
        parts.append(t("Na missão, {count} no vermelho; o último foi dos dias {a} a {b}.",
                       count=count, a=last["start"], b=last["end"]))
    elif not eps:
        parts.append(t("Nenhum episódio no vermelho até agora na missão."))
    theme_notes = [i["text"] for i in rep.contexts.get("out_of_norm", [])
                   if i["kind"] in ("unica_vez", "tema_novo", "mais_que_o_normal", "sumiu")][:2]
    if theme_notes:
        parts.append(t("Fora do habitual: {items}", items=" ".join(theme_notes)))
    if rep.discordance:
        parts.append(t("Atenção: {items}.", items="; ".join(rep.discordance)))
    return " ".join(parts)


def build_report(crew_id: str, immediate: Optional[bool] = None) -> Optional[Report]:
    all_history = storage.get_history(crew_id, config.MISSION_DAYS)
    if not all_history:
        return None
    last: Analysis = all_history[-1]
    history = [a for a in all_history if a.day > last.day - WEEK]   # a semana do relatório
    is_immediate = (last.band == "vermelho") if immediate is None else immediate
    levels = {k: sensor_level(k, v) for k, v in last.z.items() if k in SENSOR_LABELS}
    missing, quality = _data_quality(crew_id, last.day, {a.day for a in history})
    why = explain(last)
    week_days = last.day - WEEK
    prev = [a for a in all_history if week_days - WEEK < a.day <= week_days]
    sensor_off = {k: sum(1 for a in history if sensor_level(k, a.z.get(k, 0.0)) != "dentro")
                  for k in SENSOR_LABELS}
    episodes = _episodes(all_history)
    from support import contexts as contexts_mod          # import tardio: contexts usa funções deste módulo
    ctx = contexts_mod.build(all_history, max(1, last.day - WEEK + 1), last.day,
                             baseline_for(crew_id)[0].usual_themes)
    rep = Report(
        pseudonym=pseudonym(crew_id),
        period_start_day=history[0].day,
        period_end_day=last.day,
        mission_total_days=config.MISSION_DAYS,
        kind="imediato" if is_immediate else "semanal",
        risk=last.risk, band=last.band,
        risk_breakdown={k: round(v, 1) for k, v in why.points.items()},
        breakdown_notes=why.notes,
        onset_day=_onset_day(all_history[-config.HISTORY_CHART_DAYS * 2:]),
        trend=[a.risk for a in history],
        theme_days={t: n for t, n in last.persistence.items() if n > 0},
        alert_reasons=alert_reasons(last),
        sensor_dev=levels,
        discordance=_discordance(last, levels),
        mood=last.mood_confirmed,
        support=_support(crew_id, last.day),
        missing_diary_days=missing,
        data_days=quality,
        last_directive_read=_last_directive_read(crew_id),
        immediate=is_immediate,
        summary="",
        trend_days=[a.day for a in history],
        trend_bands=[a.band for a in history],
        week=_week_stats(history),
        prev_week=_week_stats(prev),
        breakdown_why=component_text(last),
        sensor_days_off=sensor_off,
        habitual_themes=_habitual_themes(crew_id, list(last.persistence)),
        mission_context={"episodes": episodes, "days_not_green": sum(1 for a in all_history if a.band != "verde"),
                         "days_total": len(all_history)},
        contexts=ctx,
    )
    rep.summary = _summary(rep)
    return rep


# ---------------------------------------------------------------- aviso ao astronauta
@dataclass
class SentInfo:
    day: int
    kind: str          # "semanal" | "imediato"
    held: bool         # ficou retido por blackout quando foi enviado


def _blackout_on() -> bool:
    try:
        return str(storage.get_setting("blackout")) == "1"
    except (KeyError, TypeError):
        return False


def record_sent(crew_id: str, day: int, kind: str) -> None:
    held = "1" if _blackout_on() else "0"
    storage.set_setting(f"last_report_{kind}_{crew_id}", f"{day}:{held}")


def last_sent(crew_id: str, kind: Optional[str] = None) -> Optional[SentInfo]:
    """Último envio do tipo pedido; sem tipo, o mais recente (no mesmo dia, o imediato)."""
    kinds = [kind] if kind else ["semanal", "imediato"]
    found = []
    for k in kinds:
        try:
            day, held = str(storage.get_setting(f"last_report_{k}_{crew_id}")).split(":", 1)
            found.append(SentInfo(int(day), k, held == "1"))
        except (KeyError, ValueError, TypeError):
            continue
    return max(found, key=lambda i: (i.day, i.kind == "imediato"), default=None)


def next_weekly_day(crew_id: str, today: int) -> int:
    """Próximo dia de relatório semanal: múltiplo de 7, ainda não enviado."""
    try:
        sent = int(storage.get_setting(f"weekly_sent_{crew_id}"))
    except (KeyError, ValueError, TypeError):
        sent = 0
    day = ((max(today, 1) + WEEK - 1) // WEEK) * WEEK
    while day <= sent:
        day += WEEK
    return day


def _when(day: int, today: int) -> str:
    return t("hoje (dia {day})", day=day) if day == today else t("no dia {day}", day=day)


def notice_text(crew_id: str, today: int, band: Optional[str] = None) -> str:
    """Aviso ao astronauta sobre o relatório (ele não vê o conteúdo). Tom acolhedor (RNF10)."""
    nxt = next_weekly_day(crew_id, today)
    info = last_sent(crew_id)
    if band == "vermelho":
        immediate = last_sent(crew_id, "imediato")
        info = immediate or info          # na crise, o que importa é que a Terra foi avisada
    if info is None:
        return t("Nenhum relatório enviado ainda. O próximo segue automaticamente no dia {day} da missão.", day=nxt)
    if info.held and _blackout_on():
        return t("O relatório está na fila e segue assim que o link voltar. "
                 "O seu apoio a bordo continua funcionando.")
    if info.kind == "imediato":
        return t("A equipe de saúde da Terra foi avisada {when} e vai acompanhar você.", when=_when(info.day, today))
    return t("A equipe de saúde da Terra recebeu o seu relatório semanal {when}. O próximo segue no dia {day}.",
             when=_when(info.day, today), day=nxt)


# ---------------------------------------------------------------- quando enviar
def entered_red(today: Analysis, previous: list[Analysis]) -> bool:
    """Imediato só ao ENTRAR no vermelho; nos dias seguintes a atualização vai no semanal."""
    if today.band != "vermelho":
        return False
    before = [a for a in previous if a.day < today.day]
    return not before or before[-1].band != "vermelho"


def weekly_due(crew_id: str, day: int) -> bool:
    """Semanal automático nos dias 7, 14, 21… da missão, uma vez por dia."""
    if day <= 0 or day % WEEK != 0:
        return False
    try:
        return int(storage.get_setting(f"weekly_sent_{crew_id}")) < day
    except (KeyError, ValueError, TypeError):
        return True


def after_entry(crew_id: str, today: Analysis, previous: list[Analysis],
                send: Callable[[str, bool], None]) -> list[str]:
    """Decide e dispara os envios automáticos depois de salvar uma entrada."""
    sent = []
    if entered_red(today, previous):
        send(crew_id, True)
        sent.append("imediato")
    if weekly_due(crew_id, today.day):
        send(crew_id, False)
        storage.set_setting(f"weekly_sent_{crew_id}", str(today.day))
        sent.append("semanal")
    for kind in sent:
        record_sent(crew_id, today.day, kind)
    return sent
