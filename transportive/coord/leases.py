"""coord/leases.py: a lease per rule or symbol."""
import hashlib

import psycopg

from ..config import COORD_DSN


def key(name):
    # advisory locks take a 64-bit key
    return int.from_bytes(hashlib.blake2b(name.encode(), digest_size=8).digest(), "big", signed=True)


class Leases:
    """One connection per agent, and a lock lives as long as it."""
    def __init__(self, agent, dsn=COORD_DSN):
        self.agent, self.db, self.held = agent, psycopg.connect(dsn, autocommit=True), []

    def take(self, names):
        # one order for all, so one of two requests wins
        for name in sorted(set(names)):
            if not self.db.execute("SELECT pg_try_advisory_lock(%s)", [key(name)]).fetchone()[0]:
                self.drop()
                return False
            self.held.append(name)
        return True

    def drop(self):
        for name in self.held:
            self.db.execute("SELECT pg_advisory_unlock(%s)", [key(name)])
        self.held = []
