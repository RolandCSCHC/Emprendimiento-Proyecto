#!/bin/sh
# Restaura gymsight_demo.sql en Docker Postgres (esquema antiguo) y aplica la
# migración programas_clase. Requiere una base limpia: recrea la DB gymsight.
set -e

DUMP="${1:-gymsight_demo.sql}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$ROOT/$DUMP" ] && [ ! -f "$DUMP" ]; then
  echo "No se encontró el dump: $DUMP"
  exit 1
fi

DUMP_PATH="$DUMP"
if [ -f "$ROOT/$DUMP" ]; then
  DUMP_PATH="$ROOT/$DUMP"
fi

cd "$ROOT"

echo "Levantando Postgres..."
docker compose up -d db

echo "Esperando a Postgres..."
until docker compose exec -T db pg_isready -U gymsight -d gymsight >/dev/null 2>&1; do
  sleep 1
done

echo "Deteniendo web (libera conexiones a la base)..."
docker compose stop web 2>/dev/null || true

echo "Recreando base de datos gymsight..."
docker compose exec -T db psql -U gymsight -d postgres <<'SQL'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'gymsight' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS gymsight;
CREATE DATABASE gymsight OWNER gymsight;
SQL

echo "Restaurando dump..."
docker compose exec -T db psql -U gymsight -d gymsight < "$DUMP_PATH"

echo "Aplicando migración programas_clase..."
docker compose up -d web
sleep 3
docker compose exec web flask db upgrade

echo ""
echo "Listo. App en http://localhost:5001/dashboard/"
