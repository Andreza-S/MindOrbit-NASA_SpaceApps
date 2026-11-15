"""Aba da Terra de reserva. Usada só se a Pessoa B não entregar ui/earth_tab.py."""
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

import config
import storage
from models import Directive
from support import report as report_mod
from ui import earth_data


def _send_directive(crew_id: str) -> None:
    text = st.session_state.get("earth_msg", "").strip()
    save = getattr(storage, "save_directive", None)
    if not text or save is None:
        return
    save(Directive(id=None, crew_id=crew_id, text=text,
                   sent_at=datetime.now().strftime("%d/%m %H:%M")))
    st.session_state["earth_msg"] = ""
    st.session_state["earth_sent"] = True


def _render_overview(rows: list[dict]) -> None:
    urgent = earth_data.attention_needed(rows)
    if urgent:
        st.error("Atenção prioritária: " + ", ".join(urgent) + " em faixa vermelha.")
    cols = st.columns(len(rows))
    for col, r in zip(cols, rows):
        with col.container(border=True):
            st.markdown(f"**{r['crew_id']}**")
            if r["sem_dados"]:
                st.caption("Sem dados ainda")
                continue
            st.markdown(f"{earth_data.BAND_ICON[r['band']]} Risco **{r['risk']}** ({r['band']})")
            st.caption(f"Dia {r['day']} · {r['mood']}")
            st.caption(f"Tema: {r['main_theme']}"
                       + (f" há {r['days_in_theme']} dias" if r["days_in_theme"] > 1 else ""))


def _render_trend(crew_id: str) -> None:
    data = earth_data.risk_trend(crew_id)
    if not data:
        st.caption("Sem histórico para este tripulante.")
        return
    df = pd.DataFrame(data)
    line = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("dia:Q", title="Dia da missão", axis=alt.Axis(tickMinStep=1)),
        y=alt.Y("risco:Q", title="Índice de risco", scale=alt.Scale(domain=[0, 100])),
        tooltip=["dia", "risco", "faixa"])
    rules = alt.Chart(pd.DataFrame({"y": [config.BAND_GREEN_MAX, config.BAND_YELLOW_MAX]})) \
        .mark_rule(strokeDash=[4, 4], opacity=0.5).encode(y="y:Q")
    st.altair_chart(line + rules, use_container_width=True)


def _render_directive_form(crew_id: str) -> None:
    if getattr(storage, "save_directive", None) is None:
        st.caption("Envio de mensagens depende do banco da Pessoa B (save_directive).")
        return
    st.text_area("Mensagem para o tripulante", key="earth_msg", height=80)
    st.button(f"Enviar a {crew_id}", on_click=_send_directive, args=(crew_id,))
    if st.session_state.pop("earth_sent", False):
        st.success("Mensagem enviada.")


_PART_LABELS = {"tone": "Tom do diário", "persistence": "Persistência dos temas", "sensors": "Sensores"}
_PART_MAX = {"tone": config.W_TONE * 100, "persistence": config.W_PERSIST * 100,
             "sensors": config.W_SENSORS * 100}


def _render_breakdown(rep) -> None:
    """Composição do índice: quanto cada parte contribuiu, de quanto poderia."""
    st.markdown("**Composição do índice**")
    df = pd.DataFrame([{"parte": _PART_LABELS[k], "pontos": rep.risk_breakdown.get(k, 0.0),
                        "máximo": _PART_MAX[k]} for k in _PART_LABELS])
    base = alt.Chart(df).encode(y=alt.Y("parte:N", sort=None, title=None))
    chart = (base.mark_bar(opacity=0.25).encode(x=alt.X("máximo:Q", title="pontos do índice"))
             + base.mark_bar().encode(x="pontos:Q", tooltip=["parte", "pontos", "máximo"])
             + base.mark_text(align="left", dx=4).encode(
                 x="pontos:Q", text=alt.Text("pontos:Q", format=".0f")))
    st.altair_chart(chart.properties(height=110), use_container_width=True)
    st.caption(f"Soma: {rep.risk} de 100. " + " ".join(rep.breakdown_notes))


def _render_clinical(crew_id: str) -> None:
    """Relatório clínico: o que a equipe de saúde recebe. O astronauta não o vê."""
    rep = earth_data.clinical_report(crew_id)
    if rep is None:
        return
    st.subheader("Relatório clínico")
    c = st.columns(3)
    c[0].metric("Identificação", rep.pseudonym)
    c[1].metric("Dia da missão", f"{rep.period_end_day} de {rep.mission_total_days}")
    c[2].metric("Índice", f"{rep.risk} · {rep.band}")
    st.caption(f"Relatório {rep.kind} · dias {rep.period_start_day} a {rep.period_end_day} da missão")
    if rep.onset_day is not None:
        st.markdown(f"**Piora em curso desde o dia {rep.onset_day}** "
                    f"({rep.period_end_day - rep.onset_day + 1} dias).")
    else:
        st.markdown("**Sem piora em curso:** o índice de hoje está no verde.")
    _render_breakdown(rep)
    if rep.alert_reasons:
        st.markdown("**Motivo do alerta:** " + "; ".join(rep.alert_reasons))
    if rep.theme_days:
        st.markdown("**Temas (dias na semana):** " + ", ".join(
            f"{config.THEME_LABELS.get(t, t)} ({n})" for t, n in rep.theme_days.items()))
    st.markdown("**Sensores:** " + "; ".join(
        report_mod.sensor_phrase(k, v) for k, v in rep.sensor_dev.items()))
    for d in rep.discordance:
        st.warning("Discordância: " + d + ".")
    if rep.mood:
        st.markdown(f"**Humor confirmado pelo astronauta:** {rep.mood}")
    if rep.support:
        st.markdown("**Apoio prestado a bordo:**")
        st.dataframe(pd.DataFrame(rep.support).rename(
            columns={"title": "contramedida", "days": "dias", "answer": "respostas"}),
            hide_index=True, use_container_width=True)
    q = rep.data_days
    st.markdown(f"**Qualidade dos dados:** diário em {q['diario']} de {q['janela']} dias, "
                f"sensores em {q['sensores']} de {q['janela']}.")
    if rep.missing_diary_days:
        st.caption("Dias sem entrada: " + ", ".join(str(d) for d in rep.missing_diary_days))
    if rep.last_directive_read is None:
        st.caption("A Terra ainda não enviou mensagem a este tripulante.")
    else:
        st.caption("Última mensagem da Terra: " + ("lida." if rep.last_directive_read else "ainda não lida."))


def render() -> None:
    st.caption("Painel da Terra (versão de reserva). A Terra vê índices e temas, "
               "nunca o texto do diário.")
    rows = earth_data.overview_rows()
    _render_overview(rows)
    crew_id = st.selectbox("Tripulante em detalhe", config.CREW_IDS, key="earth_crew")
    trend = earth_data.risk_trend(crew_id)
    if trend:
        first, last = trend[0]["dia"], trend[-1]["dia"]
        st.subheader(f"{crew_id}: risco do dia {first} ao dia {last}")
    else:
        st.subheader(f"{crew_id}: risco por dia")
    _render_trend(crew_id)
    _render_clinical(crew_id)
    st.subheader("Mensagem da Terra")
    _render_directive_form(crew_id)
