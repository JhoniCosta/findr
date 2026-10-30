import unittest

from findr.domain.matching import FuzzyMatcher
from findr.domain.query import Query


class FuzzyMatcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.matcher = FuzzyMatcher()

    def score(self, query: str, text: str) -> float:
        return self.matcher.score(Query.parse(query), text)

    def test_tiers_are_ordered_exact_prefix_word_substring(self) -> None:
        exact = self.score("files", "Files")
        prefix = self.score("fir", "Firefox")
        word_prefix = self.score("code", "Visual Studio Code")
        substring = self.score("efo", "Firefox")
        self.assertEqual(exact, 1.0)
        self.assertGreater(exact, prefix)
        self.assertGreater(prefix, word_prefix)
        self.assertGreater(word_prefix, substring)
        self.assertGreater(substring, 0)

    def test_matching_ignores_case_and_accents(self) -> None:
        self.assertGreater(self.score("configuracoes", "Configurações"), 0.9)

    def test_acronym_matches_word_initials(self) -> None:
        self.assertEqual(self.score("vsc", "Visual Studio Code"), FuzzyMatcher.ACRONYM)

    def test_subsequence_is_a_weak_match(self) -> None:
        fuzzy = self.score("frfx", "Firefox")
        self.assertGreater(fuzzy, 0)
        self.assertLess(fuzzy, FuzzyMatcher.SUBSTRING)

    def test_scattered_subsequence_does_not_match(self) -> None:
        self.assertEqual(self.score("abz", "a long name without the z... ok zzz"), 0)

    def test_multi_token_requires_every_token(self) -> None:
        self.assertGreater(self.score("studio code", "Visual Studio Code"), 0)
        self.assertGreater(self.score("code visual", "Visual Studio Code"), 0)
        self.assertEqual(self.score("code banana", "Visual Studio Code"), 0)

    def test_empty_query_never_matches(self) -> None:
        self.assertEqual(self.score("   ", "anything"), 0)

    def test_best_score_applies_field_weights(self) -> None:
        query = Query.parse("browser")
        score = self.matcher.best_score(query, [("Firefox", 1.0), ("Web Browser", 0.5), (None, 1.0)])
        self.assertAlmostEqual(score, self.matcher.score(query, "Web Browser") * 0.5)


if __name__ == "__main__":
    unittest.main()
