# CareerPilot AI backend container image.
# Production-oriented runtime: no reload, no source mount, non-root user.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-cache-dir -r requirements.txt


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:${PATH}"

WORKDIR /app

RUN addgroup --system careerpilot && \
    adduser --system --ingroup careerpilot --home /app careerpilot && \
    mkdir -p /app/uploads && \
    chown -R careerpilot:careerpilot /app

COPY --from=builder /install /usr/local
COPY --chown=careerpilot:careerpilot app ./app
COPY --chown=careerpilot:careerpilot alembic ./alembic
COPY --chown=careerpilot:careerpilot alembic.ini ./alembic.ini

USER careerpilot

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2"]
