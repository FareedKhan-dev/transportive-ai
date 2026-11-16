"""verify/race.py: a race on two connections."""
import importlib
import threading

from django.db import connection, connections


def hold(target, name, barrier):
    # both threads pause right after the target
    real = getattr(target, name)

    def held(*args, **kwargs):
        value = real(*args, **kwargs)
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass                                    # the other is stuck on a row lock
        return value
    setattr(target, name, held)
    return real


def worker(who, op, out):
    connection.ensure_connection()
    out[who] = {"pid": connection.connection.info.backend_pid}
    try:
        out[who]["result"] = op()
    except Exception as e:                           # a constraint error is a result too, and a loud one
        out[who]["result"] = repr(e)
    connections.close_all()


def race(op, pause, wait=5.0):
    """Run op twice at once. A row lock times the barrier out."""
    module, name = pause.rsplit(".", 1)
    target, out = importlib.import_module(module), {}
    real = hold(target, name, threading.Barrier(2, timeout=wait))
    threads = [threading.Thread(target=worker, args=(who, op, out)) for who in "ab"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    setattr(target, name, real)
    return out
