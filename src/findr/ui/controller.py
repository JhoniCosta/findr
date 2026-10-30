import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Protocol

from gi.repository import GLib

from findr.domain.actions import DesktopPort
from findr.domain.models import ResultGroup, SearchResult
from findr.domain.ports import UsageRepository
from findr.services.search_engine import SearchEngine

logger = logging.getLogger(__name__)


class LauncherView(Protocol):
    def show_results(self, groups: list[ResultGroup]) -> None: ...

    def dismiss(self) -> None: ...


class SearchController:
    """Presenter: debounces keystrokes, searches off the UI thread and runs result actions.

    Every dispatched search gets a generation number; answers that arrive
    after a newer query was typed are discarded, so results never "flicker
    back" to an older query.
    """

    DEBOUNCE_MS = 60

    def __init__(self, engine: SearchEngine, desktop: DesktopPort, usage: UsageRepository) -> None:
        self._engine = engine
        self._desktop = desktop
        self._usage = usage
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="findr-search")
        self._view: LauncherView | None = None
        self._generation = 0
        self._pending_source: int | None = None

    def attach(self, view: LauncherView) -> None:
        self._view = view

    def query_changed(self, text: str) -> None:
        self._cancel_pending()
        self._generation += 1
        if not text.strip():
            self._show([])
            return
        generation = self._generation
        self._pending_source = GLib.timeout_add(self.DEBOUNCE_MS, self._dispatch, text, generation)

    def activate(self, result: SearchResult, alternate: bool = False) -> None:
        action = result.alternate_action if alternate and result.alternate_action else result.action
        try:
            action.execute(self._desktop)
        except Exception:
            logger.exception("could not run %r for %r", action, result.title)
            return
        self._usage.record_usage(result.id)
        if self._view:
            self._view.dismiss()

    def shutdown(self) -> None:
        self._cancel_pending()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _dispatch(self, text: str, generation: int) -> bool:
        self._pending_source = None
        future = self._executor.submit(self._engine.search, text)
        future.add_done_callback(lambda done: GLib.idle_add(self._deliver, done, generation))
        return GLib.SOURCE_REMOVE

    def _deliver(self, future: Future, generation: int) -> bool:
        if generation == self._generation:
            try:
                self._show(future.result())
            except Exception:
                logger.exception("search failed")
        return GLib.SOURCE_REMOVE

    def _show(self, groups: list[ResultGroup]) -> None:
        if self._view:
            self._view.show_results(groups)

    def _cancel_pending(self) -> None:
        if self._pending_source is not None:
            GLib.source_remove(self._pending_source)
            self._pending_source = None
