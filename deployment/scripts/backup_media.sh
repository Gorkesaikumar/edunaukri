#!/bin/bash

set -Eeuo pipefail

###############################################
# EduNaukri Media Backup Script
###############################################

MEDIA_DIR="/var/lib/docker/volumes/edunaukri_media_data/_data"

LOG_DIR="deployment/backups/media/logs"

LOG_FILE="${LOG_DIR}/media_backup_$(date +%F).log"

REMOTE="gdrive:EduNaukri-Backups/media"

mkdir -p "$LOG_DIR"

echo "==========================================" | tee -a "$LOG_FILE"
echo "EduNaukri Media Backup Started" | tee -a "$LOG_FILE"
echo "Started : $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

if [ ! -d "$MEDIA_DIR" ]; then
    echo "Media folder not found: $MEDIA_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

for folder in "$MEDIA_DIR"/*; do

    if [ -d "$folder" ]; then

        FOLDER_NAME=$(basename "$folder")

        echo "" | tee -a "$LOG_FILE"
        echo "------------------------------------------" | tee -a "$LOG_FILE"
        echo "Syncing : $FOLDER_NAME" | tee -a "$LOG_FILE"

        rclone sync \
            "$folder" \
            "${REMOTE}/${FOLDER_NAME}" \
            --progress \
            --create-empty-src-dirs

        echo "Completed : $FOLDER_NAME" | tee -a "$LOG_FILE"

    fi

done

echo "" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "Media Backup Completed Successfully." | tee -a "$LOG_FILE"
echo "Finished : $(date)" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
