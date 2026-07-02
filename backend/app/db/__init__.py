# db package.
#
# Database plumbing:
#   - base.py    -> declarative Base + model imports for Alembic autogenerate.
#   - session.py -> async engine and session factory / get_db() dependency.
#
# Alembic migrations (in ../../infra or a top-level alembic/) target Base.metadata
# defined here. No queries or business logic live in this package.
