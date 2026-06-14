"""Add programas_clase and link clases to programa.

Revision ID: 001_programas_clase
Revises:
Create Date: 2026-06-14

"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "001_programas_clase"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "programas_clase",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gimnasio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profesor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_clase_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("sala", sa.String(length=100), nullable=True),
        sa.Column("nivel", sa.String(length=50), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["gimnasio_id"], ["gimnasios.id"]),
        sa.ForeignKeyConstraint(["profesor_id"], ["profesores.id"]),
        sa.ForeignKeyConstraint(["tipo_clase_id"], ["tipos_clase.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "clases",
        sa.Column("programa_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    conn = op.get_bind()
    clases = conn.execute(
        sa.text(
            """
            SELECT id, gimnasio_id, profesor_id, tipo_clase_id, nombre, sala, nivel, notas
            FROM clases
            """
        )
    ).fetchall()

    for clase in clases:
        programa_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO programas_clase
                    (id, gimnasio_id, profesor_id, tipo_clase_id, nombre, sala, nivel, notas, activo)
                VALUES
                    (:id, :gimnasio_id, :profesor_id, :tipo_clase_id, :nombre, :sala, :nivel, :notas, true)
                """
            ),
            {
                "id": programa_id,
                "gimnasio_id": clase.gimnasio_id,
                "profesor_id": clase.profesor_id,
                "tipo_clase_id": clase.tipo_clase_id,
                "nombre": clase.nombre,
                "sala": clase.sala,
                "nivel": clase.nivel,
                "notas": clase.notas,
            },
        )
        conn.execute(
            sa.text("UPDATE clases SET programa_id = :programa_id WHERE id = :clase_id"),
            {"programa_id": programa_id, "clase_id": clase.id},
        )

    op.alter_column("clases", "programa_id", nullable=False)
    op.create_foreign_key(
        "fk_clases_programa_id",
        "clases",
        "programas_clase",
        ["programa_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_clases_programa_id", "clases", type_="foreignkey")
    op.drop_column("clases", "programa_id")
    op.drop_table("programas_clase")
