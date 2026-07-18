#!/usr/bin/env bash
# ==============================================================================
# Production Health Check Script (`healthcheck.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/healthcheck.sh
#
# Description:
#   Comprehensive production health verification script. Performs multi-layered
#   health checks across host resources (CPU, Memory, Disk), Docker infrastructure,
#   core data stores (PostgreSQL, Redis), application workers (Celery, Beat),
#   web proxy (Nginx, HTTPS, SSL Certificate Expiry), and the Django HTTP API
#   endpoint (/api/v1/health/) with 5 automatic retries.
#
# Return Code:
#   0 = success (All required checks passed)
#   1 = failed  (One or more critical checks failed)
#
# Usage:
#   ./deployment/healthcheck.sh
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Shell Configuration & Error Handling Setup
# ------------------------------------------------------------------------------
set -uo pipefail

# Determine paths dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load optional deployment overrides
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

# Ensure log directory exists
LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOGS_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOGS_DIR}/healthcheck_${TIMESTAMP}.log"

# ANSI Color Codes
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
    echo -e "${BLUE}[INFO]    ${1}${RESET}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] ${1}${RESET}"
}

log_warn() {
    echo -e "${YELLOW}[WARNING] ${1}${RESET}"
}

log_error() {
    echo -e "${RED}[FAIL]    ${1}${RESET}" >&2
}

log_header() {
    echo -e "\n${BOLD}${CYAN}==============================================================================${RESET}"
    echo -e "${BOLD}${CYAN} ${1} ${RESET}"
    echo -e "${BOLD}${CYAN}==============================================================================${RESET}"
}

# Redirect all stdout and stderr streams to both terminal and timestamped log file
exec > >(tee -a "${LOG_FILE}") 2>&1

log_header "PRODUCTION ENVIRONMENT HEALTH CHECK"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

OVERALL_STATUS=0

# Detect Docker Compose command style
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    log_error "Docker Compose ('docker compose' or 'docker-compose') not found."
    exit 1
fi

# ------------------------------------------------------------------------------
# 2. Host System Resource Checks (CPU, Memory, Disk Usage)
# ------------------------------------------------------------------------------
log_header "STEP 1: Host System Resource Verification"

# 2.1 Disk Usage Check (Warn above 85%, Fail above 95%)
DISK_PATH="/"
DISK_USAGE_PCT=$(df -h "${DISK_PATH}" | awk 'NR==2 {print $5}' | tr -d '%')
DISK_AVAIL=$(df -h "${DISK_PATH}" | awk 'NR==2 {print $4}')

if [[ "${DISK_USAGE_PCT}" -ge 95 ]]; then
    log_error "Critical Disk Usage on ${DISK_PATH}: ${DISK_USAGE_PCT}% used (${DISK_AVAIL} available)"
    OVERALL_STATUS=1
elif [[ "${DISK_USAGE_PCT}" -ge 85 ]]; then
    log_warn "High Disk Usage on ${DISK_PATH}: ${DISK_USAGE_PCT}% used (${DISK_AVAIL} available)"
else
    log_success "Disk Usage check passed: ${DISK_USAGE_PCT}% used (${DISK_AVAIL} available)"
fi

# 2.2 Memory Usage Check
if command -v free >/dev/null 2>&1; then
    MEM_TOTAL=$(free -m | awk '/^Mem:/ {print $2}')
    MEM_USED=$(free -m | awk '/^Mem:/ {print $3}')
    MEM_AVAIL=$(free -m | awk '/^Mem:/ {print $7}')
    MEM_USAGE_PCT=$(( (MEM_USED * 100) / MEM_TOTAL ))

    if [[ "${MEM_USAGE_PCT}" -ge 95 ]]; then
        log_error "Critical Memory Usage: ${MEM_USAGE_PCT}% used (${MEM_AVAIL}MB available out of ${MEM_TOTAL}MB)"
        OVERALL_STATUS=1
