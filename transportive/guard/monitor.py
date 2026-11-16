"""guard/monitor.py: shadow replay and a kill switch."""
from ..verify.compile import holds


def shadow(events, rules):
    return [(e["id"], r.id) for e in events for r in rules if r.db and not holds(r, e["after"])]


def kill(channels):
    # the task reads this setting, so False stops it
    return channels.update(release_funds_for_expired_checkouts=False)
