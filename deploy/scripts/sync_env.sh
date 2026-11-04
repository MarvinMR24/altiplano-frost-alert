#!/usr/bin/env bash
# Upload .env.production (on your Mac, gitignored) to the server as the repo's .env, mode 600.
# The file content is never printed.
# Run from your Mac at the repo root:
#   deploy/scripts/sync_env.sh ubuntu@<elastic-ip> [remote_repo_dir]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <user@host> [remote_repo_dir (default: ~/altiplano-frost-alert)]" >&2
  exit 1
fi
TARGET="$1"
REMOTE_DIR="${2:-altiplano-frost-alert}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/.env.production"

if [[ ! -f "$SRC" ]]; then
  echo ".env.production not found: copy .env.production.example and fill it in" >&2
  exit 1
fi
# Refuse obviously incomplete files (names only are checked, values are not shown).
for name in APP_ENV DOMAIN PUBLIC_BASE_URL SESSION_SECRET DATA_PROVIDER EMAIL_PROVIDER; do
  if ! grep -Eq "^${name}=.+" "$SRC"; then
    echo "$name is empty in .env.production" >&2
    exit 1
  fi
done

ssh "$TARGET" "umask 077 && mkdir -p '$REMOTE_DIR'"
scp -q "$SRC" "$TARGET:$REMOTE_DIR/.env"
ssh "$TARGET" "chmod 600 '$REMOTE_DIR/.env'"
echo "uploaded .env.production to $TARGET:$REMOTE_DIR/.env (mode 600)"
