#!/bin/sh
set -eu

if [ -z "${POSTGRES_TELEGRAM_DB:-}" ] || [ "$POSTGRES_TELEGRAM_DB" = "$POSTGRES_DB" ]; then
    exit 0
fi

psql \
    --username "$POSTGRES_USER" \
    --dbname "$POSTGRES_DB" \
    --set=db_name="$POSTGRES_TELEGRAM_DB" \
    --set=ON_ERROR_STOP=1 <<-'EOSQL'
SELECT 'CREATE DATABASE ' || quote_ident(:'db_name')
WHERE NOT EXISTS (
    SELECT FROM pg_database WHERE datname = :'db_name'
)\gexec
EOSQL
