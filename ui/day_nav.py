"""Navegação pelos dias da missão: setas para voltar e avançar, sempre visíveis acima das abas.

O sistema é progressivo: só se vê o que aconteceu até o dia atual. Voltar mostra o estado daquele dia
(nada é apagado). Avançar exige que todos os tripulantes tenham escrito o diário do dia atual.
"""
import streamlit as st

import config
import demo_seed
import storage
from support import link_status as link
from support.i18n import t

ULTIMO_DIA = config.MISSION_DAYS


def afterwards(msg: str) -> None:
    st.session_state["sidebar_msg"] = msg
    st.session_state["sb_goto"] = int(storage.get_setting("sim_day"))   # o campo de dia acompanha
    st.session_state.pop("last", None)


def avancar() -> None:
    """O diário é obrigatório: só avança quando todos os tripulantes escreveram o do dia."""
    dia = int(storage.get_setting("sim_day"))
    if demo_seed.missing_crews(dia) or dia >= ULTIMO_DIA:
        return
    novo = dia + 1
    storage.set_setting("sim_day", str(novo))
    demo_seed.ingest(novo)
    afterwards(t("Dia {day} da missão. O diário de hoje está pendente para todos.", day=novo))


def voltar() -> None:
    dia = max(1, int(storage.get_setting("sim_day")) - 1)
    storage.set_setting("sim_day", str(dia))
    afterwards(t("Dia {day} da missão (o que veio depois continua guardado).", day=dia))


def preencher() -> None:
    dia = int(storage.get_setting("sim_day"))
    feitos = demo_seed.fill_missing(dia)
    afterwards(t("Diário da demo preenchido para {crew}.", crew=", ".join(feitos)) if feitos
               else t("Todos já escreveram o diário de hoje."))


def render() -> None:
    status = link.link_status()          # também encerra o blackout cujo dia previsto chegou
    dia = int(storage.get_setting("sim_day"))
    pendentes = demo_seed.missing_crews(dia)
    c1, c2, c3, c4 = st.columns([1, 3, 1, 4])
    c1.button("◀", key="nav_back", on_click=voltar, disabled=dia <= 1, use_container_width=True,
              help=t("Dia anterior: mostra os dados até aquele dia"))
    c2.markdown(f"<div style='text-align:center;font-size:1.4rem'><b>{t('Dia')} {dia}</b> {t('de')} {ULTIMO_DIA}"
                f"<br><span style='font-size:0.8rem;opacity:.7'>{config.date_for_day(dia)}</span></div>",
                unsafe_allow_html=True)
    c3.button("▶", key="nav_next", on_click=avancar, type="primary",
              disabled=bool(pendentes) or dia >= ULTIMO_DIA, use_container_width=True,
              help=t("Próximo dia (precisa do diário de hoje de todos)") if not pendentes
              else t("Falta o diário de: {crew}", crew=", ".join(pendentes)))
    if pendentes:
        c4.warning(t("Diário de hoje pendente: {crew}", crew=", ".join(pendentes)))
        c4.button(t("Preencher pendentes com o diário da demo"), key="nav_fill", on_click=preencher)
    else:
        c4.caption(t("Todos escreveram o diário de hoje."))
    st.progress(dia / ULTIMO_DIA)
    (st.warning if not status.active else st.caption)(link.short_text(status))
