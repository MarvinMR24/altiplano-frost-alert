FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    BACKEND_VAR_DIR=/app/var \
    ARTIFACTS_DIR=/app/artifacts

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/var/logs /app/artifacts \
    && chown -R app:app /app/var

COPY --chown=app:app app ./app

USER app
EXPOSE 8000
# Internal operations run in the same container: docker compose exec backend python -m app.cli replay --night YYYY-MM-DD
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
