# Alembic model registry / discovery module.
#
# Importing this module pulls every ORM model into scope so their tables are
# registered on ``Base.metadata``. Alembic's env.py imports ``Base`` from here
# to get a fully-populated metadata for autogenerate. Add one import line per
# new model. The ``# noqa: F401`` marks the imports as intentional side effects.

from app.db.base import Base
from app.models.company import Company  # noqa: F401
from app.models.connector_run import ConnectorRun  # noqa: F401
from app.models.job import Job  # noqa: F401
from app.models.job_alert import JobAlert  # noqa: F401
from app.models.job_match import JobMatch  # noqa: F401
from app.models.resume import Resume  # noqa: F401
from app.models.resume_profile import ResumeProfile  # noqa: F401
from app.models.saved_search import SavedSearch  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["Base"]
