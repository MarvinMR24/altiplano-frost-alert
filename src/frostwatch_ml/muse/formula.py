"""Whitelist parser and evaluator for Muse-proposed feature formulas (no eval, no exec).

Grammar: + - * / and parentheses, unary minus, numeric constants, allowlisted feature names and
the functions min(a, b, ...), max(a, b, ...), abs(x), log1p(x), sqrt(x). Anything else (power,
attribute access, subscripts, strings, keywords, lambdas, comparisons, unknown names) is rejected.
"""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd

FUNCS = {"min": (2, 8), "max": (2, 8), "abs": (1, 1), "log1p": (1, 1), "sqrt": (1, 1)}
BINOPS = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide}
MAX_CHARS = 400
MAX_NODES = 80


class FormulaError(ValueError):
    """The formula is outside the restricted grammar or uses a name outside the allowlist."""


def parse(formula: str, names: set[str]) -> ast.Expression:
    if not isinstance(formula, str) or not formula.strip():
        raise FormulaError("empty formula")
    if len(formula) > MAX_CHARS:
        raise FormulaError("formula too long")
    try:
        tree = ast.parse(formula.strip(), mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"syntax error: {exc.msg}") from None
    count = [0]
    _check(tree.body, names, count)
    return tree


def _check(node: ast.AST, names: set[str], count: list[int]) -> None:
    count[0] += 1
    if count[0] > MAX_NODES:
        raise FormulaError("formula too complex")
    if isinstance(node, ast.BinOp):
        if type(node.op) not in BINOPS:
            raise FormulaError(f"operator {type(node.op).__name__} not allowed")
        _check(node.left, names, count)
        _check(node.right, names, count)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, (ast.USub, ast.UAdd)):
            raise FormulaError(f"unary operator {type(node.op).__name__} not allowed")
        _check(node.operand, names, count)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError("only numeric constants are allowed")
    elif isinstance(node, ast.Name):
        if node.id not in names:
            raise FormulaError(f"unknown name {node.id!r}")
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in FUNCS:
            raise FormulaError("function not allowed")
        if node.keywords:
            raise FormulaError("keyword arguments not allowed")
        lo, hi = FUNCS[node.func.id]
        if not lo <= len(node.args) <= hi:
            raise FormulaError(f"{node.func.id} takes {lo} to {hi} arguments")
        for a in node.args:
            if isinstance(a, ast.Starred):
                raise FormulaError("starred arguments not allowed")
            _check(a, names, count)
    else:
        raise FormulaError(f"{type(node).__name__} not allowed")


def names_used(tree: ast.Expression) -> set[str]:
    calls = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and id(n) not in calls}


def evaluate(tree: ast.Expression, df: pd.DataFrame) -> np.ndarray:
    """Element-wise value of a parsed formula over the rows of df (float64; NaN or inf are kept)."""
    with np.errstate(all="ignore"):
        out = _eval(tree.body, df)
        return np.broadcast_to(np.asarray(out, dtype=float), (len(df),)).copy()


def _eval(node: ast.AST, df: pd.DataFrame):
    if isinstance(node, ast.BinOp):
        return BINOPS[type(node.op)](_eval(node.left, df), _eval(node.right, df))
    if isinstance(node, ast.UnaryOp):
        v = _eval(node.operand, df)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return df[node.id].to_numpy(dtype=float)
    if isinstance(node, ast.Call):
        args = [_eval(a, df) for a in node.args]
        f = node.func.id
        if f == "min":
            return np.minimum.reduce(np.broadcast_arrays(*args))
        if f == "max":
            return np.maximum.reduce(np.broadcast_arrays(*args))
        return {"abs": np.abs, "log1p": np.log1p, "sqrt": np.sqrt}[f](args[0])
    raise FormulaError(f"{type(node).__name__} not allowed")  # unreachable after parse
