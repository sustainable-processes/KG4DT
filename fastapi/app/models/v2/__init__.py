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


class V2Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


__all__ = ["V2Base", "naming_convention"]
