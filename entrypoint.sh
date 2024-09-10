#!/bin/sh
function postgres_ready(){
    python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        dbname="${DB_NAME}",
        user="${DB_USER}",
        password="${DB_PASSWORD}",
        host="${DB_HOST}",
        port="${DB_PORT}"
    )
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

until postgres_ready; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

python manage.py collectstatic --noinput
python manage.py migrate
if [ "$DEBUG" = "true" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn config.wsgi:application -b 0.0.0.0:8000 -w 4
fi
