"""Marca os temas presentes em cada entrada do diário (RF03)."""
from typing import Optional

from core.lexicon import Lexicon, load_lexicon, tokenize


def theme_hits(text: str, lexicon: Optional[Lexicon] = None) -> dict[str, int]:
    """Número de palavras do texto que casam com cada tema (só os que aparecem)."""
    lex = lexicon or load_lexicon()
    tokens = tokenize(text)
    hits: dict[str, int] = {}
    for theme, terms in lex.themes.items():
        n = sum(1 for tok in tokens if lex.matches_any(tok, terms))
        if n:
            hits[theme] = n
    return hits


def detect_themes(text: str, lexicon: Optional[Lexicon] = None) -> list[str]:
    """Temas presentes, em ordem de número de acertos (maior primeiro)."""
    hits = theme_hits(text, lexicon)
    return sorted(hits, key=lambda t: (-hits[t], t))
