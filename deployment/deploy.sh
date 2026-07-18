#!/usr/bin/env bash
# ==============================================================================
# Main Production Deployment Script (`deploy.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/ (modular deployment suite)
#
# Description:
#   Orchestrates automated, zero-downtime/low-downtime deployments on a production
#   Ubuntu VPS using Docker Compose. Integrates seamlessly with modular companion
#   scripts (backup.sh, migrate.sh, healthcheck.sh, rollback.sh, permissions.sh).
#
# Usage:
#   ./deployment/deploy.sh [--force|-f]
#
# Workflow:
#   1. Pre-flight verification (Git repo, Docker daemon, compose, .env, .deployment.env)
#   2. Script permissions check & optional permissions.sh execution
#   3. Pre-deployment database backup calling backup.sh
#   4. Git fetch & pull with HEAD diff detection (exits cleanly if no changes unless -f)
#   5. Build Docker images & recreate ONLY affected containers
#   6. Django migrations (via migrate.sh or direct manage.py) & collectstatic
#   7. Restart Celery Worker, Celery Beat, and Nginx (if config changed)
#   8. Execute healthcheck.sh with automated rollback (`rollback.sh`) upon failure
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Error Handling
# ------------------------------------------------------------------------------
# -e: Exit immediately if any command exits with a non-zero status.
# -u: Treat unset variables as errors during substitution.
# -o pipefail: Return the exit status of the last failing command in a pipeline.
set -euo pipefail

# Capture start timestamp for accurate duration calculation
START_TIME=$(date +%s)

# Determine exact script directory (`deployment/`) and absolute project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Parse optional command-line flags (--force / -f)
FORCE_DEPLOY=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--force)
            FORCE_DEPLOY=true
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Usage: $0 [--force|-f]" >&2
            exit 1
            ;;
    esac
done

# ------------------------------------------------------------------------------
# 2. Logging Setup & Configuration Loading
# ------------------------------------------------------------------------------
# Load optional deployment-specific environment variables (`.deployment.env`)
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

# Ensure log directory exists (`logs/` or configured LOGS_DIR)
DEPLOY_LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${DEPLOY_LOGS_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${DEPLOY_LOGS_DIR}/deploy_${TIMESTAMP}.log"

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
    echo -e "${BLUE}[INFO] ${TIMESTAMP} - ${1}${RESET}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] ${TIMESTAMP} - ${1}${RESET}"
}

log_warn() {
    echo -e "${YELLOW}[WARNING] ${TIMESTAMP} - ${1}${RESET}"
}

log_error() {
    echo -e "${RED}[ERROR] ${TIMESTAMP} - ${1}${RESET}" >&2
}

log_header() {
    echo -e "\n${BOLD}${CYAN}==============================================================================${RESET}"
    echo -e "${BOLD}${CYAN} ${1} ${RESET}"
    echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
}

# Redirect all stdout and stderr streams to both terminal and timestamped log file
exec > >(tee -a "${LOG_FILE}") 2>&1

log_header "STARTING DJANGO PRODUCTION DEPLOYMENT"
log_info "Project Root Directory: ${PROJECT_ROOT}"
log_info "Deployment Suite Dir:   ${SCRIPT_DIR}"
log_info "Log File Path:          ${LOG_FILE}"
log_info "Force Deploy Flag:      ${FORCE_DEPLOY}"

# ------------------------------------------------------------------------------
# 3. Exit Trap for Cleanup and Summary Reporting
# ------------------------------------------------------------------------------
# Global state variables tracked across steps for final summary reporting
BEFORE_COMMIT=""
AFTER_COMMIT=""
HEALTHCHECK_PASSED=false

