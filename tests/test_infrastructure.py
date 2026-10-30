import tempfile
import unittest
from pathlib import Path

from findr.infrastructure.settings import Settings, SettingsLoader
from findr.infrastructure.usage_store import JsonUsageRepository


class SettingsLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.path = Path(self._temp.name) / "config.toml"

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_missing_file_gives_defaults(self) -> None:
        self.assertEqual(SettingsLoader(self.path).load(), Settings())

    def test_valid_values_override_and_invalid_ones_are_ignored(self) -> None:
        self.path.write_text(
            'max_results_per_kind = 3\noverlay = false\nfile_roots = ["~/Docs"]\n'
            'max_index_depth = "deep"\nunknown = 1\n',
            encoding="utf-8",
        )
        settings = SettingsLoader(self.path).load()
        self.assertEqual(settings.max_results_per_kind, 3)
        self.assertFalse(settings.overlay)
        self.assertEqual(settings.file_roots, (str(Path.home() / "Docs"),))
        self.assertEqual(settings.max_index_depth, Settings().max_index_depth)

    def test_broken_toml_gives_defaults(self) -> None:
        self.path.write_text("this is = = not toml", encoding="utf-8")
        self.assertEqual(SettingsLoader(self.path).load(), Settings())


class JsonUsageRepositoryTest(unittest.TestCase):
    def test_counts_survive_a_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "usage.json"
            repository = JsonUsageRepository(path)
            repository.record_usage("app:firefox")
            repository.record_usage("app:firefox")
            self.assertEqual(JsonUsageRepository(path).usage_count("app:firefox"), 2)

    def test_corrupt_file_starts_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(JsonUsageRepository(path).usage_count("x"), 0)


if __name__ == "__main__":
    unittest.main()
