import unittest

from findr.domain.actions import CopyText
from findr.domain.query import Query
from findr.providers.calculator import CalculatorProvider, SafeExpressionEvaluator


class SafeExpressionEvaluatorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.evaluator = SafeExpressionEvaluator()

    def test_arithmetic_and_precedence(self) -> None:
        self.assertEqual(self.evaluator.evaluate("2 + 3 * 4"), 14)
        self.assertEqual(self.evaluator.evaluate("(2 + 3) * 4"), 20)
        self.assertEqual(self.evaluator.evaluate("-2 ** 2"), -4)
        self.assertEqual(self.evaluator.evaluate("7 // 2"), 3)

    def test_functions_and_constants(self) -> None:
        self.assertEqual(self.evaluator.evaluate("sqrt(16)"), 4)
        self.assertAlmostEqual(self.evaluator.evaluate("2 * pi"), 6.283185307, places=6)

    def test_rejects_anything_that_is_not_arithmetic(self) -> None:
        for expression in ("__import__('os')", "open('x')", "[1, 2]", "True + 1", "x + 1", "1 if 1 else 2"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.evaluator.evaluate(expression)

    def test_errors_become_value_errors(self) -> None:
        for expression in ("1/0", "2 ** 99999", "1 +"):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                self.evaluator.evaluate(expression)


class CalculatorProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = CalculatorProvider()

    def results(self, text: str):
        return list(self.provider.search(Query.parse(text)))

    def test_shows_result_and_copies_it(self) -> None:
        [result] = self.results("12 * (3 + 1)")
        self.assertEqual(result.title, "= 48")
        self.assertEqual(result.action, CopyText("48"))

    def test_accepts_decimal_comma_and_caret_power(self) -> None:
        self.assertEqual(self.results("2,5 * 2")[0].title, "= 5")
        self.assertEqual(self.results("2^10")[0].title, "= 1024")

    def test_ignores_plain_text_and_lone_numbers(self) -> None:
        self.assertEqual(self.results("firefox"), [])
        self.assertEqual(self.results("2024"), [])
        self.assertEqual(self.results("node-2"), [])

    def test_number_formatting(self) -> None:
        self.assertEqual(CalculatorProvider.format_number(10.0), "10")
        self.assertEqual(CalculatorProvider.format_number(1 / 3), "0.3333333333")


if __name__ == "__main__":
    unittest.main()
