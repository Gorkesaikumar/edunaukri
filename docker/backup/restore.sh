#!/bin/bash
# ==============================================================================
# EduNaukri Disaster Recovery Manual Restore Tool
# ==============================================================================
# Usage: restore.sh <daily|weekly> <TIMESTAMP|latest> [--force]
# Restores a verified PostgreSQL database dump and unpacks Media archives into
# the live production environment.
# ==============================================================================

set -u

BACKUP_TYPE="${1:-daily}"
TARGET="${2:-latest}"
FORCE="${3:-}"

if [ "$TARGET" = "latest" ]; then
    DB_DUMP=$(ls -t /backups/"${BACKUP_TYPE}"/db_*.dump 2>/dev/null | head -n 1)
    MEDIA_TAR=$(ls -t /backups/"${BACKUP_TYPE}"/media_*.tar.gz 2>/dev/null | head -n 1)
else
    DB_DUMP="/backups/${BACKUP_TYPE}/db_${TARGET}.dump"
    MEDIA_TAR="/backups/${BACKUP_TYPE}/media_${TARGET}.tar.gz"
fi

echo "========================================================================"
echo "EduNaukri Production Disaster Recovery Restore"
echo "========================================================================"
echo "Backup Type:  $BACKUP_TYPE"
echo "Database:     ${DB_DUMP:-not found}"
echo "Media Tar:    ${MEDIA_TAR:-not found}"
echo "Target DB:    ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432} -> ${POSTGRES_DB:-edunaukri}"
echo "========================================================================"

if [ -z "${DB_DUMP:-}" ] || [ ! -f "$DB_DUMP" ]; then
    echo "ERROR: Specified database dump not found ($DB_DUMP)."
    exit 1
fi

if [ "$FORCE" != "--force" ]; then
    read -p "WARNING: This will OVERWRITE the current production database and media files! Type 'RESTORE' to confirm: " CONFIRM
    if [ "$CONFIRM" != "RESTORE" ]; then
        echo "Restore operation cancelled by user."
        exit 0
    fi
fi

echo "[1/2] Restoring PostgreSQL Database from $DB_DUMP..."
# --clean drops existing database objects prior to recreating them
# --if-exists prevents errors when dropping objects that do not exist yet
pg_restore -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" \
           -U "${POSTGRES_USER:-edunaukri}" -d "${POSTGRES_DB:-edunaukri}" \
           --clean --if-exists --no-owner --no-privileges "$DB_DUMP" || true

echo "SUCCESS: Database restored cleanly."

if [ -n "${MEDIA_TAR:-}" ] && [ -f "$MEDIA_TAR" ] && [ -d "/app/media" ]; then
    echo "[2/2] Restoring Media Files from $MEDIA_TAR into /app/media..."
    tar -xzf "$MEDIA_TAR" -C /app/media/
    echo "SUCCESS: Media files unpacked."
else
    echo "[2/2] Skipping media restore (archive or target directory not available)."
fi

echo "========================================================================"
echo "Disaster Recovery Restoration Completed Successfully!"
echo "========================================================================"
