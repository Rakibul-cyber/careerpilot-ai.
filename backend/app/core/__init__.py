# core package.
#
# Cross-cutting infrastructure concerns, free of any business logic:
#   - config.py     -> Pydantic Settings loaded from environment/.env.
#   - security.py   -> password hashing, JWT creation/verification.
#   - logging.py    -> structured logging configuration.
#   - exceptions.py -> shared application/domain exception types.
#
# These modules are added as the application grows.
