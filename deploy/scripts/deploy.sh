#!/usr/bin/env bash
# Deploy or update the backend. Run ON THE SERVER from the repo root:
#   bash deploy/scripts/deploy.sh
# Pulls the latest code, rebuilds and restarts backend and Caddy with the prod files,
# prunes old images and checks https://$DOMAIN/health.
set -euo pipefail

cd "$(dirname "$0")/../.."
if [[ ! -f .env ]]; then
  echo ".env missing: upload it from your Mac with deploy/scripts/sync_env.sh" >&2
  exit 1
fi
if [[ ! -f artifacts/model_card.json ]]; then
  echo "artifacts/ is empty: upload it from your Mac with deploy/scripts/sync_artifacts.sh" >&2
  exit 1
fi
DOMAIN="$(grep -E '^DOMAIN=' .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")"
if [[ -z "$DOMAIN" ]]; then
  echo "DOMAIN is empty in .env" >&2
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod)

git pull --ff-only
"${COMPOSE[@]}" up -d --build --remove-orphans
docker image prune -f > /dev/null

echo "== waiting for https://$DOMAIN/health"
for _ in $(seq 1 30); do
  if body="$(curl -fsS --max-time 5 "https://$DOMAIN/health")"; then
    echo "health: $body"
    "${COMPOSE[@]}" ps
    exit 0
  fi
  sleep 4
done
echo "health check failed; recent logs:" >&2
"${COMPOSE[@]}" logs --tail 60 backend caddy >&2
exit 1
