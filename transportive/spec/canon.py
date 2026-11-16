"""spec/canon.py: one canonical form and a fingerprint."""
import hashlib
import json

from .language import Rule, Spec

SHORTHAND = {   # Crespo's case keys as rules of our language
    ("refund_policy", "Full"): {"kind": "bound", "expr": "amount + refunded <= charged"},
    ("refund_policy", "Prorated"): {"kind": "bound", "expr": "amount + refunded <= charged * (30 - days) / 30"},
    ("duplicate_execution", "Forbidden"): {"kind": "at_most_once", "expr": "requested <= 1"},
}


def canon(doc):
    rules = [Rule(**r) for r in doc.get("rules", [])]
    cases = doc.get("contexts", {}).get("cases", [])
    for case in cases:
        rules += [Rule(f"{case['name']}.{k}", when=case["when"], **SHORTHAND[(k, v)]) for k, v in case["rules"].items()]
    return Spec(doc["specification"]["id"], str(doc.get("version", "1.0")), sorted(rules, key=lambda r: r.id), cases,
                doc.get("context_resolution", {}))


def fingerprint(spec):
    # meaning only, so a new owner keeps it
    rows = [[r.id, r.kind, r.when, r.expr, r.effect] for r in spec.rules]
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:12]


def prose(spec):
    def where(w):
        return ", ".join(f"{k} {v}" for k, v in w.items()) or "every context"
    return "\n".join(f"- {r.id} ({where(r.when)}): {r.effect} {r.expr}. Source: {r.source}" for r in spec.rules)
