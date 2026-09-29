"""add broadcasts

Revision ID: 1a198b4feeae
Revises: 098751bec64c
Create Date: 2026-09-29 22:23:19.348777

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "1a198b4feeae"
down_revision: str | None = "098751bec64c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

broadcast_status = postgresql.ENUM(
    "SENDING", "DONE", "INTERRUPTED", name="broadcast_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    broadcast_status.create(bind, checkfirst=True)

    op.create_table(
        "broadcasts",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("file_id", sa.BigInteger(), nullable=True),
        sa.Column("status", broadcast_status, nullable=False),
        sa.Column("recipients_total", sa.Integer(), nullable=False),
        sa.Column("delivered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_broadcasts_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["file_id"], ["files.id"], name=op.f("fk_broadcasts_file_id_files")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_broadcasts")),
    )
    op.create_index(
        "uq_broadcasts_single_sending",
        "broadcasts",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'SENDING'"),
    )
    op.create_table(
        "broadcast_buildings",
        sa.Column("broadcast_id", sa.BigInteger(), nullable=False),
        sa.Column("building_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["broadcast_id"],
            ["broadcasts.id"],
            name=op.f("fk_broadcast_buildings_broadcast_id_broadcasts"),
        ),
        sa.ForeignKeyConstraint(
            ["building_id"],
            ["buildings.id"],
            name=op.f("fk_broadcast_buildings_building_id_buildings"),
        ),
        sa.PrimaryKeyConstraint("broadcast_id", "building_id", name=op.f("pk_broadcast_buildings")),
    )


def downgrade() -> None:
    op.drop_table("broadcast_buildings")
    op.drop_index(
        "uq_broadcasts_single_sending",
        table_name="broadcasts",
        postgresql_where=sa.text("status = 'SENDING'"),
    )
    op.drop_table("broadcasts")

    bind = op.get_bind()
    broadcast_status.drop(bind, checkfirst=True)
