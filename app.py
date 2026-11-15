"""MindOrbit: apoio de bordo ao bem-estar do astronauta.

Rodar:  streamlit run app.py
"""
import streamlit as st

import storage
from storage import session_db
from support import i18n
from support.i18n import t
from ui import astronaut_tab
from ui import day_nav
from ui.earth_tab import render as render_earth
from ui.sidebar import render as render_sidebar

st.set_page_config(page_title="MindOrbit", page_icon="🛰️", layout="wide")
if session_db.enabled() and "db_path" not in st.session_state:
    st.session_state["db_path"] = str(session_db.new_path())     # hospedado: um banco por visitante, no dia 1
storage.init_db()


@st.cache_resource
def _fresh_start() -> bool:
    """Cada vez que o app é iniciado, a demonstração recomeça no dia 1, sem diários nem relatórios.
    Atualizar a página do navegador não zera nada: isto roda uma vez por inicialização do servidor."""
    storage.reset_demo()
    return True


if not session_db.enabled():      # no computador do usuário, o app recomeça no dia 1 a cada inicialização
    _fresh_start()

st.session_state.setdefault("lang_code", i18n.DEFAULT_APP_LANG)
head_title, head_lang = st.columns([4, 1])
head_title.title("🛰️ MindOrbit")
head_lang.radio(t("Idioma"), list(i18n.LANGS), format_func=i18n.LANGS.get, horizontal=True, key="lang_code")
st.caption(t("Armazenamento: {name}", name=storage.BACKEND_NAME))
render_sidebar()
day_nav.render()

tab_astronaut, tab_earth = st.tabs([t("Astronauta"), t("Terra")])
with tab_astronaut:
    astronaut_tab.render()
with tab_earth:
    render_earth()
