from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers, used by Alembic.
revision = "20251215_0002"
down_revision = "20251212_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert text/varchar columns to JSONB, preserving NULL/empty as NULL
    op.alter_column(
        "basics",
        "structure",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="CASE WHEN structure IS NULL OR btrim(structure) = '' THEN NULL ELSE structure::jsonb END",
        existing_nullable=True,
    )
    op.alter_column(
        "basics",
        "phase",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="CASE WHEN phase IS NULL OR btrim(phase) = '' THEN NULL ELSE phase::jsonb END",
        existing_nullable=True,
    )
    op.alter_column(
        "basics",
        "operation",
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using="CASE WHEN operation IS NULL OR btrim(operation) = '' THEN NULL ELSE operation::jsonb END",
        existing_nullable=True,
    )


def downgrade() -> None:
    # Convert JSONB back to text with original lengths
    op.alter_column(
        "basics",
        "structure",
        type_=sa.String(length=100),
        postgresql_using="structure::text",
        existing_nullable=True,
    )
    op.alter_column(
        "basics",
        "phase",
        type_=sa.String(length=50),
        postgresql_using="phase::text",
        existing_nullable=True,
    )
    op.alter_column(
        "basics",
        "operation",
        type_=sa.String(length=50),
        postgresql_using="operation::text",
        existing_nullable=True,
    )
