#!/usr/bin/env bash
# Copy the SQLite database out of the backend volume to ~/backups with a timestamp and keep
# the last 14 copies. Run ON THE SERVER from the repo root (manually or from cron):
#   bash deploy/scripts/backup_db.sh
# Crontab (crontab -e), daily at 03:30 server time:
#   30 3 * * * cd $HOME/altiplano-frost-alert && bash deploy/scripts/backup_db.sh >> $HOME/backups/backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/../.."
BACKUP_DIR="$HOME/backups"
KEEP=14
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/frostwatch-$STAMP.db"

# sqlite3's online backup API gives a consistent copy while the backend is running.
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod exec -T backend \
  python -c "import sqlite3; s=sqlite3.connect('/app/var/frostwatch.db'); d=sqlite3.connect('/app/var/backup.db'); s.backup(d); d.close(); s.close()"
CID="$(docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod ps -q backend)"
docker cp "$CID:/app/var/backup.db" "$OUT"
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile prod exec -T backend rm -f /app/var/backup.db
chmod 600 "$OUT"
echo "backup written: $OUT"

# Keep only the newest $KEEP backups.
ls -1t "$BACKUP_DIR"/frostwatch-*.db 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
