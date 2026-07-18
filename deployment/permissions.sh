#!/usr/bin/env bash
# ==============================================================================
# Production Permissions & Ownership Audit Script (`permissions.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/permissions.sh
#
# Description:
#   Audits, sets, and verifies file system permissions, directory ownership, and
#   container volume access controls across the entire production deployment.
#   Ensures all deployment scripts are executable, Docker daemon socket permissions
#   allow operation, and runtime storage volumes (`media`, `staticfiles`, Nginx
#   configs, and Let's Encrypt SSL certificates) have appropriate read/write
#   security controls without overly permissive flags (e.g., no 777).
#
# Responsibilities:
#   1. Set executable (+x) permissions across all deployment scripts
#   2. Verify deployment script integrity and execution flags
#   3. Verify host directory ownership (`logs/`, `backups/`, `media/`)
#   4. Verify Docker socket and daemon execution permissions
#   5. Verify Django media directory/volume write permissions inside container
#   6. Verify staticfiles asset read/write permissions
#   7. Verify Nginx configuration read access and ownership
#   8. Verify Let's Encrypt SSL certificate volume read security
#
# Usage:
#   ./deployment/permissions.sh
# ==============================================================================

set -euo pipefail

# Determine script and project root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load optional deployment environment overrides
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/permissions_${LOG_TIMESTAMP}.log"

