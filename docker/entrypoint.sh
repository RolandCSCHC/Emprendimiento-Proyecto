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

echo "Configurando base de datos..."
python << 'PY'
import os
import subprocess
import sys

import psycopg2

url = os.environ["DATABASE_URL"]
conn = psycopg2.connect(url)
cur = conn.cursor()

def table_exists(name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
        )
        """,
        (name,),
    )
    return cur.fetchone()[0]

def column_exists(table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s AND column_name = %s
        )
        """,
        (table, column),
    )
    return cur.fetchone()[0]

has_clases = table_exists("clases")
has_programa_id = column_exists("clases", "programa_id")
has_alembic = table_exists("alembic_version")
conn.close()

if not has_clases:
    print("Base vacía: creando tablas e insertando seed de demo...")
    subprocess.check_call(["flask", "init-db"])
    subprocess.check_call(["flask", "db", "stamp", "head"])
elif not has_programa_id:
    print("Aplicando migración programas_clase (clases recurrentes)...")
    subprocess.check_call(["flask", "db", "upgrade"])
    subprocess.check_call(["flask", "seed"])
elif not has_alembic:
    print("Marcando esquema actual como migrado...")
    subprocess.check_call(["flask", "db", "stamp", "head"])
    subprocess.check_call(["flask", "seed"])
else:
    print("Aplicando migraciones pendientes...")
    subprocess.check_call(["flask", "db", "upgrade"])
    subprocess.check_call(["flask", "seed"])
PY

echo "Iniciando Gymsight..."
exec gunicorn -b 0.0.0.0:5000 -w 2 --timeout 120 "run:app"
