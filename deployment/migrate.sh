#!/usr/bin/env bash
# ==============================================================================
# Production Migration & Static Asset Script (`migrate.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/migrate.sh
#
# Description:
#   Orchestrates Django database migration management and static asset collection
#   inside the active Docker environment (`web` container).
#   Checks for migration graph conflicts and pending model changes, applies
#   migrations safely, reports unapplied migration plans, collects static files,
#   and outputs comprehensive migration summaries.
#
# Responsibilities:
#   1. Check migration conflicts and pending model changes (`makemigrations --check`)
#   2. Run `makemigrations` (`--noinput`) safely
#   3. Detect and display unapplied migrations (`showmigrations --plan`)
#   4. Run `migrate` (`--noinput`) to apply database schema updates
#   5. Run `collectstatic` (`--noinput --clear`) for frontend/proxy delivery
#   6. Display comprehensive post-migration summary
#   7. Exit immediately on any failure with detailed error logging
#
# Usage:
#   ./deployment/migrate.sh
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Error Handling Setup
# ------------------------------------------------------------------------------
# -e: Exit immediately if any command returns a non-zero status.
# -u: Treat references to unset variables as errors.
# -o pipefail: Ensure pipeline failures propagate to the return value.
set -euo pipefail

# Determine script and project root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# ------------------------------------------------------------------------------
# 2. Logging Setup
# ------------------------------------------------------------------------------
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/migrate_${LOG_TIMESTAMP}.log"

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
# 3. Exit Trap for Summary Reporting
# ------------------------------------------------------------------------------
MIGRATE_SUCCESS=false
START_TIME=$(date +%s)

on_exit() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))

    log_header "MIGRATION SUMMARY"
    log_info "Execution Duration: ${duration}s"

    if [[ ${exit_code} -eq 0 && "${MIGRATE_SUCCESS}" == "true" ]]; then
        log_success "All Django migrations and static assets processed and verified successfully."
    else
        log_error "Migration procedure terminated with exit status ${exit_code} after ${duration}s!"
        log_warn "Review full migration log at: ${LOG_FILE}"
    fi
}
trap on_exit EXIT

log_header "STARTING DJANGO PRODUCTION MIGRATION & ASSET COLLECTION"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

# ------------------------------------------------------------------------------
# 4. Pre-flight Verification & Container Detection
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
    log_error "Docker daemon is not running or socket access denied."
    exit 1
fi

# Verify 'web' container is actively running
if ! ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^web$"; then
    log_error "Django application container ('web') is NOT running! Cannot execute management commands."
    exit 1
fi
log_success "Django application container ('web') is active and ready."

# ------------------------------------------------------------------------------
# 5. Check Migration Conflicts & Pending Model Changes
# ------------------------------------------------------------------------------
log_header "STEP 1: Checking Migration Graph & Conflicts"

log_info "Checking for uncreated model changes and graph inconsistencies (--check --dry-run)..."
# makemigrations --check exits with code 1 if uncreated migrations exist or if graph has conflicts
if ! ${DOCKER_COMPOSE_CMD} exec -T web python manage.py makemigrations --check --dry-run >/dev/null 2>&1; then
    log_warn "Uncreated model modifications detected or migration graph requires updates!"
else
    log_success "Migration graph checked: no uncreated migrations or merge conflicts detected."
fi

# ------------------------------------------------------------------------------
# 6. Run makemigrations
# ------------------------------------------------------------------------------
log_header "STEP 2: Generating New Migrations (makemigrations)"

log_info "Running makemigrations inside 'web' container (`--noinput`)..."
if ! ${DOCKER_COMPOSE_CMD} exec -T web python manage.py makemigrations --noinput; then
    log_error "makemigrations command failed! Check model definitions and syntax."
    exit 1
fi
log_success "makemigrations completed successfully."

# ------------------------------------------------------------------------------
# 7. Detect Unapplied Migrations
# ------------------------------------------------------------------------------
log_header "STEP 3: Detecting Unapplied Migrations"

log_info "Scanning database schema against available migration files..."
UNAPPLIED_PLAN=$(${DOCKER_COMPOSE_CMD} exec -T web python manage.py showmigrations --plan 2>/dev/null | grep '\[ \]' || echo "")

if [[ -n "${UNAPPLIED_PLAN}" && "${UNAPPLIED_PLAN}" != "" ]]; then
    UNAPPLIED_COUNT=$(echo "${UNAPPLIED_PLAN}" | wc -l | tr -d ' ')
    log_warn "Detected ${UNAPPLIED_COUNT} unapplied database migration(s) scheduled for execution:"
    echo -e "${YELLOW}${UNAPPLIED_PLAN}${RESET}"
else
    log_info "No unapplied migrations found. All existing migration files are currently applied."
fi

# ------------------------------------------------------------------------------
# 8. Run migrate
# ------------------------------------------------------------------------------
log_header "STEP 4: Applying Database Migrations (migrate)"

log_info "Executing database schema migrations (`python manage.py migrate --noinput`)..."
if ! ${DOCKER_COMPOSE_CMD} exec -T web python manage.py migrate --noinput; then
    log_error "Database migration failed during execution! Check database connection and SQL constraints."
    exit 1
fi
log_success "Database migrations applied and committed successfully."

# ------------------------------------------------------------------------------
# 9. Run collectstatic
# ------------------------------------------------------------------------------
log_header "STEP 5: Collecting Static Assets (collectstatic)"

log_info "Collecting application static assets (`python manage.py collectstatic --noinput --clear`)..."
if ! ${DOCKER_COMPOSE_CMD} exec -T web python manage.py collectstatic --noinput --clear; then
    log_error "collectstatic encountered errors during asset processing!"
    exit 1
fi
log_success "Static assets collected and synced to shared volume cleanly."

# ------------------------------------------------------------------------------
# 10. Show Post-Migration Summary
# ------------------------------------------------------------------------------
log_header "STEP 6: Post-Migration Status Summary"

log_info "Querying complete migration status across all installed apps (`showmigrations`)..."
# Display full migration graph status showing applied [X] vs unapplied [ ]
${DOCKER_COMPOSE_CMD} exec -T web python manage.py showmigrations || log_warn "Could not fetch full migration tree."

# Double check that no migrations remain unapplied
REMAINING_UNAPPLIED=$(${DOCKER_COMPOSE_CMD} exec -T web python manage.py showmigrations --plan 2>/dev/null | grep '\[ \]' || echo "")
if [[ -n "${REMAINING_UNAPPLIED}" && "${REMAINING_UNAPPLIED}" != "" ]]; then
    log_error "Post-verification failure: Some migrations remained unapplied after running migrate!"
    echo -e "${RED}${REMAINING_UNAPPLIED}${RESET}"
    exit 1
fi

MIGRATE_SUCCESS=true
log_success "All database schemas and static files verified and up-to-date."
exit 0
