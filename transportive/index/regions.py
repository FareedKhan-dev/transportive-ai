"""index/regions.py: code regions typed by context."""
import ast

COORD_OF = {"payment_method_type": "method", "region": "region", "country": "region", "contract": "contract"}


def regions(source):
    out = []
    for node in ast.walk(ast.parse(source)):
        # an if on a coordinate types the lines of its body
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            attr, value = getattr(node.test.left, "attr", None), node.test.comparators[0]
            if attr in COORD_OF and isinstance(value, ast.Constant):
                out.append((node.body[0].lineno, node.body[-1].end_lineno, {COORD_OF[attr]: value.value}))
    return out


def wrong_context(source, changed, ticket):
    return [(a, b, typed) for a, b, typed in regions(source) if any(a <= n <= b for n in changed)
            and any(ticket.get(k, v) != v for k, v in typed.items())]
