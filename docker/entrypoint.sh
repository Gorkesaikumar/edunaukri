#!/bin/bash
set -e

wait_for_service() {
    host="$1"
    port="$2"
    name="$3"
    retries=30

    echo "Waiting for ${name} at ${host}:${port}..."
    for i in $(seq 1 $retries); do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "${name} is available."
            return 0
        fi
        sleep 2
    done
    echo "Timed out waiting for ${name} after ${retries} attempts."
    exit 1
}

# Wait for PostgreSQL
if [ -n "${DB_HOST:-}" ] && [ -n "${DB_PORT:-}" ]; then
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL"
fi

# Wait for Redis (robust URL parsing supporting authentication and custom ports)
if [ -n "${REDIS_URL:-}" ]; then
    # Extract host by stripping scheme, credentials, and port/path
    REDIS_HOST=$(echo "$REDIS_URL" | sed -E 's|^[^:]+://([^@]+@)?([^:/]+).*|\2|')
    # Extract port or default to 6379
    REDIS_PORT=$(echo "$REDIS_URL" | sed -nE 's|^[^:]+://([^@]+@)?[^:/]+:([0-9]+).*|\2|p')
    REDIS_PORT=${REDIS_PORT:-6379}
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis"
fi

echo "Running database migrations..."
python manage.py migrate --noinput

if [ "${DJANGO_SETTINGS_MODULE}" = "config.settings.production" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput --clear
fi

exec "$@"
