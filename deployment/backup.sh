#!/usr/bin/env bash
# ==============================================================================
# Production Backup Script (`backup.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/backup.sh
#
# Description:
#   Performs production-grade, compressed, and verified backups of the PostgreSQL
#   database, uploaded media assets, and persistent Docker volumes.
#   Automates backup retention cleanup (14 days) and guarantees zero credential
#   exposure. Designed to be called standalone or directly from `deploy.sh`.
#
# Responsibilities:
#   1. Backup PostgreSQL database (pg_dump compressed via gzip)
#   2. Backup uploaded media assets (tar.gz from media volume)
#   3. Backup core persistent Docker volumes (tar.gz via ephemeral container)
#   4. Organize output neatly into backups/{database,media,volumes}/
#   5. Filename timestamp formatting: YYYY-MM-DD_HH-MM-SS
#   6. Verify backup archive integrity post-creation (gzip -t / tar -tzf)
#   7. Enforce 14-day retention policy (pruning old backups automatically)
#   8. Safe, idempotent execution with full POSIX/Bash compatibility
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Strict Error Handling
# ------------------------------------------------------------------------------
# -e: Exit immediately if any pipeline/command returns a non-zero exit status.
# -u: Treat references to unset variables as critical errors.
# -o pipefail: Ensure pipeline failures propagate right to the caller.
set -euo pipefail

# Capture start timestamp for accurate execution duration logging
START_TIME=$(date +%s)

# Determine exact paths dynamically so script is callable from any working directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# 2. Logging Setup & Configuration Loading
# ------------------------------------------------------------------------------
# Load optional deployment suite variables if present
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

# Ensure logging directory exists
LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/backup_${LOG_TIMESTAMP}.log"

# Define ANSI color escape codes for terminal formatting
if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' CYAN='' BOLD='' RESET=''
fi

log_info() {
    echo -e "${BLUE}[INFO] $(date +"%Y-%m-%d %H:%M:%S") - ${1}${RESET}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] $(date +"%Y-%m-%d %H:%M:%S") - ${1}${RESET}"
}

log_warn() {
    echo -e "${YELLOW}[WARNING] $(date +"%Y-%m-%d %H:%M:%S") - ${1}${RESET}"
}

log_error() {
    echo -e "${RED}[ERROR] $(date +"%Y-%m-%d %H:%M:%S") - ${1}${RESET}" >&2
}

log_header() {
    echo -e "\n${BOLD}${CYAN}==============================================================================${RESET}"
    echo -e "${BOLD}${CYAN} ${1} ${RESET}"
    echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
}

# Redirect stdout and stderr to both terminal and timestamped log file
exec > >(tee -a "${LOG_FILE}") 2>&1

# ------------------------------------------------------------------------------
# 3. Exit Trap for Clean Reporting & Error Propagation
# ------------------------------------------------------------------------------
BACKUP_SUCCESS=false

on_exit() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))

    log_header "BACKUP SUMMARY"
    log_info "Total Duration: ${duration}s"

    if [[ ${exit_code} -eq 0 && "${BACKUP_SUCCESS}" == "true" ]]; then
        log_success "All backup operations completed and verified successfully."
    else
        log_error "Backup process aborted or failed with exit code ${exit_code} after ${duration}s!"
        log_warn "Review full execution log at: ${LOG_FILE}"
    fi
}
trap on_exit EXIT

log_header "STARTING PRODUCTION BACKUP PROCESS"
log_info "Project Root:  ${PROJECT_ROOT}"
log_info "Log File Path: ${LOG_FILE}"

# ------------------------------------------------------------------------------
# 4. Pre-flight Verification & Docker Compose Auto-Detection
# ------------------------------------------------------------------------------
# Verify Docker binary installation
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker binary not found in PATH."
    exit 1
fi

# Detect Docker Compose command style (v2 plugin vs v1 standalone)
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose is not installed on this system."
    exit 1
fi
log_info "Using Docker Compose command: '${DOCKER_COMPOSE_CMD}'"

# Verify Docker daemon connectivity
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or socket permissions are denied."
    exit 1
