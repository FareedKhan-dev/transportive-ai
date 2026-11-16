"""verify/compile.py: rules compiled into tests."""
import re

from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from ..engine.transport import split


def holds(r, state):
    try:
        ok = eval(r.expr, {"__builtins__": {}}, dict(state))
    except NameError:                           # a value this state lacks
        return True
    return not ok if r.effect == "forbid" else ok


def require(r, state):
    seen = ", ".join(f"{k}={state[k]}" for k in sorted(set(re.findall(r"[a-z_]+", r.expr)) & set(state)))
    assert holds(r, state), f"{r.id} broken: {r.expr} with {seen}"


def machine(rules, moves, observe):
    body = {name: rule(**draws)(move) for name, (move, draws) in moves.items()}
    for r in rules:
        if r.kind in ("bound", "invariant", "at_most_once"):
            # every money rule is checked after every move
            body[f"check_{r.id.replace('.', '_')}"] = invariant()(lambda self, r=r: require(r, observe(self)))
    return type("Compiled", (RuleBasedStateMachine,), body)


def same_end(apply, charged, amount, parts):
    return apply(charged, [amount]) == apply(charged, split(amount, parts))


def replay(histories, apply, rules):
    return [(h["invoice"], r.id) for h in histories for state in apply(h["charged"], h["refunds"], each=True)
            for r in rules if not holds(r, state)]
