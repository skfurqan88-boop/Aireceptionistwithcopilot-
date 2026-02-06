#!/bin/bash
# Production startup script for AI Receptionist Backend

set -e

echo "Starting AI Receptionist Backend..."

# Wait for database to be ready (if using external database)
if [[ "$DATABASE_URL" == postgresql* ]]; then
    echo "Waiting for PostgreSQL to be ready..."
    until python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 1
    done
    echo "PostgreSQL is ready!"
fi

# Initialize database
echo "Initializing database..."
python init_db.py --business-id=${BUSINESS_ID:-default} --timezone=${BUSINESS_TIMEZONE:-UTC}

# Start application
echo "Starting Uvicorn server..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WORKERS:-1} \
    --log-level ${LOG_LEVEL:-info}
