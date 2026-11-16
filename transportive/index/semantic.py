"""index/semantic.py: scopes and database effects, for the agents."""
import ast
import symtable
from pathlib import Path

EFFECTS = {"select_for_update": "row lock", "atomic": "transaction", "uuid4": "fresh key", "bulk_create": "bulk insert",
           "bulk_update": "bulk write"}


def scopes(path):
    found, todo = {}, [symtable.symtable(Path(path).read_text(encoding="utf-8"), str(path), "exec")]
    while todo:
        table = todo.pop()
        todo += table.get_children()
        if table.get_type() == "function":
            found[table.get_name()] = table.get_parameters()
    return found


def effects(path):
    out = []
    for node in ast.walk(ast.parse(Path(path).read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            name, args = getattr(node.func, "attr", getattr(node.func, "id", "")), [ast.unparse(a) for a in node.args]
            hit = next((k for k in EFFECTS if name.endswith(k)), None)
            if name == "using" and any("REPLICA" in a for a in args):     # a read from the lagging standby
                out.append((node.lineno, "replica read", args[0]))
            elif hit:
                out.append((node.lineno, EFFECTS[hit], name))
    return sorted(out)
