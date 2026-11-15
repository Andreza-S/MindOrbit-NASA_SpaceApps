"""Aba da Terra: painel da equipe de saúde.

Une o painel clínico (Pessoa A) com o link da Pessoa B: relatórios recebidos pela fila, fila do link
e envio de mensagem pelo mesmo link. A Terra só vê o que chegou pelo
pacote: pseudônimo, índice, temas e sensores. O texto do diário nunca sai da nave.
"""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import config
import storage
from models import Directive
from support import link_status
from support import report as report_mod
from support.i18n import N_, t
from ui import _compat, earth_data


def _send_directive(crew_id: str) -> None:
    text = st.session_state.get("earth_msg", "").strip()
    if not text:
        return
    if _compat.COMMS_AVAILABLE:     # sai pelo link: segue o atraso e o blackout
        import comms
        comms.send_directive(report_mod.pseudonym(crew_id), text)
        st.session_state["earth_sent"] = t("Mensagem na fila de volta para a nave (segue o atraso do sinal).")
    else:
        save = getattr(storage, "save_directive", None)
        if save is None:
            return
        save(Directive(id=None, crew_id=crew_id, text=text,
                       sent_at=datetime.now().strftime("%d/%m %H:%M")))
        st.session_state["earth_sent"] = t("Mensagem enviada.")
    st.session_state["earth_msg"] = ""


def _render_overview(rows: list[dict]) -> None:
    urgent = earth_data.attention_needed(rows)
    if urgent:
        st.error(t("Atenção prioritária: {crew} em faixa vermelha.", crew=", ".join(urgent)))
    cols = st.columns(len(rows))
    for col, r in zip(cols, rows):
        with col.container(border=True):
            st.markdown(f"**{r['crew_id']}**")
            if r["sem_dados"]:
                st.caption(t("Sem dados ainda"))
                continue
            st.markdown(earth_data.BAND_ICON[r["band"]] + " " + t("Risco **{risk}** ({band})", risk=r["risk"], band=t(r["band"])))
            st.caption(t("Dia {day} · {mood}", day=r["day"], mood=t(r["mood"])))
            st.caption(t("Tema: {theme}", theme=r["main_theme"])
                       + (" " + t("há {n} dias", n=r["days_in_theme"]) if r["days_in_theme"] > 1 else ""))


def _render_trend(crew_id: str, start: int, end: int, focus_day: int = 0) -> None:
    data = earth_data.risk_range(crew_id, start, end)
    if not data:
        st.caption(t("Sem histórico para este tripulante neste período."))
        return
    df = pd.DataFrame(data)
    span = [start - 0.5, end + 0.5] if end > start else [start - 1, start + 1]
    line = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("dia:Q", title=t("Dia da missão"), axis=alt.Axis(tickMinStep=1), scale=alt.Scale(domain=span)),
        y=alt.Y("risco:Q", title=t("Índice de risco"), scale=alt.Scale(domain=[0, 100])),
        tooltip=[alt.Tooltip("dia:Q", title=t("Dia da missão")), alt.Tooltip("risco:Q", title=t("Índice de risco")),
                 alt.Tooltip("faixa:N", title=t("Faixa"))])
    rules = alt.Chart(pd.DataFrame({"y": [config.BAND_GREEN_MAX, config.BAND_YELLOW_MAX]})) \
        .mark_rule(strokeDash=[4, 4], opacity=0.5).encode(y="y:Q")
    chart = line + rules
    if focus_day:
        chart += alt.Chart(pd.DataFrame({"x": [focus_day]})).mark_rule(color="#d64545", opacity=0.7).encode(x="x:Q")
    st.altair_chart(chart, use_container_width=True)


