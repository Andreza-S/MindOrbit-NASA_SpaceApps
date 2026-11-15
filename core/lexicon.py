"""Carrega o léxico em português e normaliza o texto (RF03, RF04, RNF09)."""
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Optional

import config


def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparar texto e léxico do mesmo jeito."""
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", normalize(text))


def term_matches(token: str, term: str) -> bool:
    """Termo curto casa por igualdade; termo longo casa por prefixo (flexões)."""
    if len(term) < config.MIN_STEM_LEN:
        return token == term
    return token.startswith(term)


class Lexicon:
    def __init__(self, themes: dict[str, list[str]], positive: list[str],
                 negative: list[str], negation: list[str]):
        self.themes = {k: [normalize(t) for t in v] for k, v in themes.items()}
        self.positive = [normalize(t) for t in positive]
        self.negative = [normalize(t) for t in negative]
        self.negation = set(normalize(t) for t in negation)

    def matches_any(self, token: str, terms: list[str]) -> bool:
        return any(term_matches(token, t) for t in terms)


@lru_cache(maxsize=4)
def _load(directory: str) -> Lexicon:
    d = Path(directory)
    read = lambda name: json.loads((d / name).read_text(encoding="utf-8"))
    return Lexicon(read("temas.json"), read("positivas.json"),
                   read("negativas.json"), read("negacao.json"))


def load_lexicon(directory: Optional[Path] = None) -> Lexicon:
    return _load(str(directory or config.LEXICON_DIR))
