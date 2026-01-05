from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = "20251219_0004"
down_revision = "20251215_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add surrogate primary key column `id` with a sequence for existing rows
    op.execute("CREATE SEQUENCE IF NOT EXISTS reactor_basic_junction_id_seq;")
    op.add_column(
        "reactor_basic_junction",
        sa.Column("id", sa.BigInteger(), server_default=sa.text("nextval('reactor_basic_junction_id_seq')"), nullable=True),
    )

    # Populate id for existing rows
    op.execute(
        "UPDATE reactor_basic_junction SET id = nextval('reactor_basic_junction_id_seq') WHERE id IS NULL;"
    )

    # Drop existing composite primary key (reactor_id, basic_id)
    op.drop_constraint("reactor_basic_junction_pkey", "reactor_basic_junction", type_="primary")

    # Create new primary key on id
    op.create_primary_key(
        "pk_reactor_basic_junction", "reactor_basic_junction", ["id"],
    )

    # Ensure id is not null going forward
    op.alter_column("reactor_basic_junction", "id", nullable=False)

    # Set id default owned by table
    op.execute(
        "ALTER SEQUENCE reactor_basic_junction_id_seq OWNED BY reactor_basic_junction.id;"
    )


def downgrade() -> None:
    # Recreate composite primary key (may fail if duplicate pairs exist)
    op.drop_constraint("pk_reactor_basic_junction", "reactor_basic_junction", type_="primary")
    op.create_primary_key(
        "reactor_basic_junction_pkey", "reactor_basic_junction", ["reactor_id", "basic_id"]
    )

    # Drop id column and its sequence
    op.drop_column("reactor_basic_junction", "id")
    op.execute("DROP SEQUENCE IF EXISTS reactor_basic_junction_id_seq;")
