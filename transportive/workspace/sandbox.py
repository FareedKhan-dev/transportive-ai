"""workspace/sandbox.py: a room per candidate."""
import os
import subprocess
from pathlib import Path

from ..config import ASSETS, REPLICA_LAG_S, SALEOR, SALEOR_PIN

COMPOSE = str(ASSETS / "workspace" / "compose.yaml")


def compose(room, *args, check=False):
    env = {**os.environ, "APPLY_DELAY": f"{int(REPLICA_LAG_S * 1000)}ms"}   # how late the standby applies commits
    return subprocess.run(["docker", "compose", "-p", room.lower().replace(".", "-"), "-f", COMPOSE, *args], env=env, capture_output=True,
                          text=True, check=check)


def up(room, commit=SALEOR_PIN):
    tree = (SALEOR.parent / "rooms" / room).resolve()
    subprocess.run(["git", "-C", str(SALEOR), "worktree", "add", "--detach", str(tree), commit], check=True)
    compose(room, "up", "-d", "--wait", check=True)
    return tree


def run(room, tree, *cmd, mounts=()):
    vols = [x for m in (f"{Path(tree).resolve()}:/app", *mounts) for x in ("-v", m)]
    return compose(room, "run", "--rm", *vols, "app", *cmd)


def down(room, tree):
    compose(room, "down", "-v")
    subprocess.run(["git", "-C", str(SALEOR), "worktree", "remove", "--force", str(tree)], check=True)
