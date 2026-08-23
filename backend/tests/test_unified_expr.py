"""Tests for the $ expression compiler — safe, restricted, no Any."""

from __future__ import annotations

import pytest

from aps.unified._expr import compile_expr


class TestCompileExpr:
    def test_simple_arithmetic(self) -> None:
        fn = compile_expr("$x + 1", frozenset({"x"}))
        assert fn(x=2) == 3

    def test_subtraction(self) -> None:
        fn = compile_expr("$x - $y", frozenset({"x", "y"}))
        assert fn(x=10, y=3) == 7

    def test_multiplication(self) -> None:
        fn = compile_expr("$x * $y", frozenset({"x", "y"}))
        assert fn(x=4, y=3) == 12

    def test_division(self) -> None:
        fn = compile_expr("$x / $y", frozenset({"x", "y"}))
        assert fn(x=10, y=2) == 5

    def test_field_access(self) -> None:
        fn = compile_expr("$x.expiry", frozenset({"x"}))
        assert fn(x={"expiry": 42}) == 42

    def test_min_function(self) -> None:
        fn = compile_expr("min($a, $b)", frozenset({"a", "b"}))
        assert fn(a=5, b=10) == 5

    def test_max_function(self) -> None:
        fn = compile_expr("max($a, $b)", frozenset({"a", "b"}))
        assert fn(a=5, b=10) == 10

    def test_ceil_function(self) -> None:
        fn = compile_expr("ceil($x)", frozenset({"x"}))
        assert fn(x=3.2) == 4

    def test_floor_function(self) -> None:
        fn = compile_expr("floor($x)", frozenset({"x"}))
        assert fn(x=3.8) == 3

    def test_abs_function(self) -> None:
        fn = compile_expr("abs($x)", frozenset({"x"}))
        assert fn(x=-5) == 5

    def test_self_reference(self) -> None:
        fn = compile_expr("$this.max_lifetime", frozenset())
        assert fn(this={"max_lifetime": 100}) == 100

    def test_now_reference(self) -> None:
        fn = compile_expr("$now", frozenset())
        assert fn(now_ts=1234567890) == 1234567890

    def test_min_with_field_access(self) -> None:
        fn = compile_expr("min($top.expiry, $bottom.expiry)", frozenset({"top", "bottom"}))
        result = fn(top={"expiry": 100}, bottom={"expiry": 200})
        assert result == 100

    def test_expression_with_literals(self) -> None:
        fn = compile_expr("$x + 10", frozenset({"x"}))
        assert fn(x=5) == 15

    def test_comparison_eq(self) -> None:
        fn = compile_expr("$x = $y", frozenset({"x", "y"}))
        assert fn(x=5, y=5) is True
        assert fn(x=5, y=3) is False

    def test_comparison_ne(self) -> None:
        fn = compile_expr("$x != $y", frozenset({"x", "y"}))
        assert fn(x=5, y=3) is True
        assert fn(x=5, y=5) is False

    def test_comparison_lt(self) -> None:
        fn = compile_expr("$x < $y", frozenset({"x", "y"}))
        assert fn(x=3, y=5) is True
        assert fn(x=5, y=3) is False

    def test_comparison_gt(self) -> None:
        fn = compile_expr("$x > $y", frozenset({"x", "y"}))
        assert fn(x=5, y=3) is True
        assert fn(x=3, y=5) is False

    def test_comparison_le(self) -> None:
        fn = compile_expr("$x <= $y", frozenset({"x", "y"}))
        assert fn(x=5, y=5) is True
        assert fn(x=6, y=5) is False

    def test_comparison_ge(self) -> None:
        fn = compile_expr("$x >= $y", frozenset({"x", "y"}))
        assert fn(x=5, y=5) is True
        assert fn(x=4, y=5) is False

    def test_logic_and(self) -> None:
        fn = compile_expr("$x and $y", frozenset({"x", "y"}))
        assert fn(x=True, y=True) is True
        assert fn(x=True, y=False) is False

    def test_logic_or(self) -> None:
        fn = compile_expr("$x or $y", frozenset({"x", "y"}))
        assert fn(x=False, y=True) is True
        assert fn(x=False, y=False) is False

    def test_logic_not(self) -> None:
        fn = compile_expr("not $x", frozenset({"x"}))
        assert fn(x=False) is True
        assert fn(x=True) is False

    def test_rejects_import(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            compile_expr("__import__('os')", frozenset())

    def test_rejects_open(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            compile_expr("open('/etc/passwd')", frozenset())

    def test_rejects_eval(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            compile_expr("eval('1+1')", frozenset())

    def test_rejects_exec(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            compile_expr("exec('x=1')", frozenset())

    def test_rejects_getattr(self) -> None:
        with pytest.raises(ValueError, match="forbidden"):
            compile_expr("getattr(x, 'y')", frozenset({"x"}))

    def test_unknown_bound_name_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown"):
            compile_expr("$unknown + 1", frozenset({"x"}))

    def test_caching_returns_same_function(self) -> None:
        fn1 = compile_expr("$x + 1", frozenset({"x"}))
        fn2 = compile_expr("$x + 1", frozenset({"x"}))
        assert fn1 is fn2

    def test_different_names_give_different_functions(self) -> None:
        fn1 = compile_expr("$x + 1", frozenset({"x"}))
        fn2 = compile_expr("$x + 1", frozenset({"x", "y"}))
        assert fn1 is not fn2

    def test_start_and_end_references(self) -> None:
        fn = compile_expr("$end - $start", frozenset())
        assert fn(start=100, end=200) == 100
