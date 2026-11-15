"""Aba do astronauta: diário, retorno, humor, contramedida, histórico e escalonamento
(RF02, RF09 a RF12, RF20, RNF07)."""
import time
from collections import Counter

import altair as alt
import pandas as pd
import streamlit as st

import config
import demo_seed
import storage
from core.pipeline import analyze_entry
from ingest.source import baseline_for, sensor_for
from models import Analysis, CountermeasureLog, Entry, Feedback
from support import explain as explain_mod
from support import link_status
from support import report as report_mod
from support.countermeasures import CATALOG
from support.feedback import build_feedback
from support.i18n import t
from ui import _compat

BAND_COLORS = {"verde": "#2e9e5b", "amarelo": "#e0a800", "vermelho": "#d64545"}
BAND_EMOJI = {"verde": "🟢", "amarelo": "🟡", "vermelho": "🔴"}


def _sim_day() -> int:
    return int(storage.get_setting("sim_day"))


# ---------------------------------------------------------------- diário
def _use_example(crew_id: str, day: int) -> None:
    text = _compat.demo_text(crew_id, day)
    if text:
        st.session_state["diary_text"] = text


def _on_crew_change() -> None:
    """O dia da missão é um só para todos: trocar de tripulante só limpa o campo."""
    st.session_state["diary_text"] = ""
    st.session_state.pop("last", None)


def _on_save() -> None:
    """Callback do botão: roda antes da nova renderização, então pode limpar o campo."""
    text = st.session_state.get("diary_text", "").strip()
    if not text:
        st.session_state["empty_warning"] = True
        return
    st.session_state["empty_warning"] = False
    _submit(st.session_state["crew"], _sim_day(), text)


def _submit(crew_id: str, day: int, text: str) -> None:
    # Um diário por dia: escrever de novo no mesmo dia substitui a entrada anterior
    existing = next((a.entry_id for a in storage.get_history(crew_id, 1) if a.day == day), None)
    entry = Entry(id=existing, crew_id=crew_id, day=day, date=config.date_for_day(day), text=text)
    entry.id = storage.save_entry(entry)
    history = [a for a in storage.get_history(crew_id, config.WINDOW_DAYS) if a.day != day]
    baseline, is_example = baseline_for(crew_id)
    sensors = sensor_for(crew_id, entry.date)

    analysis = analyze_entry(entry, history, baseline, sensors)
    feedback = build_feedback(analysis)
    storage.save_analysis(analysis)
    if feedback.countermeasure and storage.save_countermeasure:  # RF18: guarda para perguntar depois
        storage.save_countermeasure(CountermeasureLog(
            None, entry.id, crew_id, day, feedback.countermeasure.theme,
            CATALOG[feedback.countermeasure.theme].title))     # guarda o título-fonte (português); traduz ao exibir

    # Relatórios automáticos (RF13): imediato ao entrar no vermelho; semanal a cada 7 dias
    auto_sent = report_mod.after_entry(
        crew_id, analysis, history,
        lambda crew, immediate: _compat.send_report(crew, immediate=immediate))

    st.session_state["last"] = {
        "analysis": analysis, "feedback": feedback,
        "no_sensor": sensors is None, "example_baseline": is_example,
        "replaced": existing is not None, "auto_sent": auto_sent,
    }
    st.session_state.pop("timer_end", None)
    st.session_state["diary_text"] = ""


def _confirm_mood(key: str, a: Analysis) -> None:
    a.mood_confirmed = st.session_state[key]
    storage.save_analysis(a)  # upsert por entry_id


def _render_diary(crew_id: str, day: int) -> None:
    st.subheader(t("Diário"))
    st.caption(t("Escreva o que quiser, do jeito que quiser. O texto fica só aqui na nave."))
    st.info(t("📝 Escreva o diário em português. A análise dos textos (temas e tom) foi feita para o português; "
              "em outro idioma ela não funciona bem. Os textos de exemplo também estão em português."))
    st.text_area(t("Como foi o seu dia?"), key="diary_text", height=140,
                 label_visibility="collapsed", placeholder=t("Escreva livremente..."))
    c1, c2 = st.columns([1, 1])
    c1.button(t("Salvar entrada"), type="primary", on_click=_on_save)
    if st.session_state.get("empty_warning"):
        st.warning(t("Escreva ao menos uma palavra para eu poder ajudar."))
    if _compat.demo_text(crew_id, day):
        c2.button(t("Usar texto de exemplo"), on_click=_use_example, args=(crew_id, day))


