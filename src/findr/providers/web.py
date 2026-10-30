from collections.abc import Iterable
from urllib.parse import quote_plus

from findr.domain.actions import OpenUri
from findr.domain.icons import themed_icon
from findr.domain.models import ResultKind, SearchResult
from findr.domain.ports import SearchProvider
from findr.domain.query import Query


class WebSearchProvider(SearchProvider):
    """Always-available fallback: "search the web for <query>", ranked last."""

    name = "web"
    SCORE = 0.01

    def __init__(self, url_template: str) -> None:
        if "{query}" not in url_template:
            raise ValueError("url_template must contain a '{query}' placeholder")
        self._url_template = url_template

    def search(self, query: Query) -> Iterable[SearchResult]:
        if query.is_empty:
            return []
        return [
            SearchResult(
                id="web-search",
                title=f"Pesquisar “{query.raw}” na web",
                subtitle=self._url_template.split("/")[2] if "//" in self._url_template else "Navegador",
                kind=ResultKind.WEB,
                score=self.SCORE,
                action=OpenUri(self._url_template.format(query=quote_plus(query.raw))),
                icon=themed_icon("web-browser", "applications-internet"),
            )
        ]
