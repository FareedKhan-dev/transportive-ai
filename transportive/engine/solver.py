"""engine/solver.py: rules as Z3 formulas."""
import ast
import operator

import z3

from ..spec.language import STATE

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
       ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge, ast.Eq: operator.eq,
       ast.NotEq: operator.ne}
SORTS = {"real": z3.Real, "int": z3.Int, "bool": z3.Bool}


def variables():
    return {name: SORTS[sort](name) for name, sort in STATE.items()}


def formula(expr, V):
    def go(n):
        if isinstance(n, ast.Name):
            return V[n.id]
        if isinstance(n, ast.Constant):
            return z3.BoolVal(n.value) if isinstance(n.value, bool) else z3.RealVal(n.value)
        if isinstance(n, ast.BinOp):
            return OPS[type(n.op)](go(n.left), go(n.right))
        if isinstance(n, ast.Compare) and len(n.ops) == 1:
            return OPS[type(n.ops[0])](go(n.left), go(n.comparators[0]))
        if isinstance(n, ast.BoolOp):
            return (z3.And if isinstance(n.op, ast.And) else z3.Or)(*map(go, n.values))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
            return z3.Not(go(n.operand))
        raise ValueError(f"not in the rule language: {ast.unparse(n)}")   # anything else is refused
    return go(ast.parse(expr, mode="eval").body)


def obligation(rule, V):
    """The formula, its negation for forbid, nothing for permit."""
    f = formula(rule.expr, V)
    return z3.Not(f) if rule.effect == "forbid" else z3.BoolVal(True) if rule.effect == "permit" else f


def conflict(rules):
    V, s = variables(), z3.Solver()
    s.set("core.minimize", True)
    for r in rules:
        s.assert_and_track(obligation(r, V), z3.Bool(r.id))          # tracked by id, so the core names rules
    return sorted(str(c) for c in s.unsat_core()) if s.check() == z3.unsat else []   # unsat: no state fits them all


def gaps(rules, outputs):
    # an output no rule names is a guess
    named = {n.id for r in rules for n in ast.walk(ast.parse(r.expr, mode="eval")) if isinstance(n, ast.Name)}
    return [o for o in outputs if o not in named]


def changed(old, new):
    # a state one version accepts and the other refuses
    V, s = variables(), z3.Solver()
    s.add(z3.And(*[obligation(r, V) for r in old], True) != z3.And(*[obligation(r, V) for r in new], True))
    return s.model() if s.check() == z3.sat else None
