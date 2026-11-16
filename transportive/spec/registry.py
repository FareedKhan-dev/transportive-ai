"""spec/registry.py: signed, versioned specs."""
import dataclasses
import json
from pathlib import Path

from .canon import fingerprint
from .language import Rule


def amend(spec, decision):
    major, minor = spec.version.split(".")
    rule = Rule(decision["id"], decision["kind"], decision["when"], decision["expr"], source=decision["id"],
                owner=decision["owner"])
    return dataclasses.replace(spec, version=f"{major}.{int(minor) + 1}", rules=sorted(spec.rules + [rule], key=lambda r: r.id))


def publish(spec, signed, conflicts, root="assets/registry"):
    unsigned = sorted({r.owner for r in spec.rules if r.owner and r.owner not in signed})
    if unsigned or conflicts:
        raise ValueError(f"spec {spec.version} not published: unsigned {unsigned}, conflicts {conflicts}")
    path = Path(root, f"{spec.id}-{spec.version}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fingerprint": fingerprint(spec), "rules": [vars(r) for r in spec.rules]}, indent=1))
    return path
