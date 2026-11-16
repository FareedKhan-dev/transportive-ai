"""verify/model.py: every interleaving of the release task."""
import ast
from collections import deque


def check(init, steps, bad, limit=500_000):
    """(states seen, shortest trace to a bad state or None)."""
    seen, queue = {init: None}, deque([init])
    while queue and len(seen) < limit:
        state = queue.popleft()
        if bad(state):
            trace = []
            while seen[state] is not None:
                state, step = seen[state]
                trace.append(step)
            return len(seen), trace[::-1]
        for step, nxt in steps(state):
            if nxt not in seen:
                seen[nxt] = (state, step)
                queue.append(nxt)
    return len(seen), ["state limit reached"] if queue else None


def switches(source, fn="transaction_release_funds_for_checkout_task"):
    """(row lock, writer recheck), read from the task."""
    body = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == fn)
    calls = [n for n in ast.walk(body) if isinstance(n, ast.Call)]
    # criterion two: ordered row locks
    locked = any(getattr(c.func, "id", getattr(c.func, "attr", "")).endswith("select_for_update") for c in calls)
    # criterion one: a recheck on the writer
    return locked, any(k.arg == "last_refund_success" and getattr(k.value, "value", None) is True
                       for c in calls for k in c.keywords)


def at(pcs, w, pc):
    return tuple(pc if i == w else old for i, old in enumerate(pcs))


def release_task(locked, rechecked, runs=3):
    # state: two workers, flag on writer and replica, lock, sent, reruns
    def steps(s):
        pcs, (writer, replica, lock, sent, left) = s[:2], s[2:]
        out = [("standby replays the commit", (*pcs, writer, writer, lock, sent, left))] if replica != writer else []
        for w, who in enumerate("ab"):
            pc = pcs[w]
            if pc == "start":
                out.append((f"{who} reads the replica", (*at(pcs, w, "picked" if replica else "done"), *s[2:])))
            elif pc == "picked" and (lock is None or not locked):
                go = writer or not rechecked
                out.append((f"{who} rereads the writer", (*at(pcs, w, "read" if go else "done"), writer, replica,
                                                          who if locked and go else lock, sent, left)))
            elif pc == "read":
                out.append((f"{who} commits the flag", (*at(pcs, w, "sending"), False, replica, None, sent, left)))
            elif pc == "sending":
                out.append((f"{who} sends a refund request", (*at(pcs, w, "done"), writer, replica, lock, sent + 1, left)))
            elif pc == "done" and left:
                out.append((f"{who} runs again", (*at(pcs, w, "start"), writer, replica, lock, sent, left - 1)))
        return out
    return ("start", "start", True, True, None, 0, runs), steps, lambda s: s[5] > 1   # bad: a second request
