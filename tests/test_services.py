import unittest

from findr.domain.actions import CopyText, OpenPath, RevealPath
from findr.domain.models import ResultKind
from findr.services.grouping import ResultGrouper
from findr.services.ranking import UsageAwareRanking
from findr.services.search_engine import SearchEngine
from tests.fakes import FailingProvider, InMemoryUsage, RecordingDesktop, StaticProvider, make_result


class RankingTest(unittest.TestCase):
    def test_frequently_used_results_climb(self) -> None:
        ranking = UsageAwareRanking(InMemoryUsage({"b": 20}))
        ranked = ranking.rank([make_result("a", 0.8), make_result("b", 0.7)])
        self.assertEqual([result.id for result in ranked], ["b", "a"])

    def test_boost_is_bounded(self) -> None:
        ranking = UsageAwareRanking(InMemoryUsage({"b": 10_000}))
        [result] = ranking.rank([make_result("b", 0.5)])
        self.assertAlmostEqual(result.score, 0.5 + UsageAwareRanking.MAX_BOOST)


class GrouperTest(unittest.TestCase):
    def test_top_hit_then_sections_in_rank_order_with_caps(self) -> None:
        ranked = [
            make_result("app1", 0.9),
            make_result("doc1", 0.8, ResultKind.FILE),
            make_result("app2", 0.7),
            make_result("app3", 0.6),
            make_result("app4", 0.5),
            make_result("web", 0.01, ResultKind.WEB),
        ]
        groups = ResultGrouper(max_per_kind=2).group(ranked)
        self.assertTrue(groups[0].is_top_hit)
        self.assertEqual([r.id for r in groups[0].results], ["app1"])
        self.assertEqual([(g.kind, [r.id for r in g.results]) for g in groups[1:]], [
            (ResultKind.FILE, ["doc1"]),
            (ResultKind.APPLICATION, ["app2", "app3"]),
            (ResultKind.WEB, ["web"]),
        ])

    def test_web_fallback_is_never_the_top_hit(self) -> None:
        groups = ResultGrouper(max_per_kind=3).group([make_result("web", 0.01, ResultKind.WEB)])
        self.assertEqual([g.kind for g in groups], [ResultKind.WEB])


class SearchEngineTest(unittest.TestCase):
    def engine(self, *providers):
        return SearchEngine(providers, UsageAwareRanking(InMemoryUsage()), ResultGrouper(max_per_kind=5))

    def test_failing_provider_does_not_break_the_search(self) -> None:
        with self.assertLogs("findr.services.search_engine", level="ERROR"):
            groups = self.engine(FailingProvider(), StaticProvider([make_result("a", 0.5)])).search("a")
        self.assertEqual([r.id for g in groups for r in g.results], ["a"])

    def test_duplicates_keep_the_best_score(self) -> None:
        engine = self.engine(StaticProvider([make_result("a", 0.2)]), StaticProvider([make_result("a", 0.9)]))
        [top] = engine.search("a")
        self.assertEqual(top.results[0].score, 0.9)

    def test_blank_query_returns_nothing(self) -> None:
        self.assertEqual(self.engine(StaticProvider([make_result("a", 1)])).search("  "), [])


class ActionsTest(unittest.TestCase):
    def test_actions_delegate_to_the_desktop_port(self) -> None:
        desktop = RecordingDesktop()
        OpenPath("/tmp/a b.txt").execute(desktop)
        RevealPath("/tmp/a").execute(desktop)
        CopyText("42").execute(desktop)
        self.assertEqual(desktop.calls, [("open", "file:///tmp/a%20b.txt"), ("reveal", "/tmp/a"), ("copy", "42")])


if __name__ == "__main__":
    unittest.main()
