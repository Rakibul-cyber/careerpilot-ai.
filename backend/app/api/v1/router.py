# v1 aggregate router.
#
# Future responsibility:
#   - Import every endpoint module from app.api.v1.endpoints.
#   - Combine them into a single APIRouter and expose it as `api_router`.
#   - main.py includes this router under the /api/v1 prefix.
#
# This file is the single place that declares which endpoints exist in v1.
