"""Text normalization shared by queries and indexed candidates."""

import re
import unicodedata

_WORD_SEPARATORS = re.compile(r"[\s\-_./\\()\[\]{},:;+]+")


def normalize(text: str) -> str:
    """Case- and accent-insensitive form, so "configuracoes" matches "Configurações"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def split_words(normalized_text: str) -> list[str]:
    return [word for word in _WORD_SEPARATORS.split(normalized_text) if word]
