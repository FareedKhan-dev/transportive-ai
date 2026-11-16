"""spec/language.py: rule kinds and what they compile to."""
from dataclasses import dataclass, field

COORDS = {"region": ("EU", "US", "BR"), "method": ("card", "sepa_debit", "boleto", "voucher"),
          "contract": ("standard", "subscription")}
# what a refund reads, typed for Z3
STATE = {"amount": "real", "charged": "real", "refunded": "real", "surcharge": "real", "charge_events": "real",
         "requested": "int", "days": "int", "allocated": "int", "allocations": "int", "disputed": "bool",
         "consent": "bool", "same_means": "bool", "returned": "bool", "credential_closed": "bool"}
KINDS = {"bound": ("property", "check"), "at_most_once": ("stateful", "unique"), "invariant": ("stateful", "check"),
         "deadline": ("clock", None), "same_means": ("property", None), "transition": ("stateful", None),
         "atomic": ("fault", None), "env": ("stateful", None)}     # kind: (the test it becomes, its database guard)


@dataclass
class Rule:
    id: str
    kind: str
    when: dict                   # the coordinates it covers, a missing one means any
    expr: str                    # a formula over STATE, such as "amount + refunded <= charged"
    effect: str = "require"      # require, forbid or permit, and forbid beats permit
    source: str = ""             # file:line in Saleor, or a fact id with its quote
    owner: str = ""
    db: dict = None              # its guard: {guard, model, q}, plus fields if unique


@dataclass
class Spec:
    id: str
    version: str
    rules: list = field(default_factory=list)
    cases: list = field(default_factory=list)       # Crespo's named contexts, each a when and its rules
    resolution: dict = field(default_factory=dict)  # what the door does on no match and on a tie
