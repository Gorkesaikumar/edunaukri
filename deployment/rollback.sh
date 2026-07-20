#!/usr/bin/env bash
# ==============================================================================
# Production Rollback Script (`rollback.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/rollback.sh
#
# Description:
#   Automatically restores the previous known-good deployment state. Safely stops
#   running containers, reverts Git repository to a previous commit/tag, rebuilds
#   Docker images, restarts containers, and optionally restores the PostgreSQL
#   database from a snapshot without ever deleting or mutating backup archives.
#   Performs comprehensive health verification and outputs detailed diagnostics
#   upon any failure.
#
# Usage:
#   ./deployment/rollback.sh [TARGET_COMMIT] [--restore-db [BACKUP_FILE_PATH]]
#
# Examples:
#   ./deployment/rollback.sh                       # Rollback to HEAD~1
#   ./deployment/rollback.sh a1b2c3d               # Rollback to specific commit
#   ./deployment/rollback.sh --restore-db          # Rollback HEAD~1 + latest DB backup
#   ./deployment/rollback.sh v1.2.0 --restore-db backups/database/db_2026-07-18_20-00-00.sql.gz
#
# Workflow:
#   1. Pre-flight checks & target resolution (Git ref & optional DB backup file)
#   2. Gracefully stop running containers (`docker compose stop` / `down`)
#   3. Restore target Git commit (`git reset --hard` / `checkout`)
#   4. Rebuild application Docker images (`docker compose build`)
#   5. Restart container infrastructure (`docker compose up -d`)
#   6. Restore previous PostgreSQL backup (if requested via --restore-db)
#   7. Verify application health check endpoints and reverse proxy
#   8. Execute detailed diagnostics (`docker compose logs`, `ps`) if rollback fails
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Strict Error Handling
# ------------------------------------------------------------------------------
# -e: Exit immediately if any command exits with a non-zero status.
# -u: Treat unset variable references as fatal errors during substitution.
# -o pipefail: Propagate pipeline failures to the return value of the pipeline.
set -euo pipefail

# Capture rollback execution start timestamp for duration measurement
START_TIME=$(date +%s)

