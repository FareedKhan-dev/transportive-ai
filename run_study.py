"""run_study.py: the study the post's harness section describes. Every arm, both coders, every sealed ticket.

Each attempt runs in its own room, and its record has the fields results/derive.py reads: shipped, hidden_pass,
violation, commits, asked, conflict_flagged, wall_min, credits, refusals, repair_rounds. The hidden oracle runs the
shipped patch in a fresh room at the pin, so nothing the coder left behind can change the verdict.

    CODER=opus python run_study.py        then CODER=qwen, then fold results/story.jsonl into results/story.json
"""
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

from transportive.agents import team
from transportive.agents.coder import TOOLS, code
from transportive.config import BUDGET, CODER
from transportive.coord.leases import Leases
from transportive.engine import context, solver
from transportive.eval import harness, suite
from transportive.ledger.trace import Ledger
from transportive.loop.deliver import deliver
from transportive.spec.canon import canon, prose
from transportive.spec.language import Rule
from transportive.verify import rings
from transportive.workspace import sandbox

SPEC = canon(yaml.safe_load(Path("assets/specs/payment.refund.yaml").read_text(encoding="utf-8")))
PLAIN = Path("assets/prompts/plain.md").read_text(encoding="utf-8")
VERDICTS = {}   # (ticket, patch sha1) -> the rule class the hidden oracle reported broken
CLASS_OF = {"duplicate_transfer": ("requested <= 1", "at_most_once"), "over_refund": ("refunded <= charged",),
            "rounding_drift": ("minor_units",), "wrong_method": ("same_means",), "refund_in_dispute": ("disputed",),
            "deadline_breach": ("days <=",), "lost_update": ("charge_events", "allocations")}


def meter(ticket):
    return {"ticket": ticket["id"], "credits": 0.0, "cap": BUDGET["credits"], "refusals": 0, "log": []}


def pack(ticket, arm):
    """What the coder is told: a plain prompt, the spec as prose (A2), or the rule pack of the ticket's context."""
    if arm["pack"] == "plain":
        return PLAIN
    if arm["pack"] == "agents_md":
        return PLAIN + "\n# AGENTS.md\n" + prose(SPEC)
    rules = context.resolve(SPEC, ticket["context"])[1]
    return PLAIN + "\n# Rules for this ticket\n" + "\n".join(f"- {r.id}: {r.effect} {r.expr} ({r.source})" for r in rules)


def commits(tree):
    out = subprocess.run(["git", "-C", str(tree), "rev-list", "--count", "HEAD", "^" + sandbox.SALEOR_PIN],
                         capture_output=True, text=True).stdout.strip()
    return int(out or 0) or 1


def gate(ticket):
    """The same gate as loop/deliver.py: a core with the ticket's demands rejects, a free output asks."""
    decision, rules, why = context.resolve(SPEC, ticket["context"])
    asks = [Rule(f"ticket.{k}", "bound", {}, e) for k, e in enumerate(ticket.get("demands", []))]
    core, free = solver.conflict(rules + asks), solver.gaps(rules + asks, ticket.get("outputs", []))
    return decision, rules, bool(core), bool(free) or decision == "clarify"


def answered(ticket):
    """The ticket after the owner's sealed answer: the question settled, a rejected demand dropped."""
    a = yaml.safe_load(Path(f"assets/decisions/tickets/{ticket['id']}.yaml").read_text(encoding="utf-8"))
    return {**ticket, "text": ticket["text"] + "\nOwner's answer: " + a["answer"], "demands": [], "outputs": []}


def attempt(ticket, arm, coder):
    """One ticket under one arm. Only the gated arms stop to ask, and the sealed answer lets them go on."""
    start, m, room = time.monotonic(), meter(ticket), f"{ticket['id']}.{coder}.{arm['pack']}"
    decision, rules, flagged, asked = gate(ticket)
    rec = {"asked": arm["gate"] and asked, "conflict_flagged": arm["gate"] and flagged, "repair_rounds": 0,
           "patch": "", "shipped": False}
    if arm["gate"] and (asked or flagged):
        ticket = answered(ticket)
    if arm["team"]:
        def build(t, p, rm, tree):
            return team.build(t, p, rm, tree, m, Leases(f"{rm}.architect"))
        r = deliver(ticket, SPEC, build, Ledger(), arm["rings"])
        rec.update(shipped=r["status"] == "accepted", patch=r.get("patch", ""), repair_rounds=r.get("rounds", 1) - 1)
    else:
        tree = sandbox.up(room)
        try:
            code(ticket["text"], pack(ticket, arm), room, tree, list(TOOLS), m, coder=coder)
            report = rings.verify(room, str(tree), rules, arm["rings"])
            patch = subprocess.run(["git", "-C", str(tree), "diff"], capture_output=True, text=True).stdout
            rec.update(shipped=report.ok and bool(patch), patch=patch, commits=commits(tree))
        finally:
            sandbox.down(room, tree)
    rec.setdefault("commits", 1)
    rec.update(credits=round(m["credits"], 4), refusals=m["refusals"], wall_min=round((time.monotonic() - start) / 60, 1))
    return rec


def hidden(ticket, patch):
    """The sealed oracle on the shipped patch, in a fresh room at the pin."""
    room = f"{ticket['id']}.hidden"
    tree = sandbox.up(room)
    try:
        if subprocess.run(["git", "-C", str(tree), "apply", "-"], input=patch.encode()).returncode:
            return False
        passed, printed = suite.oracle(ticket, room, tree)
        VERDICTS[ticket["id"], hashlib.sha1(patch.encode()).hexdigest()] = None if passed else violation(printed)
        return passed
    finally:
        sandbox.down(room, tree)


def violation(printed):
    """The class of rule the oracle reported broken, read off its FAIL line."""
    line = next((ln for ln in printed.splitlines() if ln.startswith("FAIL")), "")
    return next((cls for cls, marks in CLASS_OF.items() if any(re.search(re.escape(k), line) for k in marks)), None)


def label(path="results/story.jsonl"):
    """Add the violation class to every record the harness wrote, from what its hidden oracle printed."""
    recs = [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    for r in recs:
        r.setdefault("violation", VERDICTS.get((r["ticket"], hashlib.sha1(r["patch"].encode()).hexdigest())))
    Path(path).write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")


def main(arms=tuple(harness.ARMS)):
    sealed = [t for t in suite.load() if t["kind"] != "dev"]
    for arm in arms:
        harness.run(arm, CODER, sealed, attempt, hidden)
    label()
    print(f"{len(arms)} arms x {len(sealed)} tickets with {CODER}: results/story.jsonl")


if __name__ == "__main__":
    main(tuple(sys.argv[1:]) or tuple(harness.ARMS))
