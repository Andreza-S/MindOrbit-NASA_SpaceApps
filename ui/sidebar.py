"""Barra lateral da demonstração: dia da missão, sensores e link nave ↔ Terra.

Une a barra da Pessoa B (link, blackout, atraso real NASA/JPL, chegada dos sensores) com o dia
único da missão: o campo "Ir para o dia" leva todos ao dia digitado (as setas ficam em ui/day_nav.py).
Os relatórios semanais e imediatos saem sozinhos quando o diário é salvo (support/report.py);
aqui só há um atalho de demo.
"""
import streamlit as st

import config
import demo_seed
import storage
from ui import _compat
from support.i18n import num, t
from ui.day_nav import afterwards as _afterwards

ULTIMO_DIA = config.MISSION_DAYS


def _ir_para_o_dia() -> None:
    alvo = int(st.session_state["sb_goto"])
    incluir = bool(st.session_state.get("sb_goto_incluir", True))
    gravados = demo_seed.go_to_day(alvo, include_day=incluir)
    novos = sum(gravados.values())
    _afterwards(t("Dia {day} de {total}: ", day=alvo, total=ULTIMO_DIA)
                + (t("{n} diário(s) da demo analisado(s).", n=novos) if novos else t("o histórico já estava pronto."))
                + ("" if incluir else " " + t("O diário do dia está em branco.")))


def _reiniciar() -> None:
    storage.reset_demo()
    for key in ("last", "sb_goto", "diary_text", "sb_reset_ok", "earth_view", "earth_first", "earth_last",
                "earth_day"):
        st.session_state.pop(key, None)
    st.session_state["sidebar_msg"] = t("Demo reiniciada: dia 1, sem diários nem relatórios.")


def _atalho_semanal() -> None:
    import comms
    n = comms.send_weekly_reports()
    st.session_state["sidebar_msg"] = t("Atalho de demo: {n} relatório(s) semanal(is) na fila.", n=n)


def _blackout() -> None:
    import comms
    from support import link_status
    if st.session_state["sb_blackout"]:
        link_status.start_blackout(int(st.session_state.get("sb_blackout_days", 0)) or None)
    else:
        link_status.end_blackout()
    comms.tick()


def _atraso() -> None:
    storage.set_setting("delay_seconds", st.session_state["sb_delay"])


def _modo_atraso() -> None:
    storage.set_setting("delay_mode", "jpl" if st.session_state["sb_jpl"] else "manual")


def _render_link(sb, dia: int) -> None:
    import comms
    sb.divider()
    sb.subheader(t("Link nave ↔ Terra"))
    st.session_state["sb_blackout"] = storage.get_setting("blackout") == "1"   # acompanha o fim automático
    sb.toggle(t("Blackout (sem comunicação)"), key="sb_blackout", on_change=_blackout)
    sb.number_input(t("Duração do blackout (dias da missão, 0 = sem previsão)"), min_value=0, max_value=60,
                    value=0, step=1, key="sb_blackout_days",
                    help=t("Vale quando você liga o blackout. Ele termina sozinho no dia previsto."))
    real = sb.toggle(t("Atraso real Terra–Marte (NASA/JPL)"), value=storage.get_setting("delay_mode") == "jpl",
                     key="sb_jpl", on_change=_modo_atraso)
    if real:
        from simulator.light_delay import SEGUNDOS_LUZ_POR_AU, atraso_minutos
        minutos = atraso_minutos(dia)
        km = minutos * 60 / SEGUNDOS_LUZ_POR_AU * 149.6
        sb.caption(t("Hoje o sinal leva **{min} min** para ir da nave à Terra (≈ {km} milhões de km). "
                     "Na demo: {sec} s. Fonte: elementos orbitais do NASA JPL.",
                     min=num(minutos), km=f"{km:.0f}", sec=f"{minutos:.0f}"))
    else:
        sb.slider(t("Atraso do sinal (s)"), 3, 60, int(float(storage.get_setting("delay_seconds"))), key="sb_delay",
                  on_change=_atraso, help=t("Demonstração acelerada: 1 s aqui representa cerca de 1 min até Marte."))
    sb.button(t("Atalho de demo: enviar semanais agora"), on_click=_atalho_semanal, use_container_width=True,
              help=t("Os relatórios saem sozinhos nos dias 7, 14, 21… e quando o índice entra no vermelho."))
    if sb.button(t("🔄 Atualizar link"), use_container_width=True):
        comms.tick()
    fila = comms.queue_status()
    retidos = sum(1 for p in fila if p["code"] == "held")
    transito = sum(1 for p in fila if p["code"] == "transit")
    sb.caption(t("Fila: {held} retido(s) · {transit} em trânsito", held=retidos, transit=transito))


def render() -> None:
    sb = st.sidebar
    sb.title(t("🛰️ Controle da demo"))
    dia = int(storage.get_setting("sim_day"))
    sb.metric(t("Dia da missão"), t("{day} de {total}", day=dia, total=ULTIMO_DIA),
              help=t("Data: {date}", date=config.date_for_day(dia)))
    sb.progress(dia / ULTIMO_DIA)

    with sb.expander(t("Ir para o dia da missão"), expanded=True):
        st.session_state.setdefault("sb_goto", dia)
        st.number_input(t("Dia (1 a {total}): Enter ou o botão Ir aplicam", total=ULTIMO_DIA), min_value=1,
                        max_value=ULTIMO_DIA, step=1, key="sb_goto", on_change=_ir_para_o_dia)
        st.checkbox(t("Incluir o diário desse dia já analisado"), value=True, key="sb_goto_incluir",
                    help=t("Desmarcado, o histórico vai até a véspera e o dia fica em branco para escrever."))
        st.button(t("Ir"), on_click=_ir_para_o_dia, use_container_width=True)
    if st.session_state.get("sidebar_msg"):
        sb.caption(st.session_state["sidebar_msg"])
    with sb.expander(t("Reiniciar a demo")):
        st.caption(t("Apaga diários, análises, mensagens e a fila do link, e volta ao dia 1. "
                     "Use quando os dados de uma versão antiga ficarem guardados no banco."))
        st.checkbox(t("Tenho certeza"), key="sb_reset_ok")
        st.button(t("Reiniciar"), on_click=_reiniciar, disabled=not st.session_state.get("sb_reset_ok"),
                  use_container_width=True)
    if _compat.COMMS_AVAILABLE:
        from storage import db
        ultima = db.last_sensor_received(up_to_day=dia)
        if ultima:
            sb.caption(t("📡 Sensores recebidos até o dia {last} (hoje é o dia {day})", last=ultima["day"], day=dia))
        _render_link(sb, dia)
    sb.caption(t("Armazenamento: {name}", name=storage.BACKEND_NAME))
