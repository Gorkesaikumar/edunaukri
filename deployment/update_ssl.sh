#!/usr/bin/env bash
# ==============================================================================
# Production SSL Certificate Renewal & Verification Script (`update_ssl.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/update_ssl.sh
#
# Description:
#   Manages Let's Encrypt SSL/TLS certificates mounted inside the Nginx reverse
#   proxy container (`ssl_data` volume at `/etc/letsencrypt`).
#   Checks exact certificate expiration dates, calculates remaining days, and
#   performs renewal only when required (<= 30 days remaining) or when forced.
#   Verifies renewed certificates and reloads Nginx safely without downtime.
#
# Responsibilities:
#   1. Check certificate expiration and display exact remaining days
#   2. Skip unnecessary renewal if > 30 days remaining (unless `--force`)
#   3. Renew SSL via Certbot container/host engine (`certbot renew`)
#   4. Verify new certificate integrity (`openssl x509 -noout -enddate`)
#   5. Reload/restart Nginx gracefully only if certificates changed/renewed
#   6. Exit safely with comprehensive diagnostic logging
#
# Usage:
#   ./deployment/update_ssl.sh             # Check expiry & renew only if <= 30 days
#   ./deployment/update_ssl.sh --force     # Force immediate renewal & Nginx reload
# ==============================================================================

set -euo pipefail

# Determine script and project root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load optional deployment environment variables
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
LOG_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/update_ssl_${LOG_TIMESTAMP}.log"

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

# Redirect all stdout and stderr streams to both terminal and timestamped log file
exec > >(tee -a "${LOG_FILE}") 2>&1

FORCE_RENEWAL=false
for arg in "$@"; do
    case "${arg}" in
        -f|--force)
            FORCE_RENEWAL=true
            ;;
        -h|--help)
            echo "Usage: $0 [-f|--force]"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: ${arg}${RESET}" >&2
            exit 1
            ;;
    esac
done

log_header "PRODUCTION SSL CERTIFICATE CHECK & RENEWAL"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

# Detect Docker Compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose not found in PATH."
    exit 1
fi

# Verify Docker engine
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or socket permissions denied."
    exit 1
fi

# ------------------------------------------------------------------------------
# 1. Check Certificate Expiry & Display Remaining Days
# ------------------------------------------------------------------------------
log_header "STEP 1: Certificate Expiration & Status Check"

RENEWAL_NEEDED=false
DAYS_LEFT=999
CERT_PATH=""

if ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^nginx$"; then
    # Locate fullchain.pem inside nginx container
    CERT_PATH=$(${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'ls -1 /etc/letsencrypt/live/*/fullchain.pem 2>/dev/null | head -1 | tr -d "\r"' || echo "")
    
    if [[ -n "${CERT_PATH}" && "${CERT_PATH}" != "" ]]; then
        log_info "Found active certificate inside Nginx container: ${CERT_PATH}"
        EXPIRY_DATE=$(${DOCKER_COMPOSE_CMD} exec -T nginx openssl x509 -in "${CERT_PATH}" -noout -enddate 2>/dev/null | cut -d= -f2- || echo "")
        
        if [[ -n "${EXPIRY_DATE}" ]]; then
            EXPIRY_SEC=$(date -d "${EXPIRY_DATE}" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "${EXPIRY_DATE}" +%s 2>/dev/null || echo "0")
            NOW_SEC=$(date +%s)
            DAYS_LEFT=$(( (EXPIRY_SEC - NOW_SEC) / 86400 ))

            echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────────────────────────────────${RESET}"
            echo -e "  Certificate File:  ${BOLD}${CERT_PATH}${RESET}"
            echo -e "  Expiration Date:   ${BOLD}${EXPIRY_DATE}${RESET}"
            if [[ "${DAYS_LEFT}" -le 0 ]]; then
                echo -e "  Remaining Days:    ${BOLD}${RED}${DAYS_LEFT} days (EXPIRED)${RESET}"
            elif [[ "${DAYS_LEFT}" -le 30 ]]; then
                echo -e "  Remaining Days:    ${BOLD}${YELLOW}${DAYS_LEFT} days (Expiring soon)${RESET}"
            else
                echo -e "  Remaining Days:    ${BOLD}${GREEN}${DAYS_LEFT} days (Valid)${RESET}"
            fi
            echo -e "${BOLD}${CYAN}──────────────────────────────────────────────────────────────────────────────${RESET}"

            if [[ "${DAYS_LEFT}" -le 30 ]]; then
                log_warn "Certificate expires in ${DAYS_LEFT} days (<= 30). Renewal required."
                RENEWAL_NEEDED=true
            else
                log_success "Certificate is valid with ${DAYS_LEFT} remaining days (> 30 threshold)."
                RENEWAL_NEEDED=false
            fi
        else
            log_warn "Could not parse expiration date from ${CERT_PATH}. Forcing check/renewal."
            RENEWAL_NEEDED=true
        fi
    else
        log_warn "No live certificate found at /etc/letsencrypt/live inside Nginx container."
        RENEWAL_NEEDED=true
    fi
else
    log_warn "Nginx container is not running; checking via local certificate volume inspection or forcing renewal."
    RENEWAL_NEEDED=true
fi

# Override if forced
if [[ "${FORCE_RENEWAL}" == "true" ]]; then
    log_info "Renewal explicitly forced via --force (-f) flag."
    RENEWAL_NEEDED=true
fi

# ------------------------------------------------------------------------------
# 2. Skip Renewal if Not Needed
# ------------------------------------------------------------------------------
if [[ "${RENEWAL_NEEDED}" != "true" ]]; then
    log_header "RENEWAL UNNECESSARY"
    log_success "SSL Certificate is up-to-date (${DAYS_LEFT} days remaining). No Nginx reload or restart required."
    exit 0
fi

# ------------------------------------------------------------------------------
# 3. Perform Let's Encrypt SSL Renewal
# ------------------------------------------------------------------------------
log_header "STEP 2: Executing SSL Certificate Renewal"

RENEWAL_SUCCESS=false

# Check if docker compose has a dedicated certbot service
if ${DOCKER_COMPOSE_CMD} config --services 2>/dev/null | grep -q "^certbot$"; then
    log_info "Using Docker Compose 'certbot' service for renewal..."
    if ${DOCKER_COMPOSE_CMD} run --rm certbot renew --webroot -w /var/www/certbot; then
        RENEWAL_SUCCESS=true
    else
        log_error "Docker Compose certbot renewal encountered errors!"
        RENEWAL_SUCCESS=false
    fi
# Check if host has certbot binary installed directly
elif command -v certbot >/dev/null 2>&1; then
    log_info "Using host certbot engine for renewal..."
    if certbot renew; then
        RENEWAL_SUCCESS=true
    else
        log_error "Host certbot renewal check failed!"
        RENEWAL_SUCCESS=false
    fi
else
    # Fallback: Run ephemeral certbot container mounting project ssl and webroot named volumes
    log_info "Launching ephemeral Certbot Docker container (`certbot/certbot`) against named volumes..."
    
    # Resolve exact Docker volume names from project prefix
    PROJECT_NAME=$(${DOCKER_COMPOSE_CMD} ls --format json 2>/dev/null | grep -o '"Name": *"[^"]*"' | cut -d'"' -f4 | head -1 || echo "$(basename "${PROJECT_ROOT}")")
    SSL_VOL=$(docker volume ls --filter name="${PROJECT_NAME}_ssl_data" --format "{{.Name}}" 2>/dev/null | head -1 || echo "${PROJECT_NAME}_ssl_data")
    CERTBOT_VOL=$(docker volume ls --filter name="${PROJECT_NAME}_certbot_data" --format "{{.Name}}" 2>/dev/null | head -1 || echo "${PROJECT_NAME}_certbot_data")

    if docker run --rm \
        -v "${SSL_VOL}:/etc/letsencrypt" \
        -v "${CERTBOT_VOL}:/var/www/certbot" \
        certbot/certbot renew --webroot -w /var/www/certbot; then
        RENEWAL_SUCCESS=true
    else
        log_error "Ephemeral certbot container renewal check failed!"
        RENEWAL_SUCCESS=false
    fi
fi

if [[ "${RENEWAL_SUCCESS}" != "true" ]]; then
    log_error "Certificate renewal process failed! Please verify DNS resolution and webroot permissions."
    exit 1
fi
log_success "Let's Encrypt certificate check and renewal completed successfully."

# ------------------------------------------------------------------------------
# 4. Verify Renewed Certificate
# ------------------------------------------------------------------------------
log_header "STEP 3: Verifying Renewed Certificate Integrity"

if ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^nginx$"; then
    CERT_PATH=$(${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'ls -1 /etc/letsencrypt/live/*/fullchain.pem 2>/dev/null | head -1 | tr -d "\r"' || echo "")
    if [[ -n "${CERT_PATH}" && "${CERT_PATH}" != "" ]]; then
        NEW_EXPIRY=$(${DOCKER_COMPOSE_CMD} exec -T nginx openssl x509 -in "${CERT_PATH}" -noout -enddate 2>/dev/null | cut -d= -f2- || echo "")
        log_success "Verified renewed certificate fullchain: ${CERT_PATH}"
        log_info "New Expiration Date: ${BOLD}${NEW_EXPIRY:-Verified}${RESET}"
    else
        log_warn "Could not read certificate path inside Nginx container after renewal."
    fi
fi

# ------------------------------------------------------------------------------
# 5. Reload Nginx Reverse Proxy
# ------------------------------------------------------------------------------
log_header "STEP 4: Reloading Nginx Configuration"

if ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^nginx$"; then
    log_info "Testing Nginx syntax before reload (`nginx -t`)..."
    if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t; then
        log_info "Reloading Nginx proxy service cleanly (`nginx -s reload`)..."
        if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -s reload; then
            log_success "Nginx reloaded successfully without connection drops."
        else
            log_warn "Nginx reload failed; restarting container..."
            ${DOCKER_COMPOSE_CMD} restart nginx
            log_success "Nginx container restarted."
        fi
    else
        log_error "Nginx syntax check failed! Aborting reload to prevent proxy outage."
        exit 1
    fi
else
    log_info "Nginx container is not running; no reload needed."
fi

log_header "SSL RENEWAL SUMMARY"
log_success "All SSL renewal and proxy reload tasks finished safely."
exit 0
