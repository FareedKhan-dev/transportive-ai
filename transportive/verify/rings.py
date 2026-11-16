"""verify/rings.py: five rings, inner to outer."""
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..config import SALEOR_PIN
from ..workspace import sandbox

TASK = "saleor/payment/tasks.py"


@dataclass
class Report:
    ok: bool
    ring: int = 0
    why: str = ""


def shell(room, tree, *cmd):
    r = sandbox.run(room, tree, *cmd)
    out = r.stdout + r.stderr
    return r.returncode == 0, next(iter(re.findall(r"^E +(.+)$", out, re.M)), out[-400:])


def formal(room, tree, rules):
    from . import model
    touched = subprocess.run(["git", "-C", str(tree), "diff", "--quiet", SALEOR_PIN, "--", TASK]).returncode == 1
    if touched and any(r.kind == "at_most_once" and r.source.startswith(TASK) for r in rules):
        states, trace = model.check(*model.release_task(*model.switches(Path(tree, TASK).read_text(encoding="utf-8"))))
        if trace:
            return False, f"model check, {states} states: two refund requests after {len(trace)} steps: {trace}"
    return True, ""


RINGS = {
    # 1 lint and types, 2 the model checker, 3 the spec tests
    1: lambda room, tree, rules: shell(room, tree, "sh", "-c", "ruff check saleor/payment && mypy saleor/payment"),
    2: formal,
    3: lambda room, tree, rules: shell(room, tree, "pytest", "-x", "-q", "test_from_spec.py"),
    # 4 Saleor's payment suite, 5 a person
    4: lambda room, tree, rules: shell(room, tree, "pytest", "-x", "-q", "-n", "8", "saleor/payment"),
    5: lambda room, tree, rules: (Path(tree, "APPROVED").exists(), "waiting for the owner to approve the receipt"),
}


def verify(room, tree, rules, rings=(1, 2, 3, 4, 5)):
    for n in rings:
        ok, why = RINGS[n](room, tree, rules)
        if not ok:
            return Report(False, n, why)
    return Report(True)
