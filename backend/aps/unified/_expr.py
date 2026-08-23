"""$ expression compiler — safe, restricted, cached.

The $ expression DSL is trivially convertible to safe Python lambdas.
No custom parser needed — just regex substitution + compile() in eval mode.

Safety comes from the restricted eval namespace, not from pattern matching.
The _SAFE_BUILTINS dict is the security boundary: only min, max, ceil, floor,
abs, int, float, bool, str, and constants are available.
"""

from __future__ import annotations

import re
from math import ceil, floor
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable

# ── Forbidden patterns ─────────────────────────────────────────────────────

# Only block constructs that could escape the restricted eval namespace.
# The restricted __builtins__ handles the rest — you can't call open(),
# __import__(), etc. even if the code references them, because those
# names aren't in the namespace.
_FORBIDDEN = (
    r"__\w+__",  # dunder names (can't be in the namespace, but block explicitly)
    r"\beval\b",
    r"\bexec\b",
    r"\bcompile\b",
    r"\bgetattr\b",
    r"\bsetattr\b",
    r"\bdelattr\b",
    r"\bhasattr\b",
    r"\bglobals\b",
    r"\blocals\b",
    r"\bvars\b",
    r"\bdir\b",
    r"\btype\b",
    r"\bopen\b",
    r"\b__import__\b",
    r"\binput\b",
    r"\bbreakpoint\b",
    r"\bprint\b",
    r"\bhelp\b",
    r"\bcredit\b",
    r"\blicense\b",
    r"\bcopyright\b",
)

# ── Safe builtins ──────────────────────────────────────────────────────────

_SAFE_BUILTINS: dict[str, object] = {
    "min": min,
    "max": max,
    "ceil": ceil,
    "floor": floor,
    "abs": abs,
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
    "True": True,
    "False": False,
    "None": None,
}

# ── $var pattern ───────────────────────────────────────────────────────────

# Matches $identifier or $identifier.field
_DOLLAR_RE = re.compile(r"\$([a-zA-Z_]\w*)(?:\.([a-zA-Z_]\w*))?")

# Reserved names that don't need to be in bound_names.
# These are the Python parameter names, not the $ names.
# $now → now_ts, $this → this, $start → start, $end → end
_RESERVED_NAMES = frozenset({"now_ts", "this", "start", "end"})


def _check_forbidden(expr: str) -> None:
    """Check the original expression for forbidden constructs."""
    for pattern in _FORBIDDEN:
        if re.search(pattern, expr):
            raise ValueError(
                f"forbidden construct in expression: {pattern!r} matched in {expr!r}"
            )


def _transform_dsl(expr: str, bound_names: frozenset[str]) -> str:
    """Transform the DSL expression to valid Python.

    $name           → name       (when name in bound_names or reserved)
    $name.field     → name["field"]
    $now            → now_ts
    $this           → this
    $this.field     → this["field"]
    $start          → start
    $end            → end
    =               → ==        (DSL equality, but not ! =)
    and             → and       (passthrough)
    or              → or        (passthrough)
    not             → not       (passthrough)
    """
    # Step 1: protect multi-char operators from being mangled by = → ==
    expr = expr.replace("!=", "\x00NE\x00")
    expr = expr.replace("<=", "\x00LE\x00")
    expr = expr.replace(">=", "\x00GE\x00")

    # Step 2: replace DSL = with Python ==
    expr = expr.replace("=", "==")

    # Step 3: restore multi-char operators
    expr = expr.replace("\x00NE\x00", "!=")
    expr = expr.replace("\x00LE\x00", "<=")
    expr = expr.replace("\x00GE\x00", ">=")

    # Step 4: transform $references
    all_names = bound_names | _RESERVED_NAMES

    def _replace(m: re.Match[str]) -> str:
        name = m.group(1)
        field = m.group(2)

        if name == "now":
            return "now_ts"
        if name not in all_names:
            raise ValueError(
                f"unknown name ${name} in expression {expr!r}; "
                f"bound names: {sorted(bound_names)}"
            )
        if field:
            return f'{name}["{field}"]'
        return name

    return _DOLLAR_RE.sub(_replace, expr)


# ── Cache ──────────────────────────────────────────────────────────────────

_CACHE: dict[tuple[str, str], Callable[..., int | float | bool]] = {}


def compile_expr(
    expr: str, bound_names: frozenset[str],
) -> Callable[..., int | float | bool]:
    """Compile a $expression to a safe Python lambda.

    Args:
        expr: The $expression, e.g. ``"min($top.expiry, $bottom.expiry)"``
        bound_names: Names available for binding, e.g. ``{"top", "bottom"}``

    Returns:
        A callable taking keyword arguments matching bound_names (plus
        ``this``, ``start``, ``end``, ``now_ts`` as needed) and returning
        the evaluated result.

    Raises:
        ValueError: if the expression contains forbidden constructs or
            references an unknown name.
    """
    names_key = "\x00".join(sorted(bound_names))
    cache_key = (expr, names_key)
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached

    # Validate
    _check_forbidden(expr)

    # Transform DSL syntax to valid Python
    transformed = _transform_dsl(expr, bound_names)

    # Build the lambda wrapper — only include params actually used
    all_param_names = sorted(bound_names | _RESERVED_NAMES)
    used_names: set[str] = set()
    for name in all_param_names:
        # Check if name appears as a standalone word in the transformed expression
        if re.search(rf"\b{re.escape(name)}\b", transformed):
            used_names.add(name)

    param_list = ", ".join(sorted(used_names)) if used_names else ""
    # If no params used, create a no-arg lambda
    if not param_list:
        wrapper_code = compile(f"lambda: {transformed}", "<$expr-wrapper>", "eval")
    else:
        wrapper_code = compile(
            f"lambda {param_list}: {transformed}", "<$expr-wrapper>", "eval"
        )

    # Evaluate in restricted namespace — this is the security boundary.
    # eval() returns a plain object, but we know the DSL only produces
    # int, float, or bool values. The cast is safe.
    fn = cast(
        "Callable[..., int | float | bool]",
        eval(wrapper_code, {"__builtins__": _SAFE_BUILTINS}),
    )

    _CACHE[cache_key] = fn
    return fn
