"""
Rename reactors.icon_url -> reactors.icon

This drops the legacy column name and standardizes on `icon` everywhere.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = "20251219_0003"
down_revision = "20251215_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL supports simple rename via ALTER TABLE ... RENAME COLUMN ...
    op.alter_column("reactors", "icon_url", new_column_name="icon")


def downgrade() -> None:
    op.alter_column("reactors", "icon", new_column_name="icon_url")