def _render_period_stats(crew_id: str, start: int, end: int) -> None:
    """Os números do período que está no gráfico."""
    stats = earth_data.period_stats(crew_id, start, end)
    if not stats:
        return
    c = st.columns(3)
    c[0].metric(t("Índice médio do período"), stats["mean"])
    c[1].metric(t("Pior dia do período"), stats["worst"], help=t("Dia {day} da missão", day=stats["worst_day"]))
    b = stats["bands"]
    c[2].metric(t("Dias por faixa"), f"🟢{b['verde']}  🟡{b['amarelo']}  🔴{b['vermelho']}",
                help=t("{n} dia(s) com diário no período", n=stats["days"]))


def _clamp_view_inputs(today: int) -> None:
    for key in ("earth_first", "earth_last", "earth_day"):
        if key in st.session_state:
            st.session_state[key] = max(1, min(int(st.session_state[key]), today))


def _pick_view(today: int) -> tuple[str, int, int, str, int]:
    """Escolha do período. Só oferece o que cabe nos dias que existem; nunca passa do dia atual."""
    options = earth_data.view_options(today)
    if st.session_state.get("earth_view") not in options:
        st.session_state["earth_view"] = "15" if "15" in options else "all"
    _clamp_view_inputs(today)
    key = st.radio(t("Período a visualizar"), list(options), format_func=options.get, horizontal=True,
                   key="earth_view", help=t("Só aparecem períodos que já existem na missão."))
    first = last = day = 0
    if key == "range":
        c = st.columns(2)
        first = c[0].number_input(t("Do dia"), 1, today, value=max(1, today - 14), key="earth_first")
        last = c[1].number_input(t("Ao dia"), 1, today, value=today, key="earth_last")
        if first > last:
            st.warning(t("O dia inicial vem depois do final; mostrando só o dia final."))
    elif key == "day":
        day = st.number_input(t("Dia da missão"), 1, today, value=today, key="earth_day")
    start, end, label = earth_data.resolve_view(key, today, int(first), int(last), int(day))
    return key, start, end, label, int(day)


def _message_state(m: dict) -> str:
    if m["status"] == "lida":
        return t("lida no dia {day} da missão", day=m["read_day"])
    if m["status"] == "entregue":
        return t("entregue à nave no dia {day} da missão, ainda não lida", day=m["delivered_day"])
    return t("enviada, a caminho da nave: {eta} (a confirmação volta depois do atraso do sinal)",
             eta=link_status.pending_eta(link_status.link_status()))


def _render_sent_messages(crew_id: str) -> None:
    """O que a Terra enviou e o que ela sabe de cada mensagem (as confirmações chegam com atraso)."""
    import comms
    msgs = comms.earth_messages(report_mod.pseudonym(crew_id))
    if not msgs:
        return
    st.markdown("**" + t("Mensagens enviadas") + "**")
    for m in msgs[:5]:
        mark = "🆕 " if m["unseen"] else ""
        st.markdown(f"- {mark}" + t("Dia {day}: “{text}” · **{state}**", day=m["sent_day"], text=m["text"],
                                     state=_message_state(m)))


def _render_directive_form(crew_id: str) -> None:
    if getattr(storage, "save_directive", None) is None:
        st.caption(t("Envio de mensagens depende do banco da Pessoa B (save_directive)."))
        return
    st.text_area(t("Mensagem para o tripulante"), key="earth_msg", height=80)
    st.button(t("Enviar a {crew}", crew=crew_id), on_click=_send_directive, args=(crew_id,))
    sent = st.session_state.pop("earth_sent", None)
    if sent:
        st.success(sent)
    if _compat.COMMS_AVAILABLE:
        _render_sent_messages(crew_id)


_PART_LABELS = {"tone": N_("Tom do diário"), "persistence": N_("Persistência dos temas"), "sensors": N_("Sensores")}
_PART_MAX = {"tone": config.W_TONE * 100, "persistence": config.W_PERSIST * 100,
             "sensors": config.W_SENSORS * 100}
_BAND_NAME = {"verde": N_("verde"), "amarelo": N_("amarela"), "vermelho": N_("vermelha")}


