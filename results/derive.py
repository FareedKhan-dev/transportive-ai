"""derive.py: turn results/story.json into eval.json, ablation.json, headline.json and claims.json.

Every derived leaf is {"v": value, "provisional": flag}, where the flag is true as long as any input it reads is
provisional. Rates are recomputed from counts, never typed, so a real story.json replaces every number at once.

    .venv/Scripts/python.exe -I results/derive.py
"""
import json
import math
import random
import statistics
from pathlib import Path

from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
ARMS, CODERS = ("A1", "A2", "A3", "A4"), ("opus", "qwen")
ALPHA = 0.05


def load(name):
    return json.loads((HERE / f"{name}.json").read_text(encoding="utf-8"))


def write(name, data):
    (HERE / f"{name}.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")


def leaf(v, prov=True):
    if isinstance(v, float):
        v = round(v, 6)
    return {"v": v, "provisional": prov}


def wilson(k, n):
    ci = binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    return [round(100 * ci.low, 1), round(100 * ci.high, 1)]


def mcnemar(a, b):
    """Exact two-sided McNemar on two paired outcome lists: (b, c, p), where b counts a pass and b fail."""
    only_a = sum(1 for x, y in zip(a, b) if x and not y)
    only_b = sum(1 for x, y in zip(a, b) if y and not x)
    n = only_a + only_b
    p = binomtest(min(only_a, only_b), n, 0.5).pvalue if n else 1.0
    return only_a, only_b, p


def pct(k, n):
    return 100.0 * k / n if n else 0.0


def percentile(xs, q):
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def bootstrap_per_accepted(recs, rng, reps=2000):
    vals = []
    for _ in range(reps):
        draw = [recs[rng.randrange(len(recs))] for _ in recs]
        acc = sum(r["hidden_pass"] for r in draw)
        if acc:
            vals.append(sum(r["credits"] for r in draw) / acc)
    return [round(percentile(vals, 0.025), 2), round(percentile(vals, 0.975), 2)]


def holm(pvalues):
    """{name: adjusted p} with Holm's step-down correction."""
    order = sorted(pvalues, key=pvalues.get)
    m, out, running = len(order), {}, 0.0
    for i, name in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvalues[name]))
        out[name] = running
    return out


