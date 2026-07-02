# Declarative base for all ORM models.
# Models will subclass Base and be imported here later for Alembic autogenerate.

from sqlalchemy.orm import declarative_base

Base = declarative_base()
