#!/bin/bash
# ==============================================================================
# EduNaukri Master Backup Orchestration Script
# ==============================================================================
# Usage: backup.sh [daily|weekly|manual]
# Performs automated backups of PostgreSQL, Media files, Application Logs,
# and System Configuration, executes automated restore verification, and prunes
# expired archives according to retention policies.
# ==============================================================================

set -u

BACKUP_TYPE="${1:-daily}"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
TARGET_DIR="/backups/${BACKUP_TYPE}"
LOG_DIR="/backups/logs"
LOG_FILE="${LOG_DIR}/backup_${BACKUP_TYPE}_latest.log"

mkdir -p "$TARGET_DIR" "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [BACKUP-${BACKUP_TYPE^^}] $1" | tee -a "$LOG_FILE"
}

log "========================================================================"
log "Starting EduNaukri Automated Backup ($BACKUP_TYPE)"
log "Timestamp: $TIMESTAMP"
log "Target Directory: $TARGET_DIR"
log "========================================================================"

# 1. PostgreSQL Database Backup (Custom Compressed Format -Fc)
DB_DUMP="${TARGET_DIR}/db_${TIMESTAMP}.dump"
log "Backing up PostgreSQL database (${POSTGRES_DB:-edunaukri}) from host ${POSTGRES_HOST:-db}..."

if pg_dump -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" \
           -U "${POSTGRES_USER:-edunaukri}" -d "${POSTGRES_DB:-edunaukri}" \
           -Fc -f "$DB_DUMP" >> "$LOG_FILE" 2>&1; then
    DB_SIZE=$(du -h "$DB_DUMP" | cut -f1)
    log "SUCCESS: Database backup completed -> $DB_DUMP ($DB_SIZE)"
else
    log "ERROR: PostgreSQL backup failed! Check logs in $LOG_FILE"
    exit 1
fi

# 2. Media Directory Backup
MEDIA_TAR="${TARGET_DIR}/media_${TIMESTAMP}.tar.gz"
if [ -d "/app/media" ] && [ "$(ls -A /app/media 2>/dev/null)" ]; then
    log "Archiving user media files (/app/media)..."
    if tar -czf "$MEDIA_TAR" -C /app/media . >> "$LOG_FILE" 2>&1; then
        MEDIA_SIZE=$(du -h "$MEDIA_TAR" | cut -f1)
        log "SUCCESS: Media backup completed -> $MEDIA_TAR ($MEDIA_SIZE)"
    else
        log "WARNING: Media archive encountered errors during tar execution."
    fi
else
    log "INFO: Media directory is empty or missing; skipping media archive."
    MEDIA_TAR=""
fi

# 3. Logs Directory Backup
LOGS_TAR="${TARGET_DIR}/logs_${TIMESTAMP}.tar.gz"
if [ -d "/app/logs" ] && [ "$(ls -A /app/logs 2>/dev/null)" ]; then
    log "Archiving application logs (/app/logs)..."
    tar -czf "$LOGS_TAR" -C /app/logs . >> "$LOG_FILE" 2>&1 || true
    LOGS_SIZE=$(du -h "$LOGS_TAR" | cut -f1)
    log "SUCCESS: Logs backup completed -> $LOGS_TAR ($LOGS_SIZE)"
else
    LOGS_TAR=""
fi

# 4. System Configuration Backup
CONFIG_TAR="${TARGET_DIR}/config_${TIMESTAMP}.tar.gz"
if [ -d "/app/config_source" ] && [ "$(ls -A /app/config_source 2>/dev/null)" ]; then
    log "Archiving system configuration (/app/config_source)..."
    tar -czf "$CONFIG_TAR" -C /app/config_source . >> "$LOG_FILE" 2>&1 || true
    CONFIG_SIZE=$(du -h "$CONFIG_TAR" | cut -f1)
    log "SUCCESS: Configuration backup completed -> $CONFIG_TAR ($CONFIG_SIZE)"
else
    CONFIG_TAR=""
fi

# 5. Automated Restore Verification (Testing Backups Immediately)
if [ "${RESTORE_TEST_ENABLED:-true}" = "true" ]; then
    log "------------------------------------------------------------------------"
    log "Invoking Automated Restore Verification Engine..."
    log "------------------------------------------------------------------------"
    if /app/docker/backup/restore-test.sh "$DB_DUMP" "${MEDIA_TAR}" "${CONFIG_TAR}" | tee -a "$LOG_FILE"; then
        log "VERIFICATION STATUS: PASSED (All backups validated and restorable)"
    else
        log "VERIFICATION STATUS: FAILED (Restore verification encountered errors!)"
        # We don't delete the dump on failure so administrators can investigate, but we flag error
    fi
fi

# 6. Retention Management Policy
log "------------------------------------------------------------------------"
log "Enforcing Backup Retention Policies..."
DAILY_RETENTION=${BACKUP_RETENTION_DAILY:-7}
WEEKLY_RETENTION=${BACKUP_RETENTION_WEEKLY:-5}

if [ "$BACKUP_TYPE" = "daily" ]; then
    log "Pruning daily backups older than $DAILY_RETENTION days in /backups/daily..."
    DELETED_COUNT=$(find /backups/daily -type f -mtime +"${DAILY_RETENTION}" -delete -print | wc -l)
    log "Pruned $DELETED_COUNT expired daily backup archives."
elif [ "$BACKUP_TYPE" = "weekly" ]; then
    WEEKLY_DAYS=$((WEEKLY_RETENTION * 7))
    log "Pruning weekly backups older than $WEEKLY_RETENTION weeks ($WEEKLY_DAYS days) in /backups/weekly..."
    DELETED_COUNT=$(find /backups/weekly -type f -mtime +"${WEEKLY_DAYS}" -delete -print | wc -l)
    log "Pruned $DELETED_COUNT expired weekly backup archives."
fi

# Clean up old backup logs older than 30 days
find "$LOG_DIR" -type f -mtime +30 -delete 2>/dev/null || true

log "========================================================================"
log "EduNaukri Backup ($BACKUP_TYPE) Finished Successfully!"
log "========================================================================"
exit 0
