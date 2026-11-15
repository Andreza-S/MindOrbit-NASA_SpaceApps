"""Idioma da tela: português e inglês (o app abre em inglês; o seletor fica no topo).

Como funciona: o texto-fonte do código é o português. `t("texto em português", chave=valor)` devolve o
mesmo texto, ou a tradução de support/i18n_en.py quando o idioma é inglês. Os valores guardados no banco
(faixas, humores, temas, títulos de contramedidas) continuam em português: só o que aparece na tela muda.

O que NÃO é traduzido: o texto que o astronauta escreve e a análise dele. O léxico (data/lexicon) e os
diários da demonstração são em português.

O idioma vem da sessão do Streamlit (st.session_state["lang_code"]); fora do Streamlit, de `set_lang`.
"""
LANGS = {"en": "English", "pt": "Português"}
DEFAULT_APP_LANG = "en"       # idioma em que o app abre
_lang = "pt"                  # fora do Streamlit (testes, scripts): o texto-fonte


def set_lang(code: str) -> None:
    global _lang
    _lang = code if code in LANGS else "pt"


def _session():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is None:
            return None
        import streamlit as st
        return st.session_state
    except Exception:
        return None


session_state = _session      # usado também por storage/db.py (um banco por visitante)


def get_lang() -> str:
    state = _session()
    if state is not None:
        code = state.get("lang_code")
        if code in LANGS:
            return code
    return _lang


def N_(text: str) -> str:
    """Marca um texto para tradução sem traduzir agora (catálogos definidos na importação)."""
    return text


def t(text: str, **values) -> str:
    """Traduz `text` (português) para o idioma atual e preenche {variáveis}."""
    if get_lang() == "en":
        from support.i18n_en import EN
        text = EN.get(text, text)
    return text.format(**values) if values else text


def days(n: int) -> str:
    return t("{n} dia", n=n) if n == 1 else t("{n} dias", n=n)


def num(value: float, digits: int = 1) -> str:
    """Número decimal com vírgula em português e ponto em inglês."""
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if get_lang() == "pt" else text
