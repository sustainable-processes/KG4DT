"""
Initial v2 relational schema (PostgreSQL)

- Enables citext
- Creates enums basic_matter_type, basic_usage
- Creates updated-at trigger function
- Creates tables: users, projects, experiment_data, models, reactors, basics, reactor_basic_junction,
  categories, templates
- Adds constraints and indexes, including per-user case-insensitive unique project names
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251212_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS citext;")

    # Enums
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'basic_matter_type') THEN
                CREATE TYPE basic_matter_type AS ENUM ('steam','solid','gas');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'basic_usage') THEN
                CREATE TYPE basic_usage AS ENUM ('inlet','outlet','utilities');
            END IF;
        END $$;
        """
    )

    # Updated-at trigger function
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        """
    )

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False, unique=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # projects
    op.create_table(
        "projects",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"]) 
    op.execute("CREATE UNIQUE INDEX uq_projects_user_name_ci ON projects(user_id, lower(name));")
    op.execute("ALTER TABLE projects ADD CONSTRAINT ck_projects_name_not_empty CHECK (char_length(name) > 0);")
    op.execute("CREATE TRIGGER trg_projects_updated BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # experiment_data
    op.create_table(
        "experiment_data",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_experiment_data_project_id", "experiment_data", ["project_id"]) 
    op.execute("CREATE TRIGGER trg_experiment_data_updated BEFORE UPDATE ON experiment_data FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # models
    op.create_table(
        "models",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("mt", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("me", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("laws", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_models_project_id", "models", ["project_id"]) 
    op.execute("CREATE TRIGGER trg_models_updated BEFORE UPDATE ON models FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # reactors
    op.create_table(
        "reactors",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("number_of_input", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("number_of_output", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("icon_url", sa.String(length=255), nullable=True),
        sa.Column("json_data", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("chemistry", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("kinetics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute("CREATE TRIGGER trg_reactors_updated BEFORE UPDATE ON reactors FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # basics
    op.create_table(
        "basics",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("type", postgresql.ENUM("steam", "solid", "gas", name="basic_matter_type", create_type=False), nullable=False),
        sa.Column("usage", postgresql.ENUM("inlet", "outlet", "utilities", name="basic_usage", create_type=False), nullable=False),
        sa.Column("structure", sa.String(length=100), nullable=True),
        sa.Column("phase", sa.String(length=50), nullable=True),
        sa.Column("operation", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.execute("ALTER TABLE basics ADD CONSTRAINT ck_basics_name_not_empty CHECK (char_length(name) > 0);")
    op.execute("CREATE TRIGGER trg_basics_updated BEFORE UPDATE ON basics FOR EACH ROW EXECUTE FUNCTION set_updated_at();")

    # reactor_basic_junction
    op.create_table(
        "reactor_basic_junction",
        sa.Column("reactor_id", sa.BigInteger(), sa.ForeignKey("reactors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("basic_id", sa.BigInteger(), sa.ForeignKey("basics.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("association_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_reactor_basic_basic_id", "reactor_basic_junction", ["basic_id"]) 

    # categories
    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True),
    )

    # templates
    op.create_table(
        "templates",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("category_id", sa.BigInteger(), sa.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reactor_id", sa.BigInteger(), sa.ForeignKey("reactors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("category_id", "reactor_id", name="uq_templates_category_reactor"),
    )
    op.create_index("ix_templates_category_id", "templates", ["category_id"]) 
    op.create_index("ix_templates_reactor_id", "templates", ["reactor_id"]) 
    op.execute("CREATE TRIGGER trg_templates_updated BEFORE UPDATE ON templates FOR EACH ROW EXECUTE FUNCTION set_updated_at();")


def downgrade() -> None:
    # Drop in reverse order
    op.execute("DROP TRIGGER IF EXISTS trg_templates_updated ON templates;")
    op.drop_index("ix_templates_reactor_id", table_name="templates")
    op.drop_index("ix_templates_category_id", table_name="templates")
    op.drop_table("templates")

    op.drop_table("categories")

    op.drop_index("ix_reactor_basic_basic_id", table_name="reactor_basic_junction")
    op.drop_table("reactor_basic_junction")

    op.execute("DROP TRIGGER IF EXISTS trg_basics_updated ON basics;")
    op.drop_table("basics")
    op.execute("DROP TYPE IF EXISTS basic_usage;")
    op.execute("DROP TYPE IF EXISTS basic_matter_type;")

    op.execute("DROP TRIGGER IF EXISTS trg_reactors_updated ON reactors;")
    op.drop_table("reactors")

    op.execute("DROP TRIGGER IF EXISTS trg_models_updated ON models;")
    op.drop_index("ix_models_project_id", table_name="models")
    op.drop_table("models")

    op.execute("DROP TRIGGER IF EXISTS trg_experiment_data_updated ON experiment_data;")
    op.drop_index("ix_experiment_data_project_id", table_name="experiment_data")
    op.drop_table("experiment_data")

    op.execute("DROP TRIGGER IF EXISTS trg_projects_updated ON projects;")
    op.execute("DROP INDEX IF EXISTS uq_projects_user_name_ci;")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")

    op.execute("DROP TRIGGER IF EXISTS trg_users_updated ON users;")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")
