"""Polaridade do texto de -1 a +1, com regra de negação (RF04)."""
from typing import Optional

import config
from core.lexicon import Lexicon, load_lexicon, tokenize


def polarity(text: str, lexicon: Optional[Lexicon] = None) -> float:
    """(positivas - negativas) / max(1, positivas + negativas).

    Uma palavra de tom tem o sinal invertido se uma das 2 palavras anteriores
    for "não", "nem" ou "nunca". Sem palavra de tom, devolve 0.0.
    """
    lex = lexicon or load_lexicon()
    tokens = tokenize(text)
    pos = neg = 0
    for i, tok in enumerate(tokens):
        if tok in lex.negation:
            continue
        sign = 0
        if lex.matches_any(tok, lex.positive):
            sign = 1
        elif lex.matches_any(tok, lex.negative):
            sign = -1
        if sign == 0:
            continue
        window = tokens[max(0, i - config.NEGATION_WINDOW):i]
        if any(w in lex.negation for w in window):
            sign = -sign
        if sign > 0:
            pos += 1
        else:
            neg += 1
    return (pos - neg) / max(1, pos + neg)
