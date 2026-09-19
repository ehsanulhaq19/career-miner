#!/usr/bin/env bash
# Register (create or update) the application Postgres user on a running database.
# Defaults: admin / admin — override with POSTGRES_APP_USER / POSTGRES_APP_PASSWORD.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${DB_CONTAINER:-careerminer-db}"

export POSTGRES_APP_USER="${POSTGRES_APP_USER:-admin}"
export POSTGRES_APP_PASSWORD="${POSTGRES_APP_PASSWORD:-admin}"
export ENSURE_APP_USER_ONLINE=1

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Container '$CONTAINER' is not running." >&2
  echo "Start the stack first: docker compose -f docker-compose.prod.yml up -d db" >&2
  exit 1
fi

docker exec \
  -e POSTGRES_APP_USER \
  -e POSTGRES_APP_PASSWORD \
  -e POSTGRES_DB="${POSTGRES_DB:-careerminer}" \
  -e POSTGRES_USER="${POSTGRES_USER:-postgres}" \
  -e ENSURE_APP_USER_ONLINE=1 \
  "$CONTAINER" \
  sh /usr/local/bin/ensure-app-user.sh

echo "Verifying login as ${POSTGRES_APP_USER}..."
docker exec "$CONTAINER" psql -U "$POSTGRES_APP_USER" -d "${POSTGRES_DB:-careerminer}" -c "SELECT current_user, current_database();"

echo "Done. Set backend/.env to:"
echo "DATABASE_URL=postgresql+asyncpg://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@db:5432/${POSTGRES_DB:-careerminer}"
