"""agents/team.py: a surgical team of agents."""
import json
import subprocess
from pathlib import Path

from ..config import ASSETS
from .broker import Session
from .coder import TOOLS, code

ROLES = {r: (ASSETS / "prompts" / f"{r}.md").read_text(encoding="utf-8") for r in ("architect", "tester")}


def plan(ticket, pack, meter):
    # tasks as JSON, each with its rules and symbols
    text, _ = Session(ROLES["architect"] + pack, [], meter).turn(f"<ticket>\n{ticket['text']}\n</ticket>")
    return json.loads(text[text.index("["): text.rindex("]") + 1])


def tests(pack, meter):
    # rules only, never the patch or the source
    text, _ = Session(ROLES["tester"] + pack, [], meter).turn("Write the tests. Reply with Python source only.")
    return text


def build(ticket, pack, room, tree, meter, leases):
    work = plan(ticket, pack, meter)
    for task in work:
        if not leases.take(task["rules"] + task["symbols"]):
            return {"status": "blocked", "task": task["task"], "plan": work}
        code(task["task"], pack, room, tree, list(TOOLS), meter)
        leases.drop()
    Path(tree, "test_from_spec.py").write_text(tests(pack, meter), encoding="utf-8")
    subprocess.run(["git", "-C", str(tree), "add", "-N", "test_from_spec.py"])   # so the patch carries the tests
    return {"status": "built", "plan": work}
