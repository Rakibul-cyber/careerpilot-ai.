# Application entrypoint.
#
# Future responsibility:
#   - Create and configure the FastAPI application instance.
#   - Register middleware (CORS, request-id, logging, error handlers).
#   - Mount the versioned API router (app.api.v1.router).
#   - Wire startup/shutdown lifecycle events (DB pool, cache, etc.).
#
# Keep this file thin: it only assembles the app. No business logic here.
