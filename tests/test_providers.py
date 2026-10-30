import tempfile
import unittest
from pathlib import Path

from findr.domain.actions import LaunchApplication, OpenPath, OpenUri, RevealPath
from findr.domain.matching import FuzzyMatcher
from findr.domain.models import ResultKind
from findr.domain.query import Query
from findr.infrastructure.file_index import FileSystemIndex
from findr.providers.applications import AppEntry, ApplicationProvider
from findr.providers.files import FileProvider
from findr.providers.web import WebSearchProvider


class StaticCatalog:
    def __init__(self, *entries: AppEntry) -> None:
        self._entries = entries

    def entries(self):
        return self._entries


class ApplicationProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = ApplicationProvider(
            StaticCatalog(
                AppEntry("firefox.desktop", "Firefox", generic_name="Web Browser", keywords=("internet",)),
                AppEntry("org.gnome.Nautilus.desktop", "Arquivos", executable="nautilus"),
                AppEntry("code.desktop", "Visual Studio Code"),
            ),
            FuzzyMatcher(),
        )

    def titles(self, text: str) -> list[str]:
        results = sorted(self.provider.search(Query.parse(text)), key=lambda r: r.score, reverse=True)
        return [result.title for result in results]

    def test_matches_name_keywords_and_executable(self) -> None:
        self.assertEqual(self.titles("fire"), ["Firefox"])
        self.assertEqual(self.titles("internet"), ["Firefox"])
        self.assertEqual(self.titles("nautilus"), ["Arquivos"])
        self.assertEqual(self.titles("vsc"), ["Visual Studio Code"])

    def test_result_launches_the_application(self) -> None:
        [result] = self.provider.search(Query.parse("firefox"))
        self.assertEqual(result.action, LaunchApplication("firefox.desktop"))
        self.assertEqual(result.kind, ResultKind.APPLICATION)


class FileProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        (self.root / "Projetos" / "relatorio-final").mkdir(parents=True)
        (self.root / "Projetos" / "Relatório anual.pdf").write_text("x")
        (self.root / "node_modules" / "relatorio-lib").mkdir(parents=True)
        (self.root / ".secret-relatorio").write_text("x")
        self.index = FileSystemIndex([str(self.root)], {"node_modules"}, max_depth=5, max_entries=1000)
        self.index.rebuild()
        self.provider = FileProvider(self.index, FuzzyMatcher(), max_results=10, home=self.root)

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_finds_files_and_folders_ignoring_excluded_and_hidden(self) -> None:
        results = {result.title: result for result in self.provider.search(Query.parse("relatorio"))}
        self.assertEqual(set(results), {"relatorio-final", "Relatório anual.pdf"})
        self.assertEqual(results["relatorio-final"].kind, ResultKind.FOLDER)
        self.assertEqual(results["Relatório anual.pdf"].kind, ResultKind.FILE)
        self.assertEqual(results["Relatório anual.pdf"].subtitle, "~/Projetos")

    def test_file_actions_open_and_reveal(self) -> None:
        [result] = self.provider.search(Query.parse("anual"))
        path = str(self.root / "Projetos" / "Relatório anual.pdf")
        self.assertEqual(result.action, OpenPath(path))
        self.assertEqual(result.alternate_action, RevealPath(path))

    def test_single_character_queries_are_skipped(self) -> None:
        self.assertEqual(list(self.provider.search(Query.parse("r"))), [])

    def test_index_respects_entry_limit_keeping_shallow_entries(self) -> None:
        index = FileSystemIndex([str(self.root)], set(), max_depth=5, max_entries=2)
        index.rebuild()
        self.assertEqual(len(index), 2)
        self.assertTrue(all(entry.depth == 0 for entry in index.candidates(())))


class WebSearchProviderTest(unittest.TestCase):
    def test_builds_an_encoded_search_url(self) -> None:
        provider = WebSearchProvider("https://duckduckgo.com/?q={query}")
        [result] = provider.search(Query.parse("café & pão"))
        self.assertEqual(result.action, OpenUri("https://duckduckgo.com/?q=caf%C3%A9+%26+p%C3%A3o"))

    def test_rejects_template_without_placeholder(self) -> None:
        with self.assertRaises(ValueError):
            WebSearchProvider("https://example.com")


if __name__ == "__main__":
    unittest.main()
