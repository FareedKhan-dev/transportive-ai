#!/bin/bash
# a replication user for the standby, and the line in pg_hba.conf that lets it in
set -e
psql -v ON_ERROR_STOP=1 -U saleor -d saleor -c "CREATE ROLE replicator WITH REPLICATION LOGIN PASSWORD 'replica'"
echo "host replication replicator all scram-sha-256" >> "$PGDATA/pg_hba.conf"