def _render_breakdown(rep) -> None:
    """Composição do índice: quanto cada parte pesou e por quê, em palavras."""
    st.markdown("**" + t("Composição do índice") + "**")
    df = pd.DataFrame([{"parte": t(_PART_LABELS[k]), "pontos": rep.risk_breakdown.get(k, 0.0),
                        "máximo": _PART_MAX[k]} for k in _PART_LABELS])
    base = alt.Chart(df).encode(y=alt.Y("parte:N", sort=None, title=None,
                                        axis=alt.Axis(labelLimit=220, labelOverlap=False)))
    chart = (base.mark_bar(opacity=0.25).encode(x=alt.X("máximo:Q", title=t("pontos do índice")))
             + base.mark_bar().encode(x="pontos:Q", tooltip=[alt.Tooltip("parte:N", title=t("Parte")),
                                                              alt.Tooltip("pontos:Q", title=t("pontos")),
                                                              alt.Tooltip("máximo:Q", title=t("máximo"))]))
    st.altair_chart(chart.properties(height=150), use_container_width=True)
    for key, label in _PART_LABELS.items():
        pts = rep.risk_breakdown.get(key, 0.0)
        st.markdown("- " + t("**{label}:** {pts} de {max} pontos. {why}", label=t(label), pts=f"{pts:.0f}",
                             max=f"{_PART_MAX[key]:.0f}", why=rep.breakdown_why.get(key, "")))
    st.caption(t("Soma: {risk} de 100.", risk=rep.risk) + " " + " ".join(rep.breakdown_notes))


def _render_week(rep) -> None:
    """A semana em perspectiva: faixa de cada dia e comparação com a semana anterior."""
    icons = " ".join(f"{earth_data.BAND_ICON[b]}&nbsp;{d}" for d, b in zip(rep.trend_days, rep.trend_bands))
    st.markdown("**" + t("A semana, dia a dia:") + f"** {icons}", unsafe_allow_html=True)
    w, prev = rep.week, rep.prev_week
    c = st.columns(3)
    delta = None if not prev else t("{delta} vs semana anterior", delta=f"{w['mean'] - prev['mean']:+d}")
    c[0].metric(t("Índice médio da semana"), w["mean"], delta=delta, delta_color="inverse")
    c[1].metric(t("Pior dia"), w["worst"], help=t("Dia {day} da missão", day=w["worst_day"]))
    b = w["bands"]
    c[2].metric(t("Dias por faixa"), f"🟢{b['verde']}  🟡{b['amarelo']}  🔴{b['vermelho']}")


def _render_sensors(rep) -> None:
    rows = [{t("sensor"): report_mod.sensor_label(k).capitalize(), t("hoje"): t(v),
             t("dias fora do padrão na semana"): t("{a} de {b}", a=rep.sensor_days_off.get(k, 0), b=rep.week["days"])}
            for k, v in rep.sensor_dev.items()]
    st.markdown("**" + t("Sensores (em relação ao padrão do próprio tripulante)") + "**")
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def _render_mission_context(rep) -> None:
    ctx = rep.mission_context
    st.markdown("**" + t("Contexto da missão") + "**")
    st.markdown("- " + t("Dias fora do verde: {a} de {b} analisados.", a=ctx["days_not_green"], b=ctx["days_total"]))
    if not ctx["episodes"]:
        st.markdown("- " + t("Nenhum episódio no vermelho até agora."))
    for e in ctx["episodes"]:
        fim = t("em curso") if e["ongoing"] else t("até o dia {day}", day=e["end"])
        st.markdown("- " + t("Episódio no vermelho: do dia {start} {end}, pico {peak}.", start=e["start"], end=fim,
                             peak=e["peak"]))


