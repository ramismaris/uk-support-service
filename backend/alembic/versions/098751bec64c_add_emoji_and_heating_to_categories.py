"""add emoji and heating to categories

Revision ID: 098751bec64c
Revises: 5d6d04856100
Create Date: 2026-09-29 15:21:10.356508

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "098751bec64c"
down_revision: str | None = "5d6d04856100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (old title, new title, new sort_order, old sort_order)
CATEGORY_TITLES = [
    ("Сантехника", "🚰 Сантехника", 1, 1),
    ("Электрика", "⚡️ Электрика", 2, 2),
    ("Лифт", "🛗 Лифт", 3, 3),
    ("Отопление", "🔥 Отопление", 4, 7),
    ("Уборка", "🧹 Уборка", 5, 4),
    ("Благоустройство", "🌳 Благоустройство", 6, 5),
    ("Другое", "❓ Другое", 7, 6),
]

UPDATE_TITLE = sa.text(
    "UPDATE categories SET title = :new_title, sort_order = :sort_order WHERE title = :old_title"
)

# A seeded database gets the new category here; an empty one (a fresh install) gets all
# seven from the seed.
INSERT_HEATING = sa.text(
    "INSERT INTO categories (title, sort_order) "
    "SELECT :title, :sort_order "
    "WHERE EXISTS (SELECT 1 FROM categories) "
    "AND NOT EXISTS (SELECT 1 FROM categories WHERE title = :title)"
)


def upgrade() -> None:
    for old_title, new_title, new_order, _ in CATEGORY_TITLES:
        op.execute(
            UPDATE_TITLE.bindparams(old_title=old_title, new_title=new_title, sort_order=new_order)
        )
    op.execute(INSERT_HEATING.bindparams(title="🔥 Отопление", sort_order=4))


def downgrade() -> None:
    # Do not delete "Отопление": tickets may already reference it.
    for old_title, new_title, _, old_order in CATEGORY_TITLES:
        op.execute(
            UPDATE_TITLE.bindparams(old_title=new_title, new_title=old_title, sort_order=old_order)
        )
