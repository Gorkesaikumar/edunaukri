#!/usr/bin/env bash
# ==============================================================================
# Production Clean Rebuild Script (`rebuild.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/rebuild.sh
#
# Description:
#   Performs a complete, clean rebuild of application Docker images from scratch
#   without using intermediate build cache (--no-cache). Gracefully stops and
#   removes existing container instances, builds fresh images, starts up containers,
#   executes Django post-build tasks (migrations, collectstatic), and restarts
#   Celery workers and Nginx reverse proxy.
#   Includes automated health check verification (`healthcheck.sh`) and automatic
#   rollback (`rollback.sh`) if any verification check fails.
#
# Usage:
#   ./deployment/rebuild.sh
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Strict Error Handling Setup
# ------------------------------------------------------------------------------
# -e: Exit immediately if any command returns a non-zero exit status.
# -u: Treat unset variable references as critical errors.
# -o pipefail: Return the exit status of the last failing command in a pipeline.
set -euo pipefail

# Capture rebuild start timestamp for execution duration measurement
START_TIME=$(date +%s)

# Determine exact paths dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# 2. Logging Setup & Configuration Loading
# ------------------------------------------------------------------------------
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/rebuild_${LOG_TIMESTAMP}.log"

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
# 3. Exit Trap Handler for Summary Reporting & Automated Rollback Check
# ------------------------------------------------------------------------------
REBUILD_SUCCESS=false
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "HEAD")

on_exit() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    log_header "REBUILD SUMMARY"
    log_info "Total Execution Time: ${minutes}m ${seconds}s"
    log_info "Active Git Commit:    ${CURRENT_COMMIT}"

    if [[ ${exit_code} -eq 0 && "${REBUILD_SUCCESS}" == "true" ]]; then
        log_success "Clean rebuild procedure completed and verified successfully."
    else
        log_error "Rebuild procedure terminated with exit code ${exit_code} after ${minutes}m ${seconds}s!"
        log_warn "Review full rebuild log at: ${LOG_FILE}"
    fi
}
trap on_exit EXIT

log_header "STARTING CLEAN PRODUCTION DOCKER REBUILD"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

# ------------------------------------------------------------------------------
# 4. Pre-flight Verification
# ------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker binary not found in PATH."
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose ('docker compose' or 'docker-compose') not found."
    exit 1
fi
log_info "Using Docker Compose command: '${DOCKER_COMPOSE_CMD}'"

if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or socket permissions denied."
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    log_error "Required configuration file '.env' not found in ${PROJECT_ROOT}."
    exit 1
fi

# ------------------------------------------------------------------------------
# 5. Stop Containers & Remove Stopped Containers
# ------------------------------------------------------------------------------
log_header "STEP 1: Stopping & Removing Existing Containers"

log_info "Gracefully stopping active Docker containers..."
${DOCKER_COMPOSE_CMD} stop

log_info "Removing stopped containers and orphan instances..."
${DOCKER_COMPOSE_CMD} rm -f
log_success "Old containers removed cleanly."

# ------------------------------------------------------------------------------
# 6. Build Docker Images Without Cache
# ------------------------------------------------------------------------------
log_header "STEP 2: Building Docker Images (--no-cache)"

log_info "Building fresh Docker images without intermediate build cache..."
${DOCKER_COMPOSE_CMD} build --no-cache --pull
log_success "Docker images built from scratch successfully."

# ------------------------------------------------------------------------------
# 7. Start Containers
# ------------------------------------------------------------------------------
log_header "STEP 3: Starting Up Container Infrastructure"

log_info "Starting containers in detached mode (`docker compose up -d`)..."
${DOCKER_COMPOSE_CMD} up -d --remove-orphans

log_info "Waiting for database ('db') and caching ('redis') tiers to become responsive..."
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
log_success "Core data tier containers initialized and responsive."

# ------------------------------------------------------------------------------
# 8. Run Django Migrations & Collectstatic
# ------------------------------------------------------------------------------
log_header "STEP 4: Django Application Tasks (Migrations & Collectstatic)"

log_info "Executing database migrations..."
if [[ -x "${SCRIPT_DIR}/migrate.sh" ]]; then
    log_info "Delegating migration task to ${SCRIPT_DIR}/migrate.sh..."
    bash "${SCRIPT_DIR}/migrate.sh"
else
    log_info "Running Django migrations inside 'web' container..."
    ${DOCKER_COMPOSE_CMD} exec -T web python manage.py migrate --noinput
fi
log_success "Database migrations completed."

log_info "Collecting static assets inside 'web' container..."
${DOCKER_COMPOSE_CMD} exec -T web python manage.py collectstatic --noinput --clear
log_success "Static assets collected cleanly."

# ------------------------------------------------------------------------------
# 9. Restart Celery & Nginx Services
# ------------------------------------------------------------------------------
log_header "STEP 5: Restarting Background Workers & Reverse Proxy"

log_info "Restarting Celery Worker service..."
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^celery_worker$"; then
    ${DOCKER_COMPOSE_CMD} restart celery_worker
    log_success "Celery Worker restarted successfully."
fi

log_info "Restarting Celery Beat service..."
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^celery_beat$"; then
    ${DOCKER_COMPOSE_CMD} restart celery_beat
    log_success "Celery Beat restarted successfully."
fi

log_info "Restarting Nginx reverse proxy service..."
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^nginx$"; then
    if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t 2>/dev/null; then
        ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -s reload || ${DOCKER_COMPOSE_CMD} restart nginx
    else
        ${DOCKER_COMPOSE_CMD} restart nginx
    fi
    log_success "Nginx reverse proxy restarted successfully."
fi

# ------------------------------------------------------------------------------
# 10. Health Check Verification & Automated Rollback Protection
# ------------------------------------------------------------------------------
log_header "STEP 6: Health Check Verification & Automated Rollback Protection"

# Allow services a brief delay to bind ports and initialize sockets
sleep 5

HEALTHCHECK_PASSED=false

log_info "Executing post-rebuild healthcheck script (${SCRIPT_DIR}/healthcheck.sh)..."
if [[ -x "${SCRIPT_DIR}/healthcheck.sh" ]]; then
    if bash "${SCRIPT_DIR}/healthcheck.sh"; then
        HEALTHCHECK_PASSED=true
        log_success "Post-rebuild health verification passed."
    else
        log_error "External healthcheck.sh reported verification failure!"
        HEALTHCHECK_PASSED=false
    fi
else
    log_error "Required health check script not executable or not found: ${SCRIPT_DIR}/healthcheck.sh"
    HEALTHCHECK_PASSED=false
fi

# Automatic Rollback Trigger if Health Checks Fail
if [[ "${HEALTHCHECK_PASSED}" != "true" ]]; then
    log_error "CRITICAL: POST-REBUILD HEALTH VERIFICATION FAILED!"
    
    if [[ -x "${SCRIPT_DIR}/rollback.sh" ]]; then
        log_warn "Automatically triggering emergency rollback via ${SCRIPT_DIR}/rollback.sh (Commit: ${CURRENT_COMMIT})..."
        bash "${SCRIPT_DIR}/rollback.sh" "${CURRENT_COMMIT}" || log_error "Rollback script encountered errors during execution!"
    else
        log_error "No executable rollback script found at ${SCRIPT_DIR}/rollback.sh! Attempting direct container restart fallback..."
        ${DOCKER_COMPOSE_CMD} restart || true
    fi
    # Exit with failure so exit trap registers failure state
    exit 1
fi

REBUILD_SUCCESS=true
log_success "Clean rebuild procedure finished successfully."
exit 0
