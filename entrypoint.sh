#!/bin/sh
python manage.py collectstatic --noinput
python manage.py migrate
if [ "$DEBUG" = "true" ]; then
  exec python manage.py runserver 0.0.0.0:8000
else
  exec gunicorn config.wsgi:application -b 0.0.0.0:8000 -w 4
fi
