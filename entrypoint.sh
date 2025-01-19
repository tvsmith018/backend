#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "waiting on database"

    while ! nc -z $DB_HOST $DB_PORT; do
        sleep 0.1
    done
fi

# python manage.py flush --no-input
# python manage.py makemigrations user articles
# python manage.py migrate

exec "$@"