from dataclasses import dataclass

from findr.domain.text import normalize, split_words


@dataclass(frozen=True, slots=True)
class Query:
    """Immutable value object holding the raw user input and its normalized forms."""

    raw: str
    normalized: str
    tokens: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> "Query":
        text = raw.strip()
        normalized = normalize(text)
        return cls(raw=text, normalized=normalized, tokens=tuple(split_words(normalized)))

    @property
    def is_empty(self) -> bool:
        return not self.tokens
