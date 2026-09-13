#!/bin/sh
set -e

echo "Running migrations..."
python manage.py migrate --noinput

echo "Running fill_db..."
python manage.py fill_db

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting gunicorn..."
exec gunicorn HotelProject.wsgi:application --bind 0.0.0.0:8000 --access-logfile - --error-logfile -
