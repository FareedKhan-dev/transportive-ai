"""eval/harness.py: arms, coders and statistics."""
import json

from scipy.stats import binomtest

ARMS = {
    "A1": {"pack": "plain", "gate": False, "rings": (1,), "team": False},
    "A2": {"pack": "agents_md", "gate": False, "rings": (1,), "team": False},
    "A3": {"pack": "spec", "gate": True, "rings": (1,), "team": False},
    "A4": {"pack": "spec", "gate": True, "rings": (1, 2, 3, 4), "team": True},
}


def run(arm, coder, tickets, attempt, oracle, out="results/story.jsonl"):
    with open(out, "a", encoding="utf-8") as f:
        for t in tickets:
            rec = {"arm": arm, "coder": coder, "ticket": t["id"], **attempt(t, ARMS[arm], coder)}
            rec["hidden_pass"] = bool(rec["shipped"]) and oracle(t, rec["patch"])
            f.write(json.dumps(rec) + "\n")


def wilson(k, n):
    ci = binomtest(k, n).proportion_ci(method="wilson")
    return k / n, ci.low, ci.high


def mcnemar(a, b):
    """(only a passes, only b passes, exact p)."""
    # only the tickets the arms disagree on count
    x, y = sum(p and not q for p, q in zip(a, b)), sum(q and not p for p, q in zip(a, b))
    return x, y, binomtest(min(x, y), x + y).pvalue if x + y else 1.0


def green_but_wrong(recs):
    """P(hidden oracle fails | own checks green)."""
    shipped = [r for r in recs if r["shipped"]]
    return sum(not r["hidden_pass"] for r in shipped) / len(shipped) if shipped else 0.0
