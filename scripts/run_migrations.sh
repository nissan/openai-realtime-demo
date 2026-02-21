#!/bin/bash
# Run database migrations against local Supabase PostgreSQL
# Usage: ./scripts/run_migrations.sh
# Requires: PostgreSQL client (psql) or Docker

set -e

PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
PGDATABASE="${PGDATABASE:-postgres}"

export PGPASSWORD

echo "Running migrations against ${PGHOST}:${PGPORT}/${PGDATABASE}"
echo "Waiting for database to be ready..."

# Wait for postgres to accept connections
for i in $(seq 1 30); do
    if psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -c "SELECT 1" > /dev/null 2>&1; then
        echo "Database ready."
        break
    fi
    echo "  Attempt $i/30..."
    sleep 2
done

echo "Applying 001_shared_schema.sql..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$(dirname "$0")/../db/migrations/001_shared_schema.sql" \
    -v ON_ERROR_STOP=0 2>&1 | grep -v "already exists" || true

echo "Applying 002_version_b_jobs.sql..."
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
    -f "$(dirname "$0")/../db/migrations/002_version_b_jobs.sql" \
    -v ON_ERROR_STOP=0 2>&1 | grep -v "already exists" || true

echo "Migrations complete."
