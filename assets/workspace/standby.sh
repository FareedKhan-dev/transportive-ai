#!/bin/bash
# copy the primary once, then replay its WAL APPLY_DELAY late
set -e
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  until pg_basebackup -h primary -U replicator -D "$PGDATA" -R -X stream; do sleep 1; done
  echo "recovery_min_apply_delay = '$APPLY_DELAY'" >> "$PGDATA/postgresql.auto.conf"
  chown -R postgres:postgres "$PGDATA" && chmod 700 "$PGDATA"
fi
exec gosu postgres postgres -c hot_standby=on