# ---------------------------------------------------------------- retorno
def _render_timer(seconds: int) -> None:
    if st.button(t("Iniciar temporizador"), key="timer_start"):
        st.session_state["timer_end"] = time.time() + seconds

    @st.fragment(run_every=1)
    def tick() -> None:
        end = st.session_state.get("timer_end")
        if not end:
            return
        remaining = int(end - time.time())
        if remaining > 0:
            st.progress(min(1.0, max(0.0, 1 - remaining / seconds)),
                        text=f"{remaining // 60:02d}:{remaining % 60:02d}")
        else:
            st.success(t("Tempo concluído. Como você se sente agora?"))

    tick()


def _render_feedback(last: dict) -> None:
    a: Analysis = last["analysis"]
    fb: Feedback = last["feedback"]

    st.subheader(t("Retorno"))
    st.markdown(f"{BAND_EMOJI[a.band]} **" + t("Índice {risk}/100 · faixa {band}", risk=a.risk, band=t(a.band)) + "**")
    if fb.escalate:  # RF12
        st.error(fb.text)
    else:
        st.info(fb.text)
    if fb.reason:  # RNF06: sempre mostra o que gerou o retorno
        st.caption(t("Por que estou dizendo isso: {reason}", reason=fb.reason))
    for kind in last.get("auto_sent", []):
        st.caption(t("Relatório {kind} enviado à Terra.", kind=t(kind)))
    why = explain_mod.astronaut_text(a)
    if why:
        st.caption(why)
    if last.get("replaced"):
        st.caption(t("Você já tinha escrito neste dia: esta entrada substituiu a anterior."))
    if last.get("no_sensor"):
        st.caption(t("Sem leitura de sensores hoje: esta análise usou só o seu texto."))
    if last.get("example_baseline"):
        st.caption(t("Usando um padrão de bem-estar de exemplo (arquivo do tripulante não encontrado)."))

    # Humor do dia (RF20): leitura que o astronauta confirma ou corrige
    st.markdown(t("**Hoje você parece {mood}.** Está certo?", mood=t(a.mood)))
    current = a.mood_confirmed or a.mood
    mood_key = f"mood_choice_{a.entry_id}"
    st.radio(t("Confirme ou corrija"), config.MOOD_LABELS, horizontal=True, key=mood_key, format_func=t,
             index=config.MOOD_LABELS.index(current) if current in config.MOOD_LABELS else 0,
             on_change=_confirm_mood, args=(mood_key, a), label_visibility="collapsed")
    if a.mood_confirmed:
        st.caption(t("Registrado: {mood}. Obrigado, isso ajuda a me ajustar a você.", mood=t(a.mood_confirmed)))

    cm = fb.countermeasure  # RF10
    if cm:
        with st.expander(t("O que você pode fazer agora: {title}", title=cm.title), expanded=True):
            for i, step in enumerate(cm.steps, 1):
                st.markdown(f"{i}. {step}")
            if cm.timer_seconds:
                _render_timer(cm.timer_seconds)


# ---------------------------------------------------------------- aviso do relatório (RF17 revisto)
def _render_report_notice(crew_id: str, band: str) -> None:
    """O astronauta não envia nem vê o relatório: o envio é automático. Ele só é avisado."""
    with st.container(border=True):
        st.markdown("**" + t("Relatório à Terra") + "**")
        st.markdown(report_mod.notice_text(crew_id, _sim_day(), band))
        st.caption(t("O que é compartilhado: {items}. O texto do seu diário nunca é enviado.",
                     items=t(report_mod.NOTICE_CATEGORIES)))
        st.caption("📡 " + link_status.astronaut_text(link_status.link_status()))


# ---------------------------------------------------------------- histórico
def _render_history(crew_id: str) -> None:
    history = storage.get_history(crew_id, config.HISTORY_CHART_DAYS)
    if history:
        st.subheader(t("Seu histórico (dia {a} ao dia {b})", a=history[0].day, b=history[-1].day))
    else:
        st.subheader(t("Seu histórico"))
    if not history:
        st.caption(t("O histórico aparece depois da primeira entrada."))
        return

    # Um ponto por dia: a última entrada do dia
    by_day = {a.day: a for a in history}
    df = pd.DataFrame(
        [{"dia": d, "índice": a.risk, "faixa": a.band} for d, a in sorted(by_day.items())]
    )
    domain = list(BAND_COLORS)
    line = alt.Chart(df).mark_line(color="#888").encode(
        x=alt.X("dia:O", title=t("Dia da missão")),
        y=alt.Y("índice:Q", scale=alt.Scale(domain=[0, 100]), title=t("Índice")))
    points = alt.Chart(df).mark_circle(size=90).encode(
        x="dia:O", y="índice:Q",
        color=alt.Color("faixa:N", scale=alt.Scale(domain=domain, range=list(BAND_COLORS.values())),
                        legend=alt.Legend(title=t("Faixa"),
                                          labelExpr=" : ".join(f"datum.label == '{b}' ? '{t(b)}'" for b in domain)
                                          + " : datum.label")),
        tooltip=[alt.Tooltip("dia:O", title=t("Dia da missão")), alt.Tooltip("índice:Q", title=t("Índice")),
                 alt.Tooltip("faixa:N", title=t("Faixa"))])
    st.altair_chart(line + points, use_container_width=True)

    days_by_theme: Counter = Counter()
    seen: set[tuple[int, str]] = set()
    for a in history:
        for th in a.themes:
            if (a.day, th) not in seen:
                seen.add((a.day, th))
                days_by_theme[th] += 1
    if days_by_theme:
        tdf = pd.DataFrame(
            [{"tema": t(config.THEME_LABELS[th]), "dias": n} for th, n in days_by_theme.most_common()]
        )
        st.altair_chart(
            alt.Chart(tdf).mark_bar().encode(x=alt.X("dias:Q", title=t("Dias em que apareceu")),
                                             y=alt.Y("tema:N", sort="-x", title=None)),
            use_container_width=True)
    else:
        st.caption(t("Nenhum tema apareceu nesse período."))