elif [[ "${MEM_USAGE_PCT}" -ge 85 ]]; then
        log_warn "High Memory Usage: ${MEM_USAGE_PCT}% used (${MEM_AVAIL}MB available out of ${MEM_TOTAL}MB)"
    else
        log_success "Memory Usage check passed: ${MEM_USAGE_PCT}% used (${MEM_AVAIL}MB available)"
    fi
else
    log_info "Command 'free' not found; skipping detailed memory percentage check."
fi

# 2.3 CPU Load Check
if [[ -f /proc/loadavg ]]; then
    LOAD_1M=$(awk '{print $1}' /proc/loadavg)
    CPU_CORES=$(nproc 2>/dev/null || grep -c ^processor /proc/cpuinfo 2>/dev/null || echo "1")
    # Convert float load to integer percentage relative to total core count
    LOAD_PCT=$(awk -v l="${LOAD_1M}" -v c="${CPU_CORES}" 'BEGIN {printf "%d", (l / c) * 100}')

    if [[ "${LOAD_PCT}" -ge 150 ]]; then
        log_error "High CPU Load Average (1m): ${LOAD_1M} across ${CPU_CORES} core(s) (${LOAD_PCT}%)"
        OVERALL_STATUS=1
    elif [[ "${LOAD_PCT}" -ge 90 ]]; then
        log_warn "Elevated CPU Load Average (1m): ${LOAD_1M} across ${CPU_CORES} core(s) (${LOAD_PCT}%)"
    else
        log_success "CPU Load check passed: ${LOAD_1M} across ${CPU_CORES} core(s) (${LOAD_PCT}%)"
    fi
fi

# ------------------------------------------------------------------------------
# 3. Docker Infrastructure & Daemon Checks
# ------------------------------------------------------------------------------
log_header "STEP 2: Docker Daemon & Container Verification"

# 3.1 Check Docker Daemon
if ! docker info >/dev/null 2>&1; then
    log_error "Docker daemon is not running or socket connection refused!"
    exit 1
fi
log_success "Docker daemon is active and responsive."