def _render_details(rep, crew_id: str, start: int, end: int) -> None:
    _render_breakdown(rep)
    if rep.alert_reasons:
        st.markdown("**" + t("Motivo do alerta:") + "** " + "; ".join(rep.alert_reasons))
    if rep.theme_days:
        st.markdown("**" + t("Temas (dias na semana):") + "** " + ", ".join(
            f"{t(config.THEME_LABELS.get(th, th))} ({n}" + (t(", habitual") if th in rep.habitual_themes else "") + ")"
            for th, n in rep.theme_days.items()))
    _render_sensors(rep)
    for d in rep.discordance:
        st.warning(t("Discordância: {text}.", text=d))
    if rep.mood:
        st.markdown("**" + t("Humor confirmado pelo astronauta:") + "** " + t(rep.mood))
    support = earth_data.support_rows(crew_id, start, end)
    if support:
        st.markdown("**" + t("Apoio prestado a bordo (dias {a} a {b}):", a=start, b=end) + "**")
        st.dataframe(pd.DataFrame(support), hide_index=True, use_container_width=True)
    _render_mission_context(rep)
    q = rep.data_days
    st.markdown("**" + t("Qualidade dos dados:") + "** " + t(
        "diário em {d} de {w} dias, sensores em {s} de {w}.", d=q["diario"], w=q["janela"], s=q["sensores"]))
    if rep.missing_diary_days:
        st.caption(t("Dias sem entrada: {days}", days=", ".join(str(d) for d in rep.missing_diary_days)))
    msgs = []
    if _compat.COMMS_AVAILABLE:
        import comms
        msgs = comms.earth_messages(rep.pseudonym)
    if msgs:       # o que a Terra de fato sabe (a confirmação volta com atraso)
        st.caption(t("Última mensagem da Terra: {state}.", state=_message_state(msgs[0])))
    elif rep.last_directive_read is None:
        st.caption(t("A Terra ainda não enviou mensagem a este tripulante."))
    else:
        st.caption(t("Última mensagem da Terra: {state}.", state=t("lida") if rep.last_directive_read else t("ainda não lida")))


def _render_contexts(ctx: dict) -> None:
    """O que mais se repete e o que foge do habitual do tripulante. Só categorias e contagens, nunca o diário."""
    st.markdown("**" + t("Contextos que merecem atenção") + "**")
    st.caption(t("Dias {a} a {b} da missão. Só categorias de tema, contagens de dias e "
                 "sensores em palavras; nada do que o astronauta escreveu.", a=ctx["start"], b=ctx["end"]))
    if not ctx["recurring"] and not ctx["out_of_norm"]:
        st.markdown(t("Nada recorrente nem fora do habitual neste período."))
        return
    if ctx["recurring"]:
        st.markdown("*" + t("O que mais se repete") + "*")
        st.dataframe(pd.DataFrame([{
            t("tema"): r["label"], t("dias"): t("{a} de {b}", a=r["days"], b=r["of"]), t("último dia"): r["last_day"],
            t("em relação ao período anterior"): r["trend"] or t("sem período anterior")} for r in ctx["recurring"]]),
            hide_index=True, use_container_width=True)
    if ctx["out_of_norm"]:
        st.markdown("*" + t("O que foge do habitual deste tripulante") + "*")
        for item in ctx["out_of_norm"]:
            st.markdown(f"- {item['text']}")
    for item in ctx["combos"]:
        st.markdown(f"- {item['text']}")