# Determine exact paths dynamically so script works from any current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# 2. Argument Parsing & Configuration
# ------------------------------------------------------------------------------
TARGET_COMMIT=""
RESTORE_DB=false
DB_BACKUP_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --restore-db)
            RESTORE_DB=true
            # Check if next argument is a specific backup file path
            if [[ $# -gt 1 && "$2" != -* && ! "$2" =~ ^[0-9a-f]{7,40}$ && -f "$2" ]]; then
                DB_BACKUP_FILE="$2"
                shift 2
            elif [[ $# -gt 1 && -f "${PROJECT_ROOT}/$2" ]]; then
                DB_BACKUP_FILE="${PROJECT_ROOT}/$2"
                shift 2
            else
                shift
            fi
            ;;
        -*)
            echo "Unknown option: $1" >&2
            echo "Usage: $0 [TARGET_COMMIT] [--restore-db [BACKUP_FILE_PATH]]" >&2
            exit 1
            ;;
        *)
            if [[ -z "${TARGET_COMMIT}" ]]; then
                TARGET_COMMIT="$1"
                shift
            else
                echo "Unexpected argument: $1" >&2
                echo "Usage: $0 [TARGET_COMMIT] [--restore-db [BACKUP_FILE_PATH]]" >&2
                exit 1
            fi
            ;;
    esac
done

# If no commit specified, default to previous commit in history (`HEAD~1`)
if [[ -z "${TARGET_COMMIT}" ]]; then
    # Try reflog first if available (`HEAD@{1}`), otherwise default to `HEAD~1`
    if git rev-parse --verify HEAD@{1} >/dev/null 2>&1; then
        TARGET_COMMIT=$(git rev-parse --short HEAD@{1})
    else
        TARGET_COMMIT="HEAD~1"
    fi
fi

# ------------------------------------------------------------------------------
# 3. Logging Setup
# ------------------------------------------------------------------------------
# Load optional deployment environment overrides
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

# Ensure rollback logs directory exists
LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/rollback_${LOG_TIMESTAMP}.log"

# ANSI Color formatting codes
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

# Redirect all stdout and stderr streams to both terminal and timestamped log file
exec > >(tee -a "${LOG_FILE}") 2>&1

# ------------------------------------------------------------------------------
# 4. Diagnostics & Summary Trap Handler
# ------------------------------------------------------------------------------
ROLLBACK_SUCCESS=false

print_diagnostics() {
    log_header "CRITICAL DIAGNOSTICS & DEBUG OUTPUT"
    log_warn "Rollback did not complete successfully. Dumping environment state..."

    echo -e "\n${BOLD}1. Docker Container Status:${RESET}"
    ${DOCKER_COMPOSE_CMD} ps --all || echo "Failed to query container state."

    echo -e "\n${BOLD}2. Recent Logs from Web & Celery Services (last 60 lines):${RESET}"
    ${DOCKER_COMPOSE_CMD} logs --tail=60 web celery_worker celery_beat nginx 2>/dev/null || echo "Failed to fetch service logs."

    echo -e "\n${BOLD}3. Database & Caching Tier Health Check Status:${RESET}"
    for svc in db redis; do
        if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^${svc}$"; then
            echo -n "Service [${svc}] status: "
            ${DOCKER_COMPOSE_CMD} ps --format json "${svc}" 2>/dev/null | grep -o '"Health": *"[^"]*"' || echo "No health status / running"
        fi
    done

    echo -e "\n${BOLD}4. Host Disk Space Status:${RESET}"
    df -h / || echo "Failed to check disk space."
}

on_exit() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    log_header "ROLLBACK SUMMARY"
    log_info "Total Execution Time: ${minutes}m ${seconds}s"
    log_info "Target Git Ref:       ${TARGET_COMMIT}"
    log_info "Database Restore:     ${RESTORE_DB} (${DB_BACKUP_FILE:-none})"

    if [[ ${exit_code} -eq 0 && "${ROLLBACK_SUCCESS}" == "true" ]]; then
        log_success "Rollback procedure completed and verified successfully. Previous deployment restored."
    else
        log_error "Rollback FAILED with exit code ${exit_code} after ${minutes}m ${seconds}s!"
        print_diagnostics
        log_warn "Detailed rollback execution and diagnostic logs saved to: ${LOG_FILE}"
    fi
}
trap on_exit EXIT

log_header "STARTING PRODUCTION ROLLBACK PROCEDURE"
log_info "Project Root:      ${PROJECT_ROOT}"
log_info "Log File:          ${LOG_FILE}"
log_info "Target Git Commit: ${TARGET_COMMIT}"
log_info "Restore Database:  ${RESTORE_DB}"

# ------------------------------------------------------------------------------
# 5. Pre-flight Verification & Auto-Detection
# ------------------------------------------------------------------------------
# Verify Git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log_error "Project root (${PROJECT_ROOT}) is not a Git repository."
    exit 1
fi

# Verify target commit exists in repository history
if ! git rev-parse --verify "${TARGET_COMMIT}^{commit}" >/dev/null 2>&1; then
    log_error "Target Git reference '${TARGET_COMMIT}' cannot be resolved to a valid commit!"
    exit 1
fi
RESOLVED_COMMIT=$(git rev-parse "${TARGET_COMMIT}")
log_info "Resolved target commit to: ${RESOLVED_COMMIT} ($(git log -1 --format="%h - %s (%an)" "${RESOLVED_COMMIT}"))"

# Verify Docker binary
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker executable not found in PATH."
    exit 1
fi

# Verify Docker Compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Neither 'docker compose' nor 'docker-compose' found."
    exit 1
fi
log_info "Docker Compose command: '${DOCKER_COMPOSE_CMD}'"

# Verify Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or socket access is denied."
    exit 1
fi

# Verify .env file exists
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    log_error "Configuration file '${PROJECT_ROOT}/.env' not found."
    exit 1
fi

# If database restore requested without explicit file, auto-detect latest DB backup
if [[ "${RESTORE_DB}" == "true" && -z "${DB_BACKUP_FILE}" ]]; then
    log_info "No explicit backup file specified for --restore-db. Searching for latest database backup..."
    LATEST_BACKUP=$(find "${PROJECT_ROOT}/backups/database" -maxdepth 1 -type f -name "db_*.sql.gz" 2>/dev/null | sort -r | head -n 1 || echo "")
    if [[ -z "${LATEST_BACKUP}" ]]; then
        log_error "No database backup archives (db_*.sql.gz) found inside ${PROJECT_ROOT}/backups/database/! Cannot perform DB restore."
        exit 1
    fi
    DB_BACKUP_FILE="${LATEST_BACKUP}"
fi

if [[ "${RESTORE_DB}" == "true" ]]; then
    if [[ ! -f "${DB_BACKUP_FILE}" ]]; then
        log_error "Specified database backup file does not exist: ${DB_BACKUP_FILE}"
        exit 1
    fi
    log_info "Selected database backup snapshot for restore: ${DB_BACKUP_FILE}"
fi

# ------------------------------------------------------------------------------
# 6. Stop Running Containers
# ------------------------------------------------------------------------------
log_header "STEP 1: Stopping Active Containers"

log_info "Gracefully stopping running Docker containers..."
# Use down to clean up application containers and release ports before git reset
${DOCKER_COMPOSE_CMD} down --remove-orphans
log_success "All active application containers stopped."

# ------------------------------------------------------------------------------
# 7. Restore Previous Git Commit
# ------------------------------------------------------------------------------
log_header "STEP 2: Restoring Previous Git Commit"

CURRENT_COMMIT=$(git rev-parse HEAD)
log_info "Reverting working directory from ${CURRENT_COMMIT} -> ${RESOLVED_COMMIT}..."

# Reset hard to target commit cleanly without deleting git-ignored `.env` or `backups/`
git reset --hard "${RESOLVED_COMMIT}"
git clean -fd -e .env -e backups -e logs -e media -e staticfiles || true

log_success "Git repository restored to commit: $(git log -1 --format="%h - %s")"

# ------------------------------------------------------------------------------
# 8. Rebuild Docker Images
# ------------------------------------------------------------------------------
log_header "STEP 3: Rebuilding Application Docker Images"

log_info "Building Docker images for restored commit (${RESOLVED_COMMIT})..."
${DOCKER_COMPOSE_CMD} build --pull
log_success "Docker images built successfully for target commit."

# ------------------------------------------------------------------------------
# 9. Restart Containers
# ------------------------------------------------------------------------------
log_header "STEP 4: Restarting Container Infrastructure"

log_info "Starting up services (`docker compose up -d`)..."
${DOCKER_COMPOSE_CMD} up -d --remove-orphans

log_info "Waiting for core data tier ('db' & 'redis') to become responsive..."
for svc in db redis; do
    if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^${svc}$"; then
        attempt=0
        while [ $attempt -le 15 ]; do
            STATUS=$(${DOCKER_COMPOSE_CMD} ps --format json "${svc}" 2>/dev/null | grep -o '"Health": *"[^"]*"' | cut -d'"' -f4 || echo "running")
            if [[ -z "${STATUS}" || "${STATUS}" == "running" || "${STATUS}" == "healthy" ]]; then
                break
            fi
            sleep 4
            attempt=$((attempt + 1))
        done
    fi
done
log_success "Core containers initialized and running."

# ------------------------------------------------------------------------------
# 10. Restore Previous Database Backup (If Requested)
# ------------------------------------------------------------------------------
if [[ "${RESTORE_DB}" == "true" ]]; then
    log_header "STEP 5: Restoring Previous PostgreSQL Database Snapshot"

    # Extract database connection variables securely without printing secrets
    DB_USER=$(grep -E '^(POSTGRES_USER|DB_USER)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_NAME=$(grep -E '^(POSTGRES_DB|DB_NAME)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_PASS=$(grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")

    log_warn "IMPORTANT: Restoring database from archive ${DB_BACKUP_FILE}. This will overwrite current database state!"
    log_info "Terminating active database connections before restore..."
    ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}" -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true

    # IMPORTANT: Never delete backups! Read archive cleanly via gunzip/zcat and pipe directly into psql
    log_info "Streaming gzip archive directly into PostgreSQL database ('${DB_NAME}')..."
    if [[ "${DB_BACKUP_FILE}" =~ \.gz$ ]]; then
        gzip -dc "${DB_BACKUP_FILE}" | ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 >/dev/null
    else
        cat "${DB_BACKUP_FILE}" | ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}" -v ON_ERROR_STOP=1 >/dev/null
    fi

    log_success "Database successfully restored from snapshot (${DB_BACKUP_FILE})."

    # Restart application workers to drop cached DB connections/schemas after restore
    log_info "Restarting web and worker services after database restore..."
    ${DOCKER_COMPOSE_CMD} restart web celery_worker celery_beat || true
fi

# ------------------------------------------------------------------------------
# 11. Health Verification
# ------------------------------------------------------------------------------
log_header "STEP 6: Verifying Health Endpoints & Application Stability"

# Allow services a few seconds to warm up and bind sockets after startup/restore
sleep 5

HEALTH_OK=true

# Check if external healthcheck script is available
if [[ -x "${SCRIPT_DIR}/healthcheck.sh" ]]; then
    log_info "Calling external healthcheck script (${SCRIPT_DIR}/healthcheck.sh)..."
    if ! bash "${SCRIPT_DIR}/healthcheck.sh"; then
        log_error "External healthcheck.sh reported verification failure!"
        HEALTH_OK=false
    fi
else
    log_info "Performing internal HTTP and container health verification..."

    # 1. Check Django Web Service HTTP endpoint
    if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^web$"; then
        log_info "Probing Django web server health endpoint (http://localhost:8000/api/v1/health/)..."
        if ! ${DOCKER_COMPOSE_CMD} exec -T web python -c "
import urllib.request, sys
try:
    resp = urllib.request.urlopen('http://localhost:8000/api/v1/health/', timeout=10)
    sys.exit(0 if resp.getcode() in [200, 301, 302] else 1)
except Exception:
    try:
        resp = urllib.request.urlopen('http://localhost:8000/', timeout=10)
        sys.exit(0 if resp.getcode() < 500 else 1)
    except Exception as e:
        print(f'HTTP probe error: {e}', file=sys.stderr)
        sys.exit(1)
"; then
            log_error "Django web application failed HTTP endpoint check!"
            HEALTH_OK=false
        else
            log_success "Django web application responded with healthy status code."
        fi
    fi

    # 2. Check Celery Worker responsiveness
    if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^celery_worker$"; then
        log_info "Verifying Celery Worker connectivity..."
        if ! ${DOCKER_COMPOSE_CMD} exec -T celery_worker celery -A config inspect ping -d "celery@\$(hostname)" >/dev/null 2>&1; then
            log_warn "Celery inspect ping timed out (worker may still be warming up)."
        else
            log_success "Celery Worker is active and accepting tasks."
        fi
    fi

    # 3. Check Nginx Reverse Proxy syntax and running status
    if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^nginx$"; then
        if ! ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t >/dev/null 2>&1; then
            log_error "Nginx container reported runtime syntax/config error!"
            HEALTH_OK=false
        else
            log_success "Nginx proxy configuration verified."
        fi
    fi
fi

if [[ "${HEALTH_OK}" != "true" ]]; then
    log_error "Health verification checks failed after rollback execution!"
    exit 1
fi

ROLLBACK_SUCCESS=true
log_success "Rollback procedure completed successfully. System is stable at commit ${TARGET_COMMIT}."
exit 0
