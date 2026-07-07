#!/bin/bash
# prestart.sh

# This script ensures the application waits for the database to accept connections
# before attempting to run migrations or start the Uvicorn web server.

set -e

echo "Running environment validation and startup checks..."

# We assume POSTGRES_SERVER is set in Docker or CI
host=${POSTGRES_SERVER:-localhost}
port=${POSTGRES_PORT:-5432}

echo "Waiting for PostgreSQL at $host:$port to become healthy..."

# Optional: Using pure bash to check TCP port if nc is unavailable
while ! < /dev/tcp/$host/$port; do
  sleep 1
done

echo "Database is accepting TCP connections. Proceeding to application logic."
