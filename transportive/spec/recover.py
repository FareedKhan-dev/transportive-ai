"""spec/recover.py: rules mined from code and law."""
import ast
from pathlib import Path

from .language import Rule


def calls(node, name):
    return isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) == name


def mine(root, package="saleor/payment"):
    out = []
    for path in sorted(p for p in Path(root, package).rglob("*.py") if "tests" not in p.parts):
        rel = path.relative_to(root).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            at = f"{rel}:{getattr(node, 'lineno', 0)}"
            # an if that raises marks a forbidden state
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and isinstance(node.body[0], ast.Raise):
                out.append(Rule(f"code.{len(out)}", "bound", {}, ast.unparse(node.test), "forbid", at))
            elif calls(node, "select_for_update"):
                out.append(Rule(f"code.{len(out)}", "atomic", {}, "locked", "require", at))
            elif calls(node, "uuid4"):                                      # a new key on every call
                out.append(Rule(f"code.{len(out)}", "at_most_once", {}, "fresh key per call", "forbid", at))
            elif calls(node, "UniqueConstraint"):                           # a key the database never repeats
                fields = next((ast.literal_eval(k.value) for k in node.keywords if k.arg == "fields"), [])
                out.append(Rule(f"code.{len(out)}", "at_most_once", {}, f"unique {fields}", "require", at))
    return out


def draft(facts, text_of):
    """(kept, dropped): a draft survives only if its quote is verbatim."""
    def flat(s):
        return " ".join(s.split())             # PDF spacing never decides a match
    kept = [f for f in facts if flat(f["quote"]) in flat(text_of(f["source"]))]
    rules = [Rule(f["id"], f["kind"], f["when"], f["expr"], f.get("effect", "require"), f["source"]) for f in kept]
    return rules, [f for f in facts if f not in kept]
