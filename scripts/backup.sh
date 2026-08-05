#!/usr/bin/env bash
# Kunlik PostgreSQL zaxira nusxa
set -euo pipefail
STAMP=$(date +%Y%m%d_%H%M%S)
OUT_DIR=${BACKUP_DIR:-./backups}
mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/fjsti_id_$STAMP.sql.gz"
docker compose exec -T db pg_dump -U fjsti fjsti_id | gzip > "$FILE"
echo "Backup: $FILE"
# 14 kundan eski fayllarni o'chirish
find "$OUT_DIR" -name 'fjsti_id_*.sql.gz' -mtime +14 -delete 2>/dev/null || true