# ---------------------------------------------------------------- acompanhamento (RF18)
def _answer_followup(cm_id: int, done: bool, helped) -> None:
    storage.record_followup(cm_id, done, helped)


def _render_followup(crew_id: str, day: int) -> None:
    if not storage.get_pending_followup:
        return
    pending = storage.get_pending_followup(crew_id, day, config.FOLLOWUP_MAX_DAYS)
    if not pending:
        return
    with st.container(border=True):
        st.markdown(t("**Sobre a sugestão de dias atrás: {title}.** Como foi?", title=t(pending.title)))
        c1, c2, c3 = st.columns(3)
        c1.button(t("Fiz e ajudou"), key=f"fu_ok_{pending.id}", on_click=_answer_followup,
                  args=(pending.id, True, True))
        c2.button(t("Fiz, mas não ajudou"), key=f"fu_no_{pending.id}", on_click=_answer_followup,
                  args=(pending.id, True, False))
        c3.button(t("Não consegui fazer"), key=f"fu_skip_{pending.id}", on_click=_answer_followup,
                  args=(pending.id, False, None))


# ---------------------------------------------------------------- Terra → astronauta
def _read_directive(directive_id: int) -> None:
    storage.mark_read(directive_id)
    _compat.acknowledge_read(directive_id)      # a Terra fica sabendo que foi lida (com o atraso do sinal)


def _render_directives(crew_id: str) -> None:
    _compat.pull_directives(crew_id)  # traz o que já chegou pelo link (pode vir vazio)
    directives = storage.list_directives(crew_id)
    unread = sum(1 for d in directives if not d.read)
    st.subheader(t("Mensagens da Terra") + (t(" ({n} nova(s))", n=unread) if unread else ""))
    if not directives:
        st.caption(t("Nenhuma mensagem ainda. O apoio a bordo continua funcionando sem a Terra."))
        return
    for d in directives:
        with st.container(border=True):
            st.markdown(("" if d.read else "🆕 ") + d.text)
            st.caption(t("Enviada em {when}", when=d.sent_at))
            if not d.read:
                st.button(t("Marcar como lido"), key=f"read_{d.id}",
                          on_click=_read_directive, args=(d.id,))
                if d.ref is not None:
                    st.caption(t("Ao marcar como lido, a equipe da Terra é avisada de que você leu."))


def _latest_for(crew_id: str):
    """Retorno do último dia analisado do tripulante, para a tela não ficar vazia ao trocar."""
    history = storage.get_history(crew_id, config.HISTORY_CHART_DAYS)
    if not history:
        return None
    a = history[-1]
    return {"analysis": a, "feedback": build_feedback(a), "no_sensor": False, "example_baseline": False}


# ---------------------------------------------------------------- entrada
def render() -> None:
    top = st.columns([1, 1])
    crew_id = top[0].selectbox(t("Tripulante"), config.CREW_IDS, key="crew", on_change=_on_crew_change)
    day = _sim_day()
    if not demo_seed.has_entry(crew_id, day):
        top[1].caption(t("O diário de hoje ainda não foi escrito. Ele é obrigatório para a missão avançar."))

    left, right = st.columns([1, 1], gap="large")
    with left:
        _render_followup(crew_id, day)
        _render_diary(crew_id, day)
        _render_directives(crew_id)
    with right:
        last = st.session_state.get("last")
        if not (last and last["analysis"].crew_id == crew_id):
            last = _latest_for(crew_id)
        if last:
            last = {**last, "feedback": build_feedback(last["analysis"])}   # refaz no idioma atual
            _render_feedback(last)
            _render_report_notice(crew_id, last["analysis"].band)
        else:
            st.subheader(t("Retorno"))
            st.caption(t("Depois que você salvar uma entrada, o retorno aparece aqui."))
    st.divider()
    _render_history(crew_id)
