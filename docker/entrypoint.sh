#!/bin/sh
set -e

echo "Esperando a PostgreSQL..."
until python -c "
import os
import sys
import psycopg2
try:
    psycopg2.connect(os.environ['DATABASE_URL'])
except Exception:
    sys.exit(1)
"; do
  sleep 2
done

echo "Inicializando base de datos..."
flask init-db

echo "Iniciando Gymsight..."
exec gunicorn -b 0.0.0.0:5000 -w 2 --timeout 120 "run:app"
