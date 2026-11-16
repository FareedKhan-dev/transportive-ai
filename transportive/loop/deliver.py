"""loop/deliver.py: inspect, specify, generate, verify, receipt."""
import hashlib
import subprocess

from ..config import BUDGET, CODER
from ..engine import context, solver
from ..index import semantic
from ..spec.language import Rule
from ..verify import rings
from ..workspace import sandbox
from .journal import Journal


def receipt(ticket, tree, rules, report, rounds, ledger):
    def git(*args):
        return subprocess.run(["git", "-C", tree, *args], capture_output=True, text=True).stdout
    changed, patch = git("diff", "--name-only").split(), git("diff")
    digest = hashlib.sha256(patch.encode()).hexdigest()[:12]
    for r in rules if report["ok"] else []:
        for f in changed:
            ledger.record(r.id, ticket["context"], f, ticket["id"], digest)
    return {"ticket": ticket["id"], "status": "accepted" if report["ok"] else "red", "rounds": rounds,
            "rules": [r.id for r in rules], "patch_sha256": digest, "patch": patch,
            "effects": {f: semantic.effects(f"{tree}/{f}") for f in changed if f.endswith(".py")}}


def deliver(ticket, spec, team, ledger, ring_set=(1, 2, 3, 4)):
    """A person reads the receipt for ring 5."""
    j, room = Journal(f"results/journal/{CODER}/{spec.version}/{ticket['id']}.jsonl"), ticket["id"]
    tree = j.once("inspect", lambda: str(sandbox.up(room)))
    decision, rules, why = context.resolve(spec, ticket["context"])
    # demands go to the solver with the rules
    asks = [Rule(f"ticket.{k}", "bound", {}, e) for k, e in enumerate(ticket.get("demands", []))]
    core = j.once(f"specify.{spec.version}", lambda: solver.conflict(rules + asks))
    free = solver.gaps(rules + asks, ticket.get("outputs", []))
    if decision != "go" or core or free:                                    # fail closed: reject or ask
        return {"ticket": room, "status": "reject" if core else "clarify" if free else decision, "why": why,
                "core": core, "free": free}
    pack = "\n".join(f"- {r.id}: {r.effect} {r.expr} ({r.source})" for r in rules)
    for n in range(BUDGET["repair_rounds"] + 1):
        j.once(f"generate.{n}", lambda: team(ticket, pack, room, tree))
        report = j.once(f"verify.{n}", lambda: vars(rings.verify(room, tree, rules, ring_set)))
        if report["ok"]:
            break
        pack += f"\nRing {report['ring']} failed, fix this first: {report['why']}"   # back to the coder
    return j.once("receipt", lambda: receipt(ticket, tree, rules, report, n + 1, ledger))
