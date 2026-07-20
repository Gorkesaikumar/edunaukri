#!/bin/bash

set -Eeuo pipefail

###############################################
# EduNaukri Database Backup Script
###############################################

PROJECT_NAME="EduNaukri"

POSTGRES_CONTAINER="edunaukri-db-1"
POSTGRES_DB="edunaukari"
POSTGRES_USER="edunaukari"

LOCAL_BACKUP_DIR="deployment/backups/database/local"
LOG_DIR="deployment/backups/database/logs"

GDRIVE_REMOTE="gdrive:EduNaukri-Backups/database"

DATE=$(date +"%Y-%m-%d")
TIME=$(date +"%H-%M-%S")
YEAR=$(date +"%Y")
MONTH=$(date +"%m")

BACKUP_NAME="${POSTGRES_DB}_${DATE}_${TIME}.sql"
BACKUP_FILE="${LOCAL_BACKUP_DIR}/${BACKUP_NAME}"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

LOG_FILE="${LOG_DIR}/database_backup_${DATE}.log"

mkdir -p "$LOCAL_BACKUP_DIR"
mkdir -p "$LOG_DIR"

echo "===================================" | tee -a "$LOG_FILE"
echo "Database Backup Started : $(date)" | tee -a "$LOG_FILE"
echo "===================================" | tee -a "$LOG_FILE"

echo "[1/5] Creating PostgreSQL dump..." | tee -a "$LOG_FILE"

docker exec "$POSTGRES_CONTAINER" \
    pg_dump \
    -U "$POSTGRES_USER" \
    "$POSTGRES_DB" \
    > "$BACKUP_FILE"

echo "[2/5] Compressing backup..." | tee -a "$LOG_FILE"

gzip -f "$BACKUP_FILE"

echo "[3/5] Creating remote directory..." | tee -a "$LOG_FILE"

rclone mkdir "${GDRIVE_REMOTE}/${YEAR}/${MONTH}"

echo "[4/5] Uploading backup..." | tee -a "$LOG_FILE"

rclone copy \
    "$COMPRESSED_FILE" \
    "${GDRIVE_REMOTE}/${YEAR}/${MONTH}" \
    --progress

echo "[5/5] Verifying upload..." | tee -a "$LOG_FILE"

FILE_NAME=$(basename "$COMPRESSED_FILE")

if rclone ls "${GDRIVE_REMOTE}/${YEAR}/${MONTH}" | grep -q "$FILE_NAME"; then
    echo "✔ Upload Successful" | tee -a "$LOG_FILE"
else
    echo "✘ Upload Failed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "" | tee -a "$LOG_FILE"
echo "Database Backup Completed Successfully." | tee -a "$LOG_FILE"
echo "Finished : $(date)" | tee -a "$LOG_FILE"

find "$LOCAL_BACKUP_DIR" -type f -name "*.gz" -mtime +7 -delete

echo "Old Local Backups Cleaned." | tee -a "$LOG_FILE"

echo "===================================" | tee -a "$LOG_FILE"