on_exit() {
    local exit_code=$?
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    log_header "DEPLOYMENT SUMMARY"
    log_info "Total Duration: ${minutes}m ${seconds}s"
    log_info "Git Transition: ${BEFORE_COMMIT:-unknown} -> ${AFTER_COMMIT:-unknown}"

    if [[ ${exit_code} -eq 0 && "${HEALTHCHECK_PASSED}" == "true" ]]; then
        log_success "Deployment completed successfully without errors."
    elif [[ ${exit_code} -eq 0 && "${BEFORE_COMMIT}" != "" && "${BEFORE_COMMIT}" == "${AFTER_COMMIT}" && "${FORCE_DEPLOY}" == "false" ]]; then
        log_success "Deployment exited cleanly: No code changes detected between remote and local HEAD."
    else
        log_error "Deployment terminated with exit status ${exit_code} after ${minutes}m ${seconds}s."
        log_warn "Review full deployment logs at: ${LOG_FILE}"
    fi
}
trap on_exit EXIT

# ------------------------------------------------------------------------------
# 4. Pre-Flight Verification & Environment Checks
# ------------------------------------------------------------------------------
log_header "STEP 1: Pre-flight Verification & Environment Checks"

# 4.1 Verify repository is a valid Git repository
log_info "Verifying Git repository status..."
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log_error "Current directory (${PROJECT_ROOT}) is not a Git repository."
    exit 1
fi
log_success "Git repository verified."

# 4.2 Verify Docker binary exists
log_info "Verifying Docker installation..."
if ! command -v docker >/dev/null 2>&1; then
    log_error "Docker executable not found in PATH."
    exit 1
fi
log_success "Docker verified: $(docker --version)"

# 4.3 Verify Docker Compose command (v2 plugin or v1 standalone)
log_info "Verifying Docker Compose availability..."
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose ('docker compose' or 'docker-compose') is not installed."
    exit 1
fi
log_success "Docker Compose verified using: '${DOCKER_COMPOSE_CMD}'"

# 4.4 Verify Docker daemon is actively running and socket is accessible
log_info "Verifying Docker daemon connectivity..."
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or current user lacks socket access permissions."
    exit 1
fi
log_success "Docker daemon is active and responsive."

# 4.5 Verify main application environment file (.env) exists
log_info "Checking application configuration (${PROJECT_ROOT}/.env)..."
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    log_error "Required environment file '.env' not found in project root (${PROJECT_ROOT})."
    exit 1
fi
log_success "Application .env file verified."

# 4.6 Ensure execution permissions on companion scripts in deployment/
if [[ -x "${SCRIPT_DIR}/permissions.sh" ]]; then
    log_info "Executing permissions.sh to verify/fix suite permissions..."
    bash "${SCRIPT_DIR}/permissions.sh" || log_warn "permissions.sh reported warnings; ensuring basic +x on companion scripts..."
fi
chmod +x "${SCRIPT_DIR}/"*.sh 2>/dev/null || true

# ------------------------------------------------------------------------------
# 5. Pre-Deployment Database Backup
# ------------------------------------------------------------------------------
log_header "STEP 2: Pre-Deployment Database Backup"

log_info "Calling pre-deployment backup script (${SCRIPT_DIR}/backup.sh)..."
if [[ -x "${SCRIPT_DIR}/backup.sh" ]]; then
    if bash "${SCRIPT_DIR}/backup.sh"; then
        log_success "Database backup completed successfully via backup.sh."
    else
        log_error "Pre-deployment database backup failed! Aborting deployment to protect data."
        exit 1
    fi
else
    log_error "Required backup script not executable or not found: ${SCRIPT_DIR}/backup.sh"
    exit 1
fi

# ------------------------------------------------------------------------------
# 6. Git Operations & Change Detection
# ------------------------------------------------------------------------------
log_header "STEP 3: Git Synchronization & Diff Detection"

BEFORE_COMMIT=$(git rev-parse HEAD)
log_info "Current local commit (HEAD): ${BEFORE_COMMIT}"

log_info "Fetching latest tags, branches, and commits from origin..."
git fetch --all --tags --prune

