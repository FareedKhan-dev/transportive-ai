You are the tester. You see the rule pack below and nothing else: no source code and no patch.
Write pytest tests for the rules that the ticket's change can break, in one file.
- For every bound, invariant and at-most-once rule, build a state machine with
  transportive.verify.compile.machine(rules, moves, observe). The moves are what the world can do: a request, a retry,
  a duplicate webhook, a late refund failure, a crash between two commits.
- For every rule that two writers can break at once, add a race with transportive.verify.race.race(op, pause), on two
  database connections. One connection on its own cannot show a race.
- For every split amount, add transportive.verify.compile.same_end.
Mark tests that write to the database with @pytest.mark.django_db(transaction=True), and read the replica through the
alias the room's conftest points at the standby. Reply with Python source only.
The rule pack follows.
