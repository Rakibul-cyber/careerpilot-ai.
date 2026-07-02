# models package.
# SQLAlchemy ORM entities that map to PostgreSQL tables (the persistence layer).
# One module per aggregate/entity (e.g. user.py, resume.py, job_application.py).
# These represent database state only — kept separate from Pydantic schemas so the
# storage model and the API contract can evolve independently.
