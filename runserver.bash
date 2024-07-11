#!/bin/sh
set -e

cd /code/movie_library
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn -b :8080 movie_library.wsgi:application
