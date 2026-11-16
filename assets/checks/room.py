"""checks/room.py: what a room must be before a candidate runs in it, printed one line per fact."""
import os
import subprocess
import time
from pathlib import Path

import psycopg

primary = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
standby = psycopg.connect(os.environ["DATABASE_URL_REPLICA"], autocommit=True)
files = sum(1 for _ in Path("/app/saleor/payment").rglob("*.py"))
print(f"worktree  /app, saleor/payment with {files} files")
major = primary.execute("SHOW server_version_num").fetchone()[0][:2]
print(f"primary   PostgreSQL {major}, wal_level {primary.execute('SHOW wal_level').fetchone()[0]}")
delay = standby.execute("SHOW recovery_min_apply_delay").fetchone()[0]
print(f"standby   in recovery {standby.execute('SELECT pg_is_in_recovery()').fetchone()[0]}, recovery_min_apply_delay {delay}")
primary.execute("CREATE TABLE IF NOT EXISTS room_probe (at double precision)")
while standby.execute("SELECT to_regclass('room_probe')").fetchone()[0] is None:
    time.sleep(0.05)
mark = time.time()
primary.execute("INSERT INTO room_probe VALUES (%s)", [mark])
while not standby.execute("SELECT count(*) FROM room_probe WHERE at = %s", [mark]).fetchone()[0]:
    time.sleep(0.05)
print(f"lag       a row written on the primary reached the standby after {time.time() - mark:.1f} s")
pip = subprocess.run(["pip", "download", "--no-deps", "-d", "/tmp/probe", "django"], capture_output=True, text=True)
print("network   pip download django:", "reached the internet" if pip.returncode == 0 else "failed, no route out")
