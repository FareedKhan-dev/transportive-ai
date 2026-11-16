"""engine/transport.py: transport laws between contexts."""
from decimal import ROUND_DOWN, Decimal

PENNY = Decimal("0.01")


def split(amount, parts):
    """Allocate, never divide."""
    base = (amount / parts).quantize(PENNY, rounding=ROUND_DOWN)
    left = int((amount - base * parts) / PENNY)                     # pennies left after rounding down
    return [base + PENNY if i < left else base for i in range(parts)]


def divide(amount, parts):
    return [(amount / parts).quantize(PENNY)] * parts


def merge(parts):
    return sum(parts, Decimal(0))


LAWS = {   # (from, to): a missing pair is blocked
    ("charge", "installments"): split,
    ("installments", "charge"): merge,
    ("order_lines", "stock"): merge,       # two lines on one stock must add up, never overwrite (#19957)
}


def transport(value, path, parts=1, laws=LAWS):
    for a, b in zip(path, path[1:]):           # laws compose step by step
        if a == b:
            continue                           # the identity law: staying in a context changes nothing
        if (a, b) not in laws:
            raise ValueError(f"blocked: no law carries {a} to {b}")
        law = laws[(a, b)]
        value = law(value, parts) if law in (split, divide) else law(value)
    return value


def holonomy(amount, parts, laws=LAWS):
    """Hol(r) = T(loop)(r) - r."""
    return transport(amount, ["charge", "installments", "charge"], parts, laws) - amount
