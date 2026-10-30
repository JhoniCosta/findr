"""Inline calculator: typing ``2*(3+4)`` shows ``= 14`` as the first result."""

import ast
import math
import operator
import re
from collections.abc import Callable, Iterable

from findr.domain.actions import CopyText
from findr.domain.icons import themed_icon
from findr.domain.models import ResultKind, SearchResult
from findr.domain.ports import SearchProvider
from findr.domain.query import Query

Number = int | float


class SafeExpressionEvaluator:
    """Evaluates arithmetic by walking the AST (never ``eval``), allowing only whitelisted nodes."""

    MAX_EXPONENT = 10_000

    _BINARY_OPERATORS: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    _UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Number], Number]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }
    _FUNCTIONS: dict[str, Callable[..., Number]] = {
        "sqrt": math.sqrt, "abs": abs, "round": round, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "asin": math.asin, "acos": math.acos, "atan": math.atan, "floor": math.floor,
        "ceil": math.ceil, "factorial": math.factorial, "min": min, "max": max,
    }
    _CONSTANTS: dict[str, Number] = {"pi": math.pi, "e": math.e, "tau": math.tau}

    def evaluate(self, expression: str) -> Number:
        try:
            tree = ast.parse(expression, mode="eval")
            return self._eval(tree.body)
        except (SyntaxError, TypeError, ZeroDivisionError, OverflowError, RecursionError) as error:
            raise ValueError(f"invalid expression: {expression!r}") from error

    def _eval(self, node: ast.AST) -> Number:
        match node:
            case ast.Constant(value=bool()):
                raise ValueError("booleans are not numbers here")
            case ast.Constant(value=int() | float() as value):
                return value
            case ast.Name(id=name) if name in self._CONSTANTS:
                return self._CONSTANTS[name]
            case ast.UnaryOp(op=op, operand=operand) if type(op) in self._UNARY_OPERATORS:
                return self._UNARY_OPERATORS[type(op)](self._eval(operand))
            case ast.BinOp(left=left, op=op, right=right) if type(op) in self._BINARY_OPERATORS:
                lhs, rhs = self._eval(left), self._eval(right)
                if isinstance(op, ast.Pow) and abs(rhs) > self.MAX_EXPONENT:
                    raise ValueError("exponent too large")
                return self._BINARY_OPERATORS[type(op)](lhs, rhs)
            case ast.Call(func=ast.Name(id=name), args=args, keywords=[]) if name in self._FUNCTIONS:
                return self._FUNCTIONS[name](*(self._eval(arg) for arg in args))
        raise ValueError(f"unsupported syntax: {ast.dump(node)}")


class CalculatorProvider(SearchProvider):
    name = "calculator"
    SCORE = 1.5  # A valid expression is almost certainly what the user wants.

    _LOOKS_LIKE_MATH = re.compile(r"^[\d\s.,+\-*/%^()a-z]+$")
    _HAS_OPERATION = re.compile(r"\d\s*[-+*/%^]|[a-z]+\s*\(|^\s*-?\s*(pi|e|tau)\b")

    def __init__(self, evaluator: SafeExpressionEvaluator | None = None) -> None:
        self._evaluator = evaluator or SafeExpressionEvaluator()

    def search(self, query: Query) -> Iterable[SearchResult]:
        expression = self._to_python_syntax(query.raw.lower())
        if not self._is_candidate(expression):
            return []
        try:
            value = self._evaluator.evaluate(expression)
        except ValueError:
            return []

        formatted = self.format_number(value)
        return [
            SearchResult(
                id=f"calculator:{query.raw}",
                title=f"= {formatted}",
                subtitle=f"{query.raw}  ·  Enter copia o resultado",
                kind=ResultKind.CALCULATION,
                score=self.SCORE,
                action=CopyText(formatted),
                icon=themed_icon("accessories-calculator", "org.gnome.Calculator"),
            )
        ]

    @staticmethod
    def format_number(value: Number) -> str:
        if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            value = int(value)
        return str(value) if isinstance(value, int) else f"{value:.10g}"

    @staticmethod
    def _to_python_syntax(text: str) -> str:
        # Accept the usual Brazilian decimal comma and "^" for power.
        return text.replace(",", ".").replace("^", "**").replace("×", "*").replace("÷", "/")

    def _is_candidate(self, expression: str) -> bool:
        return bool(self._LOOKS_LIKE_MATH.match(expression) and self._HAS_OPERATION.search(expression))