def main():
    story, suite = load("story"), load("suite")
    tickets = {t["id"]: t for t in suite["sealed"]}
    ambiguous = {t["id"] for t in suite["sealed"] if t["ambiguous"]}
    conflicts = {t["id"] for t in suite["sealed"] if t["conflict"]}
    classes = suite["classes"]
    rng = random.Random(7)
    arms = {}
    for arm in ARMS:
        arms[arm] = {}
        for coder in CODERS:
            recs = story["runs"][f"{arm}.{coder}"]
            n = len(recs)
            passed = sum(r["hidden_pass"] for r in recs)
            shipped = sum(r["shipped"] for r in recs)
            wrong = sum(r["shipped"] and not r["hidden_pass"] for r in recs)
            viol = {c: sum(1 for r in recs if r["violation"] == c) for c in classes}
            asked = {r["ticket"] for r in recs if r["asked"]}
            flagged = {r["ticket"] for r in recs if r["conflict_flagged"]}
            commits = sum(r["commits"] for r in recs)
            credits = sum(r["credits"] for r in recs)
            walls = [r["wall_min"] for r in recs]
            row = {
                "n": leaf(n), "pass": leaf(passed), "pass_pct": leaf(pct(passed, n)), "pass_ci": leaf(wilson(passed, n)),
                "wilson_lo": leaf(wilson(passed, n)[0] / 100), "wilson_hi": leaf(wilson(passed, n)[1] / 100),
                "gw": leaf(wrong / shipped if shipped else 0.0),
                "shipped": leaf(shipped), "green_wrong": leaf(wrong), "gw_pct": leaf(pct(wrong, shipped)),
                "not_shipped": leaf(n - shipped),
                "violations": {c: leaf(v) for c, v in viol.items()}, "violations_total": leaf(sum(viol.values())),
                "asked": leaf(len(asked)), "clar_recall_pct": leaf(pct(len(asked & ambiguous), len(ambiguous))),
                "clar_precision_pct": leaf(pct(len(asked & ambiguous), len(asked)) if asked else 0.0),
                "conflicts_flagged": leaf(len(flagged & conflicts)), "conflicts_silent": leaf(
                    sum(1 for r in recs if r["ticket"] in conflicts and r["shipped"] and r["ticket"] not in flagged)),
                "commits": leaf(commits), "commits_per_accepted": leaf(commits / passed if passed else None),
                "credits_total": leaf(credits), "credits_per_ticket": leaf(credits / n),
                "credits_per_accepted": leaf(credits / passed), "credits_per_accepted_ci": leaf(bootstrap_per_accepted(recs, rng)),
                "wall_p50": leaf(percentile(walls, 0.5)), "wall_p95": leaf(percentile(walls, 0.95)),
            }
            if arm == "A4":
                rounds = [r["repair_rounds"] for r in recs if r["shipped"]]
                row["repair_rounds_mean"] = leaf(statistics.mean(rounds))
            if coder == "opus":
                row["opus_mtok"] = leaf(sum(sum(r["tokens"].values()) for r in recs) / 1e6)
            else:
                row["gpu_hours"] = leaf(sum(r["gpu_min"] for r in recs) / 60)
            arms[arm][coder] = row
    outcome = {k: [r["hidden_pass"] for r in v] for k, v in story["runs"].items()}
    b, c, p_h6 = mcnemar(outcome["A4.qwen"], outcome["A1.opus"])
    b2, c2, p_opus = mcnemar(outcome["A4.opus"], outcome["A1.opus"])
    a1o = story["runs"]["A1.opus"]
    gw_k = sum(r["shipped"] and not r["hidden_pass"] for r in a1o)
    gw_n = sum(r["shipped"] for r in a1o)
    p_h1 = binomtest(gw_k, gw_n, 0.10, alternative="greater").pvalue           # green-but-wrong above a 10% tolerance
    a2o = story["runs"]["A2.opus"]
    silent = sum(1 for r in a2o if r["ticket"] in conflicts and r["shipped"] and not r["conflict_flagged"])
    p_h2 = binomtest(silent, len(conflicts), 0.5, alternative="greater").pvalue  # prose resolves fewer than half
    pvals = {"H1": p_h1, "H2": p_h2, "H6": p_h6, "A4opus_vs_A1opus": p_opus}
    adjusted = holm(pvals)
    pilot = {}
    for coder, row in story["pilot"].items():
        green = sum(ch in "PW" for ch in row.values())
        ok = sum(ch == "P" for ch in row.values())
        pilot[coder] = {"tickets": leaf(len(row)), "green": leaf(green), "pass": leaf(ok),
                        "green_wrong": leaf(green - ok), "gw_pct": leaf(pct(green - ok, green))}
    par = story["parallel"]
    study_credits = (sum(r["credits"] for v in story["runs"].values() for r in v)
                     + sum(x.get("credits", 0) for x in story["ablation"]))
    eval_json = {
        "arms": arms,
        "tests": {"h6": {"b": leaf(b), "c": leaf(c), "p": leaf(p_h6), "p_repr": leaf(repr(float(p_h6))), "p_holm": leaf(adjusted["H6"])},
                  "a4_opus_vs_a1_opus": {"b": leaf(b2), "c": leaf(c2), "p": leaf(p_opus), "p_holm": leaf(adjusted["A4opus_vs_A1opus"])},
                  "h1": {"k": leaf(gw_k), "n": leaf(gw_n), "p": leaf(p_h1), "p_holm": leaf(adjusted["H1"])},
                  "h2": {"silent": leaf(silent), "n": leaf(len(conflicts)), "p": leaf(p_h2), "p_holm": leaf(adjusted["H2"])}},
        "pilot": pilot,
        "parallel": {m: {k: leaf(v) for k, v in d.items()} for m, d in par["modes"].items()},
        "guards": {k: leaf(v) for k, v in story["guards"].items() if k != "replayed_arm"},
        "wrong_context_shipped": {k: leaf(v) for k, v in story["wrong_context_shipped"].items()},
        "study": {"credits_total": leaf(study_credits),
                  "tickets_run": leaf(sum(len(v) for v in story["runs"].values()))},
        "setup": {"ci_level_pct": leaf(95, False), "alpha": leaf(ALPHA, False)},
    }
    write("eval", eval_json)

    base = arms["A4"]["qwen"]
    rows = []
    for x in story["ablation"]:
        r = {"row": x["row"], "how": x["how"]}
        if "pass" in x:
            r["pass"] = leaf(x["pass"])
            r["delta_pass"] = leaf(x["pass"] - base["pass"]["v"])
            r["double_refunds"] = leaf(x["double_refunds"])
            r["violations"] = leaf(x["violations"])
        for k in ("repair_rounds", "wrong_context_shipped", "weak_oracles", "broken_merges_shipped", "loud_errors"):
            if k in x:
                r[k] = leaf(x[k])
        rows.append(r)
    write("ablation", {"baseline": {"arm": "A4", "coder": "qwen", "pass": base["pass"],
                                    "double_refunds": base["violations"]["duplicate_transfer"],
                                    "violations": base["violations_total"],
                                    "repair_rounds": base["repair_rounds_mean"]},
                       "rows": rows})

    dr = {f"{a}.{c}": arms[a][c]["violations"]["duplicate_transfer"]["v"] for a in ARMS for c in CODERS}
    headline = {
        "a4_qwen_pass_pct": arms["A4"]["qwen"]["pass_pct"], "a4_opus_pass_pct": arms["A4"]["opus"]["pass_pct"],
        "a1_opus_pass_pct": arms["A1"]["opus"]["pass_pct"], "a1_qwen_pass_pct": arms["A1"]["qwen"]["pass_pct"],
        "a4_double_refunds": leaf(dr["A4.opus"] + dr["A4.qwen"]),
        "a1_double_refunds": leaf(dr["A1.opus"] + dr["A1.qwen"]),
        "a1_opus_gw_pct": arms["A1"]["opus"]["gw_pct"],
        "h6_p": leaf(p_h6), "sealed": leaf(len(tickets)),
    }
    write("headline", headline)

    verdicts = {
        "H1": "held" if adjusted["H1"] < ALPHA else "not held",
        "H2": "held" if silent >= 3 else "not held",
        "H3": "held" if dr["A3.opus"] >= 1 and dr["A3.qwen"] >= 1 else "not held",
        "H4": ("held in part" if story["wrong_context_shipped"]["A4.qwen"] < next(
            x["wrong_context_shipped"] for x in story["ablation"] if x["row"] == "region typing") else "not held"),
        "H5": "held" if dr["A4.opus"] == 0 and dr["A4.qwen"] == 0 else "not held",
        "H6": "held" if adjusted["H6"] < ALPHA and arms["A4"]["qwen"]["pass"]["v"] > arms["A1"]["opus"]["pass"]["v"] else "not held",
        "H7": "held" if par["modes"]["architect_leases_queue"]["broken_merges_shipped"] == 0 else "not held",
        "H8": "held" if story["guards"]["double_refunds_blocked"] == story["guards"]["double_refunds_replayed"] else "not held",
    }
    write("claims", {"verdicts": {k: leaf(v) for k, v in verdicts.items()},
                     "held": leaf(sum(v == "held" for v in verdicts.values())),
                     "held_in_part": leaf(sum(v == "held in part" for v in verdicts.values()))})
    print("arm  coder  pass  pass%  GW%   DR  viol  ask  flag  commits/acc  credits/acc  p50   p95")
    for a in ARMS:
        for cod in CODERS:
            r = arms[a][cod]
            print(f"{a}   {cod:5}  {r['pass']['v']:4}  {r['pass_pct']['v']:5.1f}  {r['gw_pct']['v']:4.1f}  "
                  f"{r['violations']['duplicate_transfer']['v']:3}  {r['violations_total']['v']:4}  {r['asked']['v']:3}  "
                  f"{r['conflicts_flagged']['v']:4}  {r['commits_per_accepted']['v']:11.2f}  {r['credits_per_accepted']['v']:11.3f}  "
                  f"{r['wall_p50']['v']:4.1f}  {r['wall_p95']['v']:4.1f}")
    print(f"H6 McNemar b={b} c={c} p={p_h6:.5f}  holm={adjusted['H6']:.5f}   verdicts: {verdicts}")
    print(f"study credits {study_credits:.1f}")


if __name__ == "__main__":
    main()
