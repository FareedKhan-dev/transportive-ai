"""ledger/trace.py: rule, context, file, ticket and patch."""
import json
import sqlite3

SCHEMA = "CREATE TABLE IF NOT EXISTS trace (rule TEXT, context TEXT, file TEXT, ticket TEXT, patch TEXT)"


class Ledger:
    def __init__(self, path="results/ledger.db"):
        self.db = sqlite3.connect(path)
        self.db.execute(SCHEMA)

    def record(self, rule, context, file, ticket, patch):
        self.db.execute("INSERT INTO trace VALUES (?, ?, ?, ?, ?)",
                        (rule, json.dumps(context, sort_keys=True), file, ticket, patch))
        self.db.commit()

    def impact(self, contexts):
        """(files, tickets) to revisit where the meaning changed."""
        keys = [json.dumps(c, sort_keys=True) for c in contexts]
        rows = self.db.execute(f"SELECT file, ticket FROM trace WHERE context IN ({','.join('?' * len(keys))})",
                               keys).fetchall()
        return sorted({s for s, _ in rows}), sorted({c for _, c in rows})