# Determine current tracking branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "${CURRENT_BRANCH}" == "HEAD" ]]; then
    log_warn "Detached HEAD state detected. Pulling fast-forward updates from origin/main..."
    git pull --ff-only origin main || git pull --ff-only origin master
else
    log_info "Fast-forward pulling upstream updates on branch '${CURRENT_BRANCH}'..."
    git pull --ff-only
fi

AFTER_COMMIT=$(git rev-parse HEAD)
log_info "Updated local commit (HEAD): ${AFTER_COMMIT}"

# Check whether files actually changed between before and after pull
if [[ "${BEFORE_COMMIT}" == "${AFTER_COMMIT}" ]]; then
    if [[ "${FORCE_DEPLOY}" == "true" ]]; then
        log_warn "No commit differences detected (${AFTER_COMMIT}), but --force (-f) flag passed. Proceeding."
    else
        log_success "No file modifications detected from upstream repo. Exiting cleanly without restarting services."
        exit 0
    fi
else
    log_info "Summary of changes (${BEFORE_COMMIT} .. ${AFTER_COMMIT}):"
    git diff --stat "${BEFORE_COMMIT}" "${AFTER_COMMIT}"
fi

# ------------------------------------------------------------------------------
# 7. Build & Recreate Affected Containers (Idempotent Lifecycle)
# ------------------------------------------------------------------------------
log_header "STEP 4: Building Images & Recreating Affected Containers"

log_info "Building application Docker images..."
${DOCKER_COMPOSE_CMD} build --pull

log_info "Recreating only affected container services (--remove-orphans)..."
# Compose calculates image hashes and service config digests; only changed services are recreated
${DOCKER_COMPOSE_CMD} up -d --remove-orphans

# Verify critical infrastructure dependencies (PostgreSQL / Redis) are ready
log_info "Waiting for database and caching services to stabilize..."
for service in db redis; do
    if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^${service}$"; then
        attempt=0
        while [ $attempt -le 12 ]; do
            STATUS=$(${DOCKER_COMPOSE_CMD} ps --format json "${service}" 2>/dev/null | grep -o '"Health": *"[^"]*"' | cut -d'"' -f4 || echo "running")
            if [[ -z "${STATUS}" || "${STATUS}" == "running" || "${STATUS}" == "healthy" ]]; then
                break
            fi
            sleep 5
            attempt=$((attempt + 1))
        done
    fi
done
log_success "Core data tier services are responsive."

# ------------------------------------------------------------------------------
# 8. Post-Deployment Django Tasks (Migrations & Static Files)
# ------------------------------------------------------------------------------
log_header "STEP 5: Django Application Tasks (Migrations & Collectstatic)"

# Call companion migrate.sh if available, otherwise execute directly on web container
log_info "Executing database migrations..."
if [[ -x "${SCRIPT_DIR}/migrate.sh" ]]; then
    log_info "Delegating database migration task to ${SCRIPT_DIR}/migrate.sh..."
    bash "${SCRIPT_DIR}/migrate.sh"
else
    log_info "Running Django migrations inside 'web' container..."
    ${DOCKER_COMPOSE_CMD} exec -T web python manage.py migrate --noinput
fi
log_success "Database migrations verified."

log_info "Collecting static assets inside 'web' container..."
${DOCKER_COMPOSE_CMD} exec -T web python manage.py collectstatic --noinput --clear
log_success "Static asset collection completed."

# ------------------------------------------------------------------------------
# 9. Service Restarts & Reverse Proxy Reloads
# ------------------------------------------------------------------------------
log_header "STEP 6: Service Restarts (Workers & Reverse Proxy)"

# Restart Celery Worker to apply updated Python tasks/signatures
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^celery_worker$"; then
    log_info "Restarting Celery Worker service..."
    ${DOCKER_COMPOSE_CMD} restart celery_worker
    log_success "Celery Worker restarted successfully."
