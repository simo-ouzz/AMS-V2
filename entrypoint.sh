#!/bin/sh
# =============================================================================
# inventotrackV2 - Entrypoint Script
# Handles database migrations and superuser creation
# =============================================================================

set -e

echo "=========================================="
echo "inventotrackV2 - Starting..."
echo "=========================================="

# Environment variables with defaults
DB_HOST=${DB_HOST:-ams_postgres}
DB_NAME=${DB_NAME:-amstest}
DB_USER=${DB_USER:-postgres}
DB_PASSWORD=${DB_PASSWORD:-root}
DB_PORT=${DB_PORT:-5432}

echo "Waiting for database at $DB_HOST:$DB_PORT..."

# Wait for database to be ready with better error handling
max_attempts=60
attempt=1

while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts: Checking database..."
    
    # Try to connect using Python
    if python -c "
import psycopg2
import os
conn = psycopg2.connect(
    host='$DB_HOST',
    database='$DB_NAME',
    user='$DB_USER',
    password='$DB_PASSWORD',
    port='$DB_PORT',
    connect_timeout=5
)
conn.close()
" 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    
    echo "Database is unavailable - sleeping 2s (attempt $attempt/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -gt $max_attempts ]; then
    echo "ERROR: Database connection failed after $max_attempts attempts!"
    echo "Exiting..."
    exit 1
fi

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput || echo "Migration warning (continuing anyway)..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "Collectstatic warning (continuing anyway)..."

# Create superuser if not exists
DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-admin123}
DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com}

echo "Setting up superuser: $DJANGO_SUPERUSER_USERNAME"

# Create superuser if not exists
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser(
        username='$DJANGO_SUPERUSER_USERNAME',
        email='$DJANGO_SUPERUSER_EMAIL',
        password='$DJANGO_SUPERUSER_PASSWORD'
    )
    print('Superuser created successfully')
else:
    user = User.objects.get(username='$DJANGO_SUPERUSER_USERNAME')
    user.set_password('$DJANGO_SUPERUSER_PASSWORD')
    user.save()
    print('Superuser password updated')
" 2>/dev/null || echo "Superuser setup warning (continuing anyway)..."

echo "=========================================="
echo "Startup complete!"
echo "=========================================="

# Execute the main command (gunicorn)
exec "$@"