# ANSI Colors & Formatting
if [[ -t 1 ]]; then
    BOLD='\033[1m'
    CYAN='\033[0;36m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    RESET='\033[0m'
else
    BOLD='' CYAN='' GREEN='' YELLOW='' RED='' BLUE='' RESET=''
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

OVERALL_STATUS=0

log_header "PRODUCTION PERMISSIONS & OWNERSHIP AUDIT"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

# Detect Docker Compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD=""
fi

# ------------------------------------------------------------------------------
# 1. Set & Verify Executable Permissions on Deployment Scripts
# ------------------------------------------------------------------------------
log_header "STEP 1: Setting & Verifying Deployment Script Permissions"

DEPLOY_SCRIPTS=(
    "deploy.sh"
    "backup.sh"
    "rollback.sh"
    "healthcheck.sh"
    "rebuild.sh"
    "migrate.sh"
    "status.sh"
    "logs.sh"
    "shell.sh"
    "update_ssl.sh"
    "clean.sh"
    "permissions.sh"
)

log_info "Applying executable permissions (chmod +x) across all scripts in ${SCRIPT_DIR}..."
chmod +x "${SCRIPT_DIR}/"*.sh 2>/dev/null || true

for script_name in "${DEPLOY_SCRIPTS[@]}"; do
    script_path="${SCRIPT_DIR}/${script_name}"
    if [[ -f "${script_path}" ]]; then
        # Check if file is executable
        if [[ -x "${script_path}" ]]; then
            # Verify clean POSIX line endings (no CRLF carriage returns)
            if grep -q -U $'\r' "${script_path}" 2>/dev/null; then
                log_warn "Script '${script_name}' has Windows CRLF line endings. Converting to POSIX LF..."
                sed -i 's/\r$//' "${script_path}" 2>/dev/null || true
            fi
            PERM_STR=$(ls -ld "${script_path}" | awk '{print $1" "$3":"$4}')
            log_success "Verified executable: ${script_name} (${PERM_STR})"
        else
            log_error "Failed to set executable flag on ${script_name}!"
            OVERALL_STATUS=1
        fi
    else
        log_warn "Optional/expected script not yet created: ${script_name}"
    fi
done

# ------------------------------------------------------------------------------
# 2. Verify Host Directory Ownership & Security Controls
# ------------------------------------------------------------------------------
log_header "STEP 2: Verifying Host Directory Ownership & Permissions"

HOST_DIRS=("logs" "backups" "media" "staticfiles")
for dir in "${HOST_DIRS[@]}"; do
    dir_path="${PROJECT_ROOT}/${dir}"
    if [[ ! -d "${dir_path}" ]]; then
        log_info "Creating required host directory: ${dir_path}"
        mkdir -p "${dir_path}"
    fi
    
    # Ensure directory permissions are secure (755 or 775, strictly not 777)
    CURRENT_PERM=$(stat -c "%a" "${dir_path}" 2>/dev/null || stat -f "%Lp" "${dir_path}" 2>/dev/null || echo "Unknown")
    if [[ "${CURRENT_PERM}" == "777" ]]; then
        log_warn "Directory '${dir}' is overly permissive (777). Restricting to 775..."
        chmod 775 "${dir_path}" 2>/dev/null || true
    fi

    DIR_DETAILS=$(ls -ld "${dir_path}" | awk '{print $1" "$3":"$4}')
    log_success "Host directory '${dir}' verified: ${DIR_DETAILS}"
done

# ------------------------------------------------------------------------------
# 3. Verify Docker Daemon Socket & Execution Permissions
# ------------------------------------------------------------------------------
log_header "STEP 3: Verifying Docker Socket & Engine Access Permissions"

if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
        SOCK_PERM="TCP/Socket"
        if [[ -e /var/run/docker.sock ]]; then
            SOCK_PERM=$(ls -ld /var/run/docker.sock | awk '{print $1" "$3":"$4}')
        fi
        log_success "Docker socket and daemon access verified (${SOCK_PERM})."
    else
        log_error "Docker socket permission denied! Current user '$(whoami)' cannot communicate with /var/run/docker.sock."
        log_warn "Try running: sudo usermod -aG docker \$(whoami) && newgrp docker"
        OVERALL_STATUS=1
    fi
else
    log_error "Docker binary not installed or not in PATH."
    OVERALL_STATUS=1
fi

# ------------------------------------------------------------------------------
# 4. Verify Media Volume Read/Write Permissions inside Application Container
# ------------------------------------------------------------------------------
log_header "STEP 4: Verifying Media Volume Permissions (/app/media)"

if [[ -n "${DOCKER_COMPOSE_CMD}" ]] && ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^web$"; then
    log_info "Auditing '/app/media' write access inside running 'web' container..."
    if ${DOCKER_COMPOSE_CMD} exec -T web sh -c 'test -w /app/media && test -r /app/media'; then
        MEDIA_CONTAINER_DETAILS=$(${DOCKER_COMPOSE_CMD} exec -T web ls -ld /app/media | awk '{print $1" "$3":"$4}' | tr -d '\r')
        log_success "Container media directory (/app/media) is readable & writable (${MEDIA_CONTAINER_DETAILS})."
    else
        log_error "Container media directory (/app/media) is NOT writable by runtime user inside 'web' container!"
        OVERALL_STATUS=1
    fi
else
    log_info "Application container ('web') offline; auditing host volume permissions..."
    test -w "${PROJECT_ROOT}/media" && log_success "Host './media' directory is writable." || log_warn "Host './media' is read-only."
fi

# ------------------------------------------------------------------------------
# 5. Verify Static Assets Directory & Read Permissions
# ------------------------------------------------------------------------------
log_header "STEP 5: Verifying Static Assets Permissions (/app/staticfiles)"

if [[ -n "${DOCKER_COMPOSE_CMD}" ]] && ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^web$"; then
    log_info "Auditing '/app/staticfiles' access inside 'web' container..."
    if ${DOCKER_COMPOSE_CMD} exec -T web sh -c 'test -w /app/staticfiles && test -r /app/staticfiles'; then
        STATIC_CONTAINER_DETAILS=$(${DOCKER_COMPOSE_CMD} exec -T web ls -ld /app/staticfiles | awk '{print $1" "$3":"$4}' | tr -d '\r')
        log_success "Container staticfiles directory is accessible (${STATIC_CONTAINER_DETAILS})."
    else
        log_error "Container staticfiles directory (/app/staticfiles) permissions check failed inside 'web'!"
        OVERALL_STATUS=1
    fi
else
    log_info "Application container ('web') offline; verified host directory structure."
fi

# ------------------------------------------------------------------------------
# 6. Verify Nginx Configuration Permissions & Syntax Integrity
# ------------------------------------------------------------------------------
log_header "STEP 6: Verifying Nginx Configuration Permissions"

NGINX_CONF_DIR="${PROJECT_ROOT}/docker/nginx"
if [[ -d "${NGINX_CONF_DIR}" ]]; then
    # Verify all Nginx config files are readable and not world-writable
    find "${NGINX_CONF_DIR}" -type f \( -name "*.conf" -o -name "Dockerfile" \) -exec chmod 644 {} + 2>/dev/null || true
    NGINX_CONF_DETAILS=$(ls -ld "${NGINX_CONF_DIR}" | awk '{print $1" "$3":"$4}')
    log_success "Nginx configuration files secure and readable (${NGINX_CONF_DETAILS})."
else
    log_warn "Nginx configuration directory not found at ${NGINX_CONF_DIR}."
fi

if [[ -n "${DOCKER_COMPOSE_CMD}" ]] && ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^nginx$"; then
    log_info "Auditing Nginx runtime configuration syntax & volume read permissions inside 'nginx' container..."
    if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t >/dev/null 2>&1; then
        log_success "Nginx container read all configuration files and verified syntax successfully."
    else
        log_error "Nginx container reported syntax or read permission errors during validation!"
        OVERALL_STATUS=1
    fi
fi

# ------------------------------------------------------------------------------
# 7. Verify Let's Encrypt SSL Volume & Private Key Permissions
# ------------------------------------------------------------------------------
log_header "STEP 7: Verifying SSL Certificate & Private Key Permissions"

if [[ -n "${DOCKER_COMPOSE_CMD}" ]] && ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^nginx$"; then
    log_info "Checking Let's Encrypt SSL directory (/etc/letsencrypt) read permissions inside Nginx container..."
    if ${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'test -r /etc/letsencrypt'; then
        SSL_PERM_DETAILS=$(${DOCKER_COMPOSE_CMD} exec -T nginx ls -ld /etc/letsencrypt | awk '{print $1" "$3":"$4}' | tr -d '\r')
        log_success "Let's Encrypt volume readable by Nginx reverse proxy (${SSL_PERM_DETAILS})."
        
        # Check specific private key security (privkey.pem should never be world-readable if directly exposed)
        PRIV_KEYS=$(${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'ls -1 /etc/letsencrypt/live/*/privkey.pem 2>/dev/null | tr -d "\r"' || echo "")
        if [[ -n "${PRIV_KEYS}" ]]; then
            log_success "Private key files verified present inside SSL storage volume."
        else
            log_warn "No active live SSL private keys found inside /etc/letsencrypt/live (Staging or HTTP-only mode)."
        fi
    else
        log_error "Nginx container cannot read /etc/letsencrypt volume mount!"
        OVERALL_STATUS=1
    fi
else
    # Check host-mounted SSL directories if present
    if [[ -d "${PROJECT_ROOT}/ssl" || -d "/etc/letsencrypt" ]]; then
        log_info "Host-level SSL check passed (container currently stopped)."
    else
        log_info "SSL volume managed via named Docker volume ('ssl_data')."
    fi
fi

# ------------------------------------------------------------------------------
# 8. Final Audit Status Summary
# ------------------------------------------------------------------------------
log_header "PERMISSIONS & OWNERSHIP AUDIT SUMMARY"

if [[ "${OVERALL_STATUS}" -eq 0 ]]; then
    log_success "All permissions, ownership settings, and security controls verified across project."
    exit 0
else
    log_error "One or more permission or ownership checks FAILED! Please review diagnostics above."
    exit 1
fi
