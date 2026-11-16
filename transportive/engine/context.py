"""engine/context.py: rules per context, failing closed."""
from itertools import product

from ..spec.language import COORDS


def contexts():
    return [dict(zip(COORDS, values)) for values in product(*COORDS.values())]


def covers(when, ctx):
    return all(ctx.get(k) == v for k, v in when.items())


def resolve(spec, ctx):
    """(decision, rules, why)."""
    unknown = [f"{k}={v}" for k, v in ctx.items() if k in COORDS and v not in COORDS[k]]
    cases = [c for c in spec.cases if covers(c["when"], ctx)]
    if unknown or not cases:                                         # the door stays shut
        return spec.resolution.get("no_match", "reject"), [], f"no case covers {unknown or ctx}"
    # the most specific cases win, a tie asks
    depth = max(len(c["when"]) for c in cases)
    top = [c for c in cases if len(c["when"]) == depth]
    if len({repr(sorted(c["rules"].items())) for c in top}) > 1:
        return spec.resolution.get("ambiguous", "clarify"), [], f"cases {[c['name'] for c in top]} tie and disagree"
    beaten = {c["name"] for c in cases} - {top[0]["name"]}          # a less specific case's own rules do not apply
    rules = [r for r in spec.rules if covers(r.when, ctx) and r.id.split(".")[0] not in beaten]
    banned = {r.expr for r in rules if r.effect == "forbid"}
    return "go", [r for r in rules if not (r.effect == "permit" and r.expr in banned)], top[0]["name"]
