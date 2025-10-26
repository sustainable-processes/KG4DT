from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from .db import get_session


def get_db() -> Generator[Session, None, None]:
    """Provide a SQLAlchemy session for request scope.

    This uses fastapi.app.db.get_session() which returns a scoped session factory.
    We ensure the session is closed after request handling.
    """
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# Alias type for dependency injection
DbSessionDep = Annotated[Session, Depends(get_db)]
