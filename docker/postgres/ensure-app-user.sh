#!/bin/sh
# Create or update the application DB role (default: admin/admin).
# Runs offline during container entrypoint (postgres --single) or online via psql.
set -e

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
APP_USER="${POSTGRES_APP_USER:-admin}"
APP_PASSWORD="${POSTGRES_APP_PASSWORD:-admin}"
APP_DB="${POSTGRES_DB:-careerminer}"
SUPERUSER="${POSTGRES_USER:-postgres}"

[ -n "$APP_USER" ] || exit 0
[ "$APP_USER" = "$SUPERUSER" ] && exit 0

esc_pass=$(printf "%s" "$APP_PASSWORD" | sed "s/'/''/g")

run_sql() {
  database=$1

  if [ "${ENSURE_APP_USER_ONLINE:-0}" = "1" ] && gosu postgres pg_isready -q 2>/dev/null; then
    gosu postgres psql -v ON_ERROR_STOP=1 -U "$SUPERUSER" -d "$database" <<EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_USER}') THEN
    CREATE ROLE "${APP_USER}" WITH LOGIN PASSWORD '${esc_pass}';
  ELSE
    ALTER ROLE "${APP_USER}" WITH LOGIN PASSWORD '${esc_pass}';
  END IF;
END
\$\$;
EOSQL
    if [ "$database" = "postgres" ]; then
      gosu postgres psql -v ON_ERROR_STOP=1 -U "$SUPERUSER" -d postgres <<EOSQL
GRANT ALL PRIVILEGES ON DATABASE "${APP_DB}" TO "${APP_USER}";
EOSQL
    else
      gosu postgres psql -v ON_ERROR_STOP=1 -U "$SUPERUSER" -d "$database" <<EOSQL
GRANT ALL ON SCHEMA public TO "${APP_USER}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "${APP_USER}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${APP_USER}";
EOSQL
    fi
  elif [ -s "${PGDATA}/PG_VERSION" ]; then
    gosu postgres postgres --single -D "$PGDATA" "$database" <<EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_USER}') THEN
    CREATE ROLE "${APP_USER}" WITH LOGIN PASSWORD '${esc_pass}';
  ELSE
    ALTER ROLE "${APP_USER}" WITH LOGIN PASSWORD '${esc_pass}';
  END IF;
END
\$\$;
EOSQL
    if [ "$database" = "postgres" ]; then
      gosu postgres postgres --single -D "$PGDATA" postgres <<EOSQL
GRANT ALL PRIVILEGES ON DATABASE "${APP_DB}" TO "${APP_USER}";
EOSQL
    else
      gosu postgres postgres --single -D "$PGDATA" "$database" <<EOSQL
GRANT ALL ON SCHEMA public TO "${APP_USER}";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "${APP_USER}";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${APP_USER}";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${APP_USER}";
EOSQL
    fi
  fi
}

run_sql postgres
run_sql "$APP_DB"
