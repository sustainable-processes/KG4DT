from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# Dedicated Base/metadata for the v2 relational schema (plural snake_case)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class V1Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)

# Re-export ORM models for convenient imports (e.g., `import ..models as m`).
from .user import User  # noqa: E402
from .project import Project  # noqa: E402
from .experiment_data import ExperimentData  # noqa: E402
from .model import Model  # noqa: E402
from .reactor import Reactor  # noqa: E402
from .basic import Basic, BasicMatterType, BasicUsageEnum  # noqa: E402
from .reactor_basic_junction import ReactorBasicJunction  # noqa: E402
from .category import Category  # noqa: E402
from .template import Template  # noqa: E402

__all__ = [
    "V1Base",
    "naming_convention",
    # Models
    "User",
    "Project",
    "ExperimentData",
    "Model",
    "Reactor",
    "Basic",
    "BasicMatterType",
    "BasicUsageEnum",
    "ReactorBasicJunction",
    "Category",
    "Template",
]
