# Dependencies only. Code and data are bind mounted by docker-compose (service "ml").
# No default command: run on demand with `docker compose run --rm ml python pipelines/...`.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /work

COPY ml/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
