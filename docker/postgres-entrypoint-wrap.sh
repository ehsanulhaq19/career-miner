#!/bin/sh
set -e

PGDATA="${PGDATA:-/var/lib/postgresql/data}"

# Existing volumes may have postgres role with login disabled (common after
# internet-facing brute-force / CVE exploit attempts). Re-apply credentials
# before the server starts (idempotent, fast).
if [ -s "${PGDATA}/PG_VERSION" ]; then
  gosu postgres sh -c "echo \"ALTER ROLE postgres WITH LOGIN SUPERUSER PASSWORD '${POSTGRES_PASSWORD:-postgres}';\" | postgres --single -D \"${PGDATA}\" postgres" >/dev/null 2>&1 || true
fi

# Restrict authentication to local/docker networks when a custom hba file is mounted.
if [ -f /etc/postgresql/pg_hba.conf ]; then
  cp /etc/postgresql/pg_hba.conf "${PGDATA}/pg_hba.conf"
fi

# Ensure dedicated app role exists (e.g. admin) before the server accepts connections.
if [ -f /usr/local/bin/ensure-app-user.sh ]; then
  sh /usr/local/bin/ensure-app-user.sh
fi

exec docker-entrypoint.sh "$@"
