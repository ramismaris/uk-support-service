"""initial schema

Revision ID: 5d6d04856100
Revises:
Create Date: 2026-09-25 15:16:59.909334

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5d6d04856100"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM("CLIENT", "MANAGER", "ADMIN", name="user_role", create_type=False)
ticket_type = postgresql.ENUM("REQUEST", "QUESTION", name="ticket_type", create_type=False)
ticket_status = postgresql.ENUM(
    "NEW",
    "IN_PROGRESS",
    "WAITING_CLIENT",
    "CLOSED",
    "REJECTED",
    name="ticket_status",
    create_type=False,
)
ticket_priority = postgresql.ENUM("NORMAL", "URGENT", name="ticket_priority", create_type=False)
sender_type = postgresql.ENUM("CLIENT", "STAFF", "SYSTEM", name="sender_type", create_type=False)

ENUM_TYPES = (user_role, ticket_type, ticket_status, ticket_priority, sender_type)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in ENUM_TYPES:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "buildings",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_buildings")),
        sa.UniqueConstraint("address", name=op.f("uq_buildings_address")),
        sa.UniqueConstraint("external_id", name=op.f("uq_buildings_external_id")),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categories")),
        sa.UniqueConstraint("title", name=op.f("uq_categories_title")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("max_user_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.Text(), nullable=False),
        sa.Column("last_name", sa.Text(), nullable=True),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("role", user_role, server_default="CLIENT", nullable=False),
        sa.Column("is_blocked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("active_ticket_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("max_user_id", name=op.f("uq_users_max_user_id")),
    )
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_tokens_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_tokens_token_hash")),
    )
    op.create_table(
        "content_blocks",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["users.id"], name=op.f("fk_content_blocks_updated_by_id_users")
        ),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_content_blocks")),
    )
    op.create_table(
        "login_tokens",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_login_tokens_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_login_tokens_token_hash")),
    )
    op.create_table(
        "residences",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("building_id", sa.BigInteger(), nullable=False),
        sa.Column("apartment", sa.Text(), nullable=False),
        sa.Column("account_number", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["building_id"], ["buildings.id"], name=op.f("fk_residences_building_id_buildings")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_residences_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_residences")),
        sa.UniqueConstraint(
            "user_id", "building_id", "apartment", name="uq_residences_user_building_apartment"
        ),
    )
    op.create_index(
        "uq_residences_primary_per_user",
        "residences",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.create_table(
        "tickets",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True, start=1000), nullable=False),
        sa.Column("type", ticket_type, nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("priority", ticket_priority, server_default="NORMAL", nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=False),
        sa.Column("assignee_id", sa.BigInteger(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("building_id", sa.BigInteger(), nullable=True),
        sa.Column("apartment", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("contact_phone", sa.Text(), nullable=True),
        sa.Column("preferred_time", sa.Text(), nullable=True),
        sa.Column("status_message_max_id", sa.Text(), nullable=True),
        sa.Column("last_client_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type = 'QUESTION' OR (building_id IS NOT NULL AND apartment IS NOT NULL "
            "AND category_id IS NOT NULL)",
            name=op.f("ck_tickets_request_has_address"),
        ),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name=op.f("ck_tickets_rating_range")),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name=op.f("fk_tickets_assignee_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["building_id"], ["buildings.id"], name=op.f("fk_tickets_building_id_buildings")
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("fk_tickets_category_id_categories")
        ),
        sa.ForeignKeyConstraint(
            ["client_id"], ["users.id"], name=op.f("fk_tickets_client_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tickets")),
    )
    op.create_index(op.f("ix_tickets_assignee_id"), "tickets", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_tickets_building_id"), "tickets", ["building_id"], unique=False)
    op.create_index(op.f("ix_tickets_client_id"), "tickets", ["client_id"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    op.create_foreign_key(
        op.f("fk_users_active_ticket_id_tickets"),
        "users",
        "tickets",
        ["active_ticket_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_type", sender_type, nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("max_message_id", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_messages_author_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_messages_ticket_id_tickets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(
        op.f("ix_messages_max_message_id"), "messages", ["max_message_id"], unique=False
    )
    op.create_table(
        "status_changes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("from_status", ticket_status, nullable=True),
        sa.Column("to_status", ticket_status, nullable=False),
        sa.Column("changed_by_id", sa.BigInteger(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_id"], ["users.id"], name=op.f("fk_status_changes_changed_by_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_status_changes_ticket_id_tickets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_status_changes")),
    )
    op.create_table(
        "ticket_triage",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("suggested_category_id", sa.BigInteger(), nullable=True),
        sa.Column("urgency", ticket_priority, nullable=False),
        sa.Column("is_relevant", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("raw", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("overridden_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["suggested_category_id"],
            ["categories.id"],
            name=op.f("fk_ticket_triage_suggested_category_id_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_ticket_triage_ticket_id_tickets")
        ),
        sa.PrimaryKeyConstraint("ticket_id", name=op.f("pk_ticket_triage")),
    )
    op.create_table(
        "files",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("mime", sa.Text(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=True),
        sa.Column("max_token", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], name=op.f("fk_files_message_id_messages")
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"], ["tickets.id"], name=op.f("fk_files_ticket_id_tickets")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_files")),
    )


def downgrade() -> None:
    op.drop_table("files")
    op.drop_table("ticket_triage")
    op.drop_table("status_changes")
    op.drop_index(op.f("ix_messages_max_message_id"), table_name="messages")
    op.drop_table("messages")
    op.drop_constraint(op.f("fk_users_active_ticket_id_tickets"), "users", type_="foreignkey")
    op.drop_index(op.f("ix_tickets_client_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_building_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_assignee_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("uq_residences_primary_per_user", table_name="residences")
    op.drop_table("residences")
    op.drop_table("login_tokens")
    op.drop_table("content_blocks")
    op.drop_table("auth_tokens")
    op.drop_table("users")
    op.drop_table("categories")
    op.drop_table("buildings")

    bind = op.get_bind()
    for enum_type in ENUM_TYPES:
        enum_type.drop(bind, checkfirst=True)
