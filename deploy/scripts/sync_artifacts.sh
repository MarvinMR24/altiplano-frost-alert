#!/usr/bin/env bash
# Copy the serving artifacts (model card, coefficients, one prediction file per night) to
# the server. artifacts/ is gitignored, so git pull never brings them.
# Run from your Mac at the repo root:
#   deploy/scripts/sync_artifacts.sh ubuntu@<elastic-ip> [--dry-run] [remote_repo_dir]
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <user@host> [--dry-run] [remote_repo_dir (default: ~/altiplano-frost-alert)]" >&2
  exit 1
fi
TARGET="$1"; shift
DRY=""
if [[ "${1:-}" == "--dry-run" ]]; then DRY="--dry-run"; shift; fi
REMOTE_DIR="${1:-altiplano-frost-alert}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
if [[ ! -f "$ROOT/artifacts/model_card.json" ]]; then
  echo "artifacts/model_card.json not found: run 'make serving' first" >&2
  exit 1
fi

# --delete keeps the server copy identical; .gitkeep stays because it exists locally too.
rsync -az --delete --stats $DRY "$ROOT/artifacts/" "$TARGET:$REMOTE_DIR/artifacts/"
echo "artifacts synced to $TARGET:$REMOTE_DIR/artifacts/ ${DRY:+(dry run, nothing copied)}"
