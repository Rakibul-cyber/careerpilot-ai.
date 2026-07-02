# Shared FastAPI dependency providers for the API layer.
#
# get_db already lives in app.db.session; it is re-exported here so endpoints
# have a single import point for dependencies. Service providers are wired here
# too, keeping construction out of the route handlers.

from app.db.session import get_db  # noqa: F401  (re-exported dependency)
from app.services.user_service import UserService


def get_user_service() -> UserService:
    return UserService()