def _render_clinical(crew_id: str, key: str, start: int, end: int, today: int, day: int) -> None:
    """Relatório clínico: o que a equipe de saúde recebe. O astronauta não o vê.

    Nas visões "Intervalo" e "Dia específico" é o relatório como estava no último dia escolhido."""
    as_of = (day if key == "day" else end) if key in ("day", "range") else today
    rep = earth_data.clinical_report(crew_id) if as_of == today else earth_data.report_at(crew_id, as_of)
    if rep is None:
        return
    st.subheader(t("Relatório clínico"))
    if as_of != today:
        st.caption(t("Consulta ao histórico: o relatório como estava no dia {day}. "
                     "O dia da missão continua sendo o {today}.", day=as_of, today=today))
    c = st.columns(3)
    c[0].metric(t("Identificação"), rep.pseudonym)
    c[1].metric(t("Dia da missão"), t("{day} de {total}", day=rep.period_end_day, total=rep.mission_total_days))
    c[2].metric(t("Índice"), f"{rep.risk} · {t(_BAND_NAME.get(rep.band, rep.band))}")
    st.caption(t("Relatório {kind} · dias {a} a {b} da missão", kind=t(rep.kind), a=rep.period_start_day,
                 b=rep.period_end_day))
    st.info(rep.summary)
    ctx = rep.contexts if key == "day" else earth_data.contexts_for(crew_id, start, end)
    _render_contexts(ctx)
    _render_week(rep)
    if rep.band == "verde":          # dia verde: o essencial na tela e o resto sob demanda
        with st.expander(t("Ver detalhes")):
            _render_details(rep, crew_id, start, end)
    else:
        _render_details(rep, crew_id, start, end)


def _render_link() -> None:
    """Relatórios que chegaram pelo link, e fila do link (Pessoa B)."""
    import comms
    st.subheader(t("Link com a nave"))
    received = comms.earth_reports()
    if not received:
        st.info(t("Nenhum relatório recebido ainda. Ele chega depois do atraso do sinal e só fora do blackout."))
    else:
        rows = []
        for item in received[:10]:
            r = item["report"]
            rows.append({t("recebido"): item["received_at"].replace("T", " "), t("identificação"): r["pseudonym"],
                         t("tipo"): t(r["kind"]), t("dias"): f"{r['period_start_day']}–{r['period_end_day']}",
                         t("índice"): r["risk"], t("faixa"): t(r["band"])})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown("**" + t("Fila do link") + "**")
    fila = comms.queue_status()
    if fila:
        cols = {"sentido": t("sentido"), "conteúdo": t("conteúdo"), "bytes": "bytes", "status": t("status")}
        st.dataframe(pd.DataFrame([{"#": r["#"], **{new: r[old] for old, new in cols.items()}} for r in fila]),
                     hide_index=True, use_container_width=True)
    else:
        st.caption(t("Fila vazia."))


def _mark_seen() -> None:
    import comms
    comms.mark_reads_seen()


def _render_read_banner() -> None:
    """Aviso no topo quando um tripulante leu uma mensagem da Terra (chega depois do atraso do sinal)."""
    import comms
    new = comms.unseen_reads()
    if not new:
        return
    lines = [t("**{who}** leu a mensagem do dia {sent} (lida no dia {read} da missão)", who=m["pseudonym"],
               sent=m["sent_day"], read=m["read_day"]) for m in new]
    st.info("🆕 " + "\n\n🆕 ".join(lines))
    st.button(t("Ok, visto"), key="earth_seen", on_click=_mark_seen)


def render() -> None:
    if _compat.COMMS_AVAILABLE:
        import comms
        comms.tick()
        status = link_status.link_status()
        (st.info if status.active else st.warning)("📡 " + link_status.earth_text(status))
        _render_read_banner()
        st.button(t("🔄 Verificar novos pacotes"), key="earth_refresh")
    st.caption(t("A Terra vê índices e temas, nunca o texto do diário."))
    rows = earth_data.overview_rows()
    _render_overview(rows)
    crew_id = st.selectbox(t("Tripulante em detalhe"), config.CREW_IDS, key="earth_crew")
    today = int(storage.get_setting("sim_day"))
    key, start, end, label, day = _pick_view(today)
    st.subheader(t("{crew}: risco do dia {a} ao dia {b} ({label})", crew=crew_id, a=start, b=end, label=label))
    _render_trend(crew_id, start, end, focus_day=day if key == "day" else 0)
    _render_period_stats(crew_id, start, end)
    _render_clinical(crew_id, key, start, end, today, day)
    st.subheader(t("Mensagem da Terra"))
    _render_directive_form(crew_id)
    if _compat.COMMS_AVAILABLE:
        st.divider()
        _render_link()