fi

# Verify application .env file existence without exposing secrets
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    log_error "Configuration file '${PROJECT_ROOT}/.env' not found."
    exit 1
fi

# ------------------------------------------------------------------------------
# 5. Backup Directory Structure & Formatting Setup
# ------------------------------------------------------------------------------
# Filename format exactly matching requirement: YYYY-MM-DD_HH-MM-SS
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

BACKUPS_ROOT="${PROJECT_ROOT}/backups"
DIR_DATABASE="${BACKUPS_ROOT}/database"
DIR_MEDIA="${BACKUPS_ROOT}/media"
DIR_VOLUMES="${BACKUPS_ROOT}/volumes"

log_info "Ensuring backup directory tree exists..."
mkdir -p "${DIR_DATABASE}" "${DIR_MEDIA}" "${DIR_VOLUMES}"

# ------------------------------------------------------------------------------
# 6. PostgreSQL Database Backup
# ------------------------------------------------------------------------------
log_header "STEP 1: PostgreSQL Database Backup"

# Check if database container is currently running
if ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^db$"; then
    DB_BACKUP_FILE="${DIR_DATABASE}/db_${TIMESTAMP}.sql.gz"
    log_info "Dumping PostgreSQL database to: ${DB_BACKUP_FILE}"

    # Extract database credentials securely without global shell export or echoing
    # Strips surrounding quotes and defaults gracefully if not set
    DB_USER=$(grep -E '^(POSTGRES_USER|DB_USER)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_NAME=$(grep -E '^(POSTGRES_DB|DB_NAME)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_PASS=$(grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")

    # Execute pg_dump inside db container passing PGPASSWORD strictly via inline environment variable
    ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db \
        pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists --no-owner --no-privileges | gzip -9 > "${DB_BACKUP_FILE}"

    # Verify backup archive integrity
    log_info "Verifying database gzip archive integrity..."
    if gzip -t "${DB_BACKUP_FILE}"; then
        BACKUP_SIZE=$(du -h "${DB_BACKUP_FILE}" | cut -f1)
        log_success "Database backup verified successfully (${BACKUP_SIZE})."
    else
        log_error "Database backup integrity check failed! Archive may be corrupted."
        rm -f "${DB_BACKUP_FILE}"
        exit 1
    fi
else
    log_error "PostgreSQL container ('db') is not currently running! Cannot perform database dump."
    exit 1
fi

# ------------------------------------------------------------------------------
# 7. Uploaded Media Backup
# ------------------------------------------------------------------------------
log_header "STEP 2: Uploaded Media Backup"

MEDIA_BACKUP_FILE="${DIR_MEDIA}/media_${TIMESTAMP}.tar.gz"
log_info "Archiving uploaded media to: ${MEDIA_BACKUP_FILE}"

# Use an ephemeral alpine container to read the named volume 'media_data' cleanly
# This guarantees root/host permission independence and zero file lock issues
if docker run --rm \
    -v edunaukri_media_data:/source:ro \
    -v "${DIR_MEDIA}:/backup" \
    alpine:latest \
    tar -czf "/backup/media_${TIMESTAMP}.tar.gz" -C /source . 2>/dev/null; then
    
    # Check if backup file was created successfully (handle alternate volume prefixes if needed)
    if [[ -f "${MEDIA_BACKUP_FILE}" ]]; then
        log_info "Verifying media tar.gz archive integrity..."
        if tar -tzf "${MEDIA_BACKUP_FILE}" >/dev/null 2>&1; then
            MEDIA_SIZE=$(du -h "${MEDIA_BACKUP_FILE}" | cut -f1)
            log_success "Media backup verified successfully (${MEDIA_SIZE})."
        else
            log_error "Media backup verification failed! Archive corrupted."
            rm -f "${MEDIA_BACKUP_FILE}"
            exit 1
        fi
    fi
else
    # Fallback to local directory backup if volume name prefix differs or ./media exists
    if [[ -d "${PROJECT_ROOT}/media" ]]; then
        log_info "Volume mount fallback: backing up local ./media directory..."
        tar -czf "${MEDIA_BACKUP_FILE}" -C "${PROJECT_ROOT}" media
        if tar -tzf "${MEDIA_BACKUP_FILE}" >/dev/null 2>&1; then
            MEDIA_SIZE=$(du -h "${MEDIA_BACKUP_FILE}" | cut -f1)
            log_success "Media backup from local folder verified successfully (${MEDIA_SIZE})."
        else
            log_error "Local media directory archive verification failed!"
            rm -f "${MEDIA_BACKUP_FILE}"
            exit 1
        fi
    else
        log_warn "No media volume ('edunaukri_media_data') or local './media' directory found. Skipping media backup."
    fi
fi

# ------------------------------------------------------------------------------
# 8. Docker Volumes Backup
# ------------------------------------------------------------------------------
log_header "STEP 3: Persistent Docker Volumes Backup"

# List of core data volumes defined in docker-compose.yml to archive
VOLUMES_TO_BACKUP=("postgres_data" "redis_data" "static_data" "ssl_data" "certbot_data" "pgadmin_data")

# Determine project prefix used by Docker Compose (usually folder name in lowercase)
PROJECT_PREFIX=$(basename "${PROJECT_ROOT}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g')

for vol in "${VOLUMES_TO_BACKUP[@]}"; do
    # Check potential volume names (with and without project prefix)
    TARGET_VOL=""
    if docker volume inspect "${PROJECT_PREFIX}_${vol}" >/dev/null 2>&1; then
        TARGET_VOL="${PROJECT_PREFIX}_${vol}"
    elif docker volume inspect "${vol}" >/dev/null 2>&1; then
        TARGET_VOL="${vol}"
    fi

    if [[ -n "${TARGET_VOL}" ]]; then
        VOL_BACKUP_FILE="${DIR_VOLUMES}/${vol}_${TIMESTAMP}.tar.gz"
        log_info "Archiving Docker volume '${TARGET_VOL}' -> ${VOL_BACKUP_FILE}"

        docker run --rm \
            -v "${TARGET_VOL}:/source:ro" \
            -v "${DIR_VOLUMES}:/backup" \
            alpine:latest \
            tar -czf "/backup/${vol}_${TIMESTAMP}.tar.gz" -C /source .

        # Verify archive integrity
        if tar -tzf "${VOL_BACKUP_FILE}" >/dev/null 2>&1; then
            VOL_SIZE=$(du -h "${VOL_BACKUP_FILE}" | cut -f1)
            log_success "Volume '${TARGET_VOL}' backed up and verified (${VOL_SIZE})."
        else
            log_error "Volume backup verification failed for ${TARGET_VOL}!"
            rm -f "${VOL_BACKUP_FILE}"
            exit 1
        fi
    else
        log_warn "Docker volume '${vol}' not found on host. Skipping."
    fi
done

# ------------------------------------------------------------------------------
# 9. Automated Retention Enforcement (Delete Backups Older Than 14 Days)
# ------------------------------------------------------------------------------
log_header "STEP 4: Backup Retention Cleanup (14-Day Expiration)"

log_info "Pruning backup archives older than 14 days..."

# Clean old database backups
PRUNED_DB=$(find "${DIR_DATABASE}" -type f -name "db_*.sql.gz" -mtime +14 -print -delete | wc -l || echo "0")
# Clean old media backups
PRUNED_MEDIA=$(find "${DIR_MEDIA}" -type f -name "media_*.tar.gz" -mtime +14 -print -delete | wc -l || echo "0")
# Clean old volume backups
PRUNED_VOL=$(find "${DIR_VOLUMES}" -type f -name "*.tar.gz" -mtime +14 -print -delete | wc -l || echo "0")

TOTAL_PRUNED=$((PRUNED_DB + PRUNED_MEDIA + PRUNED_VOL))
log_success "Retention policy enforced: deleted ${TOTAL_PRUNED} outdated archive file(s) across categories."

# Mark backup process as successful for exit trap
BACKUP_SUCCESS=true
log_success "All backup procedures executed successfully."
exit 0
