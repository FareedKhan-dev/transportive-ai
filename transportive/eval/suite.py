"""eval/suite.py: sealed tickets and oracles."""
import hashlib
import json
from pathlib import Path

import yaml

from ..config import ASSETS
from ..workspace import sandbox


def load(root="assets/tickets"):
    return [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(Path(root).glob("*.yaml"))]


def seal(root="assets/oracles"):
    files = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(root).rglob("*.py"))}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    Path(root, "MANIFEST.json").write_text(json.dumps({"sha256": digest, "files": files}, indent=1), encoding="utf-8")
    return digest, len(files)


def oracle(ticket, room, tree):
    # mounted read only, outside the coder's worktree
    r = sandbox.run(room, tree, "pytest", "-c", "pyproject.toml", "-q", "-s", "-n", "0", "--tb=no", "-rN",
                    f"/oracles/{ticket['id']}.py", mounts=[f"{(ASSETS / 'oracles').resolve()}:/oracles:ro"])
    return r.returncode == 0, r.stdout


def run(ticket, commit):
    room = f"{ticket['id']}-{commit[:7]}"
    tree = sandbox.up(room, commit)
    try:
        return oracle(ticket, room, tree)[0]
    finally:
        sandbox.down(room, tree)


def valid(ticket, run=run):
    return not run(ticket, ticket["bug_commit"]) and run(ticket, ticket["fix_commit"])
