"""verify/mutate.py: the mutation gate."""
import ast

FLIP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt}     # off-by-one mutants


def splice(source, node, text):
    # only the node's span changes, so a "# type: ignore" stays
    data, starts = source.encode(), [0]            # ast offsets count UTF-8 bytes
    for line in data.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    a, b = starts[node.lineno - 1] + node.col_offset, starts[node.end_lineno - 1] + node.end_col_offset
    return (data[:a] + text.encode() + data[b:]).decode()


def mutants(source, fn):
    body = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == fn)
    out = []
    for node in ast.walk(body):
        if isinstance(node, ast.Compare) and type(node.ops[0]) in FLIP:
            new = ast.Compare(node.left, [FLIP[type(node.ops[0])](), *node.ops[1:]], node.comparators)
            out.append(("boundary", node.lineno, splice(source, node, ast.unparse(new))))
        elif isinstance(node, ast.Call):
            for kw in node.keywords:                                   # one mutant per dropped keyword
                new = ast.Call(node.func, node.args, [k for k in node.keywords if k is not kw])
                out.append((f"no {kw.arg}", node.lineno, splice(source, node, ast.unparse(new))))
    return out


def kill_matrix(path, fn, verify):
    original, counts = path.read_text(encoding="utf-8"), {}
    try:
        for kind, line, source in mutants(original, fn):
            path.write_text(source, encoding="utf-8")
            report = verify()
            key = f"ring {report.ring}" if not report.ok else "survived"   # the first failing ring kills it
            counts[key] = counts.get(key, 0) + 1
    finally:
        path.write_text(original, encoding="utf-8")
    return counts
