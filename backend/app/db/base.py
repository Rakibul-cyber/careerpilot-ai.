# Declarative base for all ORM models (SQLAlchemy 2.x style).
#
# This module defines ONLY ``Base`` and imports no models, so it can be safely
# imported from model modules without creating a circular import. Model
# discovery for Alembic lives in ``app.db.base_all``.

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