# 3.2 Check Expected Containers
EXPECTED_SERVICES=("web" "db" "redis" "celery_worker" "celery_beat" "nginx")
RUNNING_SERVICES=$(${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null || echo "")

for svc in "${EXPECTED_SERVICES[@]}"; do
    if echo "${RUNNING_SERVICES}" | grep -qw "${svc}"; then
        # Check explicit container health status if defined
        HEALTH_STATUS=$(${DOCKER_COMPOSE_CMD} ps --format json "${svc}" 2>/dev/null | grep -o '"Health": *"[^"]*"' | cut -d'"' -f4 || echo "running")
        if [[ "${HEALTH_STATUS}" == "healthy" || "${HEALTH_STATUS}" == "running" || -z "${HEALTH_STATUS}" ]]; then
            log_success "Docker container '${svc}' is running (${HEALTH_STATUS:-active})."
        else
            log_error "Docker container '${svc}' reported abnormal health: ${HEALTH_STATUS}"
            OVERALL_STATUS=1
        fi
    else
        log_error "Expected service container '${svc}' is NOT running!"
        OVERALL_STATUS=1
    fi
done

# ------------------------------------------------------------------------------
# 4. Core Data Store Checks (PostgreSQL & Redis)
# ------------------------------------------------------------------------------
log_header "STEP 3: Data Tier Verification (PostgreSQL & Redis)"

# 4.1 PostgreSQL Health & Connectivity
if echo "${RUNNING_SERVICES}" | grep -qw "db"; then
    DB_USER=$(grep -E '^(POSTGRES_USER|DB_USER)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_NAME=$(grep -E '^(POSTGRES_DB|DB_NAME)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_PASS=$(grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")

    if ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
        # Perform quick read-only test query
        if ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1;" >/dev/null 2>&1; then
            log_success "PostgreSQL database ('${DB_NAME}') is online and accepting queries."
        else
            log_error "PostgreSQL accepted TCP connection but failed test SQL query execution!"
            OVERALL_STATUS=1
        fi
    else
        log_error "PostgreSQL pg_isready verification failed!"
        OVERALL_STATUS=1
    fi
fi

# 4.2 Redis Health & Ping
if echo "${RUNNING_SERVICES}" | grep -qw "redis"; then
    if [[ "$(${DOCKER_COMPOSE_CMD} exec -T redis redis-cli ping 2>/dev/null | tr -d '\r')" == "PONG" ]]; then
        log_success "Redis cache server responded to PONG."
    else
        log_error "Redis cache server failed ping check!"
        OVERALL_STATUS=1
    fi
fi

# ------------------------------------------------------------------------------
# 5. Celery Workers & Periodic Scheduler Checks
# ------------------------------------------------------------------------------
log_header "STEP 4: Background Task Processing (Celery Worker & Beat)"

# 5.1 Celery Worker Check
if echo "${RUNNING_SERVICES}" | grep -qw "celery_worker"; then
    if ${DOCKER_COMPOSE_CMD} exec -T celery_worker celery -A config inspect ping -d "celery@\$(hostname)" >/dev/null 2>&1; then
        log_success "Celery Worker node is responsive and connected to broker."
    else
        log_warn "Celery Worker ping check timed out or failed (worker might be busy processing tasks)."
        # Fallback process verification inside container
        if ${DOCKER_COMPOSE_CMD} exec -T celery_worker ps aux 2>/dev/null | grep -v grep | grep -q "celery -A config worker"; then
            log_info "Celery worker process verified running in container."
        else
            log_error "Celery worker process not detected inside container!"
            OVERALL_STATUS=1
        fi
    fi
fi

# 5.2 Celery Beat Check
if echo "${RUNNING_SERVICES}" | grep -qw "celery_beat"; then
    if ${DOCKER_COMPOSE_CMD} exec -T celery_beat ps aux 2>/dev/null | grep -v grep | grep -q "celery -A config beat"; then
        log_success "Celery Beat periodic task scheduler process verified."
    else
        log_error "Celery Beat scheduler process not found running inside container!"
        OVERALL_STATUS=1
    fi
fi

# ------------------------------------------------------------------------------
# 6. Reverse Proxy, HTTPS & SSL Certificate Expiry Checks
# ------------------------------------------------------------------------------
log_header "STEP 5: Reverse Proxy & SSL Expiry Verification"

# 6.1 Nginx Configuration Check
if echo "${RUNNING_SERVICES}" | grep -qw "nginx"; then
    if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t >/dev/null 2>&1; then
        log_success "Nginx syntax and runtime configuration check passed."
    else
        log_error "Nginx configuration verification (nginx -t) failed!"
        OVERALL_STATUS=1
    fi

    # 6.2 SSL Certificate Expiry Check
    log_info "Checking Let's Encrypt / SSL certificate validity and expiration..."
    # Locate active live certificate files inside nginx container
    CERT_FILE=$(${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'ls -1 /etc/letsencrypt/live/*/fullchain.pem 2>/dev/null | head -1 | tr -d "\r"' || echo "")
    
    if [[ -n "${CERT_FILE}" && "${CERT_FILE}" != "" ]]; then
        EXPIRY_DATE=$(${DOCKER_COMPOSE_CMD} exec -T nginx openssl x509 -in "${CERT_FILE}" -noout -enddate 2>/dev/null | cut -d= -f2- || echo "")
        if [[ -n "${EXPIRY_DATE}" ]]; then
            EXPIRY_SEC=$(date -d "${EXPIRY_DATE}" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "${EXPIRY_DATE}" +%s 2>/dev/null || echo "0")
            NOW_SEC=$(date +%s)
            DAYS_LEFT=$(( (EXPIRY_SEC - NOW_SEC) / 86400 ))

            if [[ "${DAYS_LEFT}" -le 0 ]]; then
                log_error "SSL Certificate has EXPIRED (${EXPIRY_DATE})!"
                OVERALL_STATUS=1
            elif [[ "${DAYS_LEFT}" -le 14 ]]; then
                log_warn "SSL Certificate expiring soon: ${DAYS_LEFT} days remaining (${EXPIRY_DATE})"
            else
                log_success "SSL Certificate is valid for ${DAYS_LEFT} days (Expires: ${EXPIRY_DATE})"
            fi
        else
            log_warn "Could not parse expiration date from SSL certificate: ${CERT_FILE}"
        fi
    else
        # Try probing localhost:443 via openssl if cert files not mounted directly at /etc/letsencrypt/live
        if echo | openssl s_client -connect localhost:443 -servername edunaukari.com 2>/dev/null | openssl x509 -noout -enddate >/dev/null 2>&1; then
            EXP_STR=$(echo | openssl s_client -connect localhost:443 -servername edunaukari.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2-)
            log_success "HTTPS/SSL endpoint active on port 443 (Cert End Date: ${EXP_STR})"
        else
            log_warn "No Let's Encrypt live certificate found inside proxy and local SSL probe on port 443 did not respond (may be HTTP-only / staging)."
        fi
    fi
fi

# ------------------------------------------------------------------------------
# 7. Django HTTP API Health Endpoint Verification (/api/v1/health/)
# ------------------------------------------------------------------------------
log_header "STEP 6: Django API Health Endpoint (/api/v1/health/ - 5 Retries)"

HEALTH_ENDPOINT_PATH="/api/v1/health/"
MAX_RETRIES=5
RETRY_DELAY=3
API_HEALTHY=false

# Check internal endpoint responsiveness directly from web container
if echo "${RUNNING_SERVICES}" | grep -qw "web"; then
    for (( attempt=1; attempt<=MAX_RETRIES; attempt++ )); do
        log_info "Probing ${HEALTH_ENDPOINT_PATH} (Attempt ${attempt}/${MAX_RETRIES})..."
        
        # Test HTTP response code using python inside container (avoid requiring curl inside image)
        HTTP_STATUS=$(${DOCKER_COMPOSE_CMD} exec -T web python -c "
import urllib.request, sys
try:
    req = urllib.request.Request('http://localhost:8000${HEALTH_ENDPOINT_PATH}', headers={'User-Agent': 'HealthCheckScript/1.0'})
    resp = urllib.request.urlopen(req, timeout=8)
    print(resp.getcode())
except urllib.error.HTTPError as e:
    print(e.code)
except Exception as e:
    print('ERR')
" 2>/dev/null | tr -d '\r\n' || echo "ERR")

        if [[ "${HTTP_STATUS}" =~ ^(200|301|302)$ ]]; then
            log_success "API Health endpoint (${HEALTH_ENDPOINT_PATH}) responded with status ${HTTP_STATUS}."
            API_HEALTHY=true
            break
        else
            log_warn "Health endpoint probe returned HTTP status '${HTTP_STATUS}'. Retrying in ${RETRY_DELAY}s..."
            sleep "${RETRY_DELAY}"
        fi
    done

    if [[ "${API_HEALTHY}" != "true" ]]; then
        log_error "Django API Health endpoint (${HEALTH_ENDPOINT_PATH}) failed all ${MAX_RETRIES} attempts!"
        OVERALL_STATUS=1
    fi
else
    log_error "Cannot check API Health endpoint: Django container ('web') is not running!"
    OVERALL_STATUS=1
fi

# ------------------------------------------------------------------------------
# 8. Final Evaluation & Return Code
# ------------------------------------------------------------------------------
log_header "FINAL HEALTH VERIFICATION SUMMARY"

if [[ "${OVERALL_STATUS}" -eq 0 ]]; then
    log_success "All production health checks passed successfully. System is FULLY HEALTHY."
    exit 0
else
    log_error "One or more critical health checks FAILED! Please review diagnostics above."
    exit 1
fi