else
    log_warn "Service 'celery_worker' not found or not running; skipping."
fi

# Restart Celery Beat to reload scheduled periodic task definitions
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^celery_beat$"; then
    log_info "Restarting Celery Beat service..."
    ${DOCKER_COMPOSE_CMD} restart celery_beat
    log_success "Celery Beat restarted successfully."
else
    log_warn "Service 'celery_beat' not found or not running; skipping."
fi

# Check and reload/restart Nginx if required
if ${DOCKER_COMPOSE_CMD} ps --services 2>/dev/null | grep -q "^nginx$"; then
    # Check if Nginx config files changed between commits OR if force deploy requested
    if git diff --name-only "${BEFORE_COMMIT}" "${AFTER_COMMIT}" 2>/dev/null | grep -E '^(docker/nginx/|nginx/|.*\.conf)' >/dev/null || [[ "${FORCE_DEPLOY}" == "true" ]]; then
        log_info "Nginx configuration changes detected or force deploy active. Validating Nginx syntax..."
        if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t; then
            log_info "Reloading Nginx configuration gracefully without dropping connections..."
            ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -s reload || ${DOCKER_COMPOSE_CMD} restart nginx
            log_success "Nginx configuration reloaded."
        else
            log_error "Nginx configuration validation (nginx -t) failed! Aborting before restart."
            exit 1
        fi
    else
        log_info "No Nginx configuration changes detected; preserving active proxy connections."
    fi
fi

# ------------------------------------------------------------------------------
# 10. Health Checks & Automated Rollback Protection
# ------------------------------------------------------------------------------
log_header "STEP 7: Post-Deployment Health Verification & Automated Rollback"

# Allow services a few seconds to bind ports and initialize workers
sleep 5

log_info "Calling post-deployment health verification script (${SCRIPT_DIR}/healthcheck.sh)..."
if [[ -x "${SCRIPT_DIR}/healthcheck.sh" ]]; then
    if bash "${SCRIPT_DIR}/healthcheck.sh"; then
        HEALTHCHECK_PASSED=true
        log_success "External health checks passed successfully."
    else
        log_error "External healthcheck.sh reported failure!"
        HEALTHCHECK_PASSED=false
    fi
else
    log_error "Required health check script not executable or not found: ${SCRIPT_DIR}/healthcheck.sh"
    HEALTHCHECK_PASSED=false
fi

# Automatic Rollback Trigger if Health Verification Fails
if [[ "${HEALTHCHECK_PASSED}" != "true" ]]; then
    log_error "CRITICAL: POST-DEPLOYMENT HEALTH VERIFICATION FAILED!"
    
    if [[ -x "${SCRIPT_DIR}/rollback.sh" ]]; then
        log_warn "Triggering automated rollback via ${SCRIPT_DIR}/rollback.sh (Target Commit: ${BEFORE_COMMIT})..."
        bash "${SCRIPT_DIR}/rollback.sh" "${BEFORE_COMMIT}" || log_error "Rollback script encountered errors during execution!"
    else
        log_error "No executable rollback script found at ${SCRIPT_DIR}/rollback.sh! Performing direct Git reset & container restore..."
        if [[ -n "${BEFORE_COMMIT}" && "${BEFORE_COMMIT}" != "${AFTER_COMMIT}" ]]; then
            git reset --hard "${BEFORE_COMMIT}"
            ${DOCKER_COMPOSE_CMD} up -d --remove-orphans --build
            ${DOCKER_COMPOSE_CMD} restart celery_worker celery_beat || true
            log_success "Emergency container restore to commit ${BEFORE_COMMIT} executed."
        else
            log_error "Cannot rollback automatically: BEFORE_COMMIT is unknown or identical to current commit."
        fi
    fi
    # Exit non-zero so trap logs overall deployment failure
    exit 1
fi

log_success "All production verification checks completed. Deployment succeeded."
exit 0
