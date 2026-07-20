#!/usr/bin/env bash
# ==============================================================================
# Production System Status & Dashboard Script (`status.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/status.sh
#
# Description:
#   Gathers comprehensive real-time metrics across host infrastructure, Docker
#   services, data stores, background workers, reverse proxy, and Git deployment
#   state, formatting all output into structured ASCII dashboard tables.
#
# Displayed Metrics:
#   - Host CPU, RAM, Disk, and System Uptime
#   - Git Branch, Current Commit, and Latest Deployment Timestamp
#   - Docker Containers, Images, and Container Health Statuses
#   - PostgreSQL status and exact Database Size (MB/GB)
#   - Redis status and responsiveness
#   - Celery Worker and Celery Beat scheduler status
#   - Nginx proxy status and SSL Certificate Expiry countdown
#   - Persistent Docker Volumes and Uploaded Media Size
#
# Usage:
#   ./deployment/status.sh
# ==============================================================================

set -uo pipefail

# Determine script and project root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load optional deployment environment variables
if [[ -f "${SCRIPT_DIR}/.deployment.env" ]]; then
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.deployment.env"
fi

# ANSI Colors & Formatting
if [[ -t 1 ]]; then
    BOLD='\033[1m'
    CYAN='\033[0;36m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    MAGENTA='\033[0;35m'
    RESET='\033[0m'
else
    BOLD='' CYAN='' GREEN='' YELLOW='' RED='' BLUE='' MAGENTA='' RESET=''
fi

# Helper functions for box-drawn table rows
print_row() {
    printf "│ %-24s │ %-49s │\n" "$1" "$2"
}

print_row_colored() {
    # Print formatted row allowing embedded ANSI codes while preserving width
    printf "│ %-24s │ %-58b │\n" "$1" "$2"
}

print_header() {
    echo -e "\n${BOLD}${CYAN}┌──────────────────────────┬───────────────────────────────────────────────────┐${RESET}"
    printf "${BOLD}${CYAN}│ %-24s │ %-49s │${RESET}\n" "$1" "$2"
    echo -e "${BOLD}${CYAN}├──────────────────────────┼───────────────────────────────────────────────────┤${RESET}"
}

print_footer() {
    echo -e "${BOLD}${CYAN}└──────────────────────────┴───────────────────────────────────────────────────┘${RESET}"
}

# Detect Docker Compose command style
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}[ERROR] Docker Compose ('docker compose' or 'docker-compose') not found.${RESET}" >&2
    exit 1
fi

echo -e "\n${BOLD}${MAGENTA}================================================================================${RESET}"
echo -e "${BOLD}${MAGENTA}                   EDUNAUKRI PRODUCTION SYSTEM STATUS DASHBOARD                 ${RESET}"
echo -e "${BOLD}${MAGENTA}================================================================================${RESET}"
echo -e "${BLUE}Report Generated: $(date +"%Y-%m-%d %H:%M:%S %Z")${RESET}"

# ==============================================================================
# 1. HOST SYSTEM RESOURCES & UPTIME
# ==============================================================================
print_header "SYSTEM RESOURCE" "METRIC / STATUS"

# Uptime
UPTIME_STR=$(uptime -p 2>/dev/null | sed 's/^up //' || uptime | awk -F'( |,|:)+' '{print $6"h "$7"m"}' 2>/dev/null || echo "Unknown")
print_row "Host Uptime" "${UPTIME_STR}"

# CPU Load Average
if [[ -f /proc/loadavg ]]; then
    LOAD_1M=$(awk '{print $1}' /proc/loadavg)
    LOAD_5M=$(awk '{print $2}' /proc/loadavg)
    LOAD_15M=$(awk '{print $3}' /proc/loadavg)
    CPU_CORES=$(nproc 2>/dev/null || echo "1")
    print_row "CPU Load Average" "${LOAD_1M} (1m), ${LOAD_5M} (5m), ${LOAD_15M} (15m) [${CPU_CORES} Cores]"
else
    print_row "CPU Load Average" "N/A"
fi

# RAM Usage
if command -v free >/dev/null 2>&1; then
    MEM_INFO=$(free -h | awk '/^Mem:/ {print $3 " / " $2 " (" $7 " available)"}')
    print_row "RAM Usage" "${MEM_INFO}"
else
    print_row "RAM Usage" "N/A"
fi

# Disk Usage
DISK_INFO=$(df -h / | awk 'NR==2 {print $3 " / " $2 " (" $5 " used, " $4 " free)"}')
print_row "Root Disk Usage (/)" "${DISK_INFO}"

print_footer

# ==============================================================================
# 2. GIT & DEPLOYMENT INFORMATION
# ==============================================================================
print_header "DEPLOYMENT INFO" "VALUE"

# Git Branch
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "Unknown")
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "Unknown")
    GIT_DATE=$(git log -1 --format="%cd" --date=short 2>/dev/null || echo "Unknown")
    GIT_MSG=$(git log -1 --format="%s" 2>/dev/null | cut -c1-35 || echo "")

    print_row_colored "Git Branch" "${GREEN}${GIT_BRANCH}${RESET}"
    print_row "Current Commit" "${GIT_COMMIT} (${GIT_DATE}) - ${GIT_MSG}"
else
    print_row "Git Branch" "Not a Git repository"
    print_row "Current Commit" "N/A"
fi

# Latest Deployment Date (Checked from deployment logs or container birth time)
LATEST_LOG=$(find "${PROJECT_ROOT}/logs/deployment" -name "deploy_*.log" -type f 2>/dev/null | sort -r | head -1 || echo "")
if [[ -n "${LATEST_LOG}" && -f "${LATEST_LOG}" ]]; then
    DEPLOY_DATE=$(date -r "${LATEST_LOG}" +"%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "Unknown")
    print_row_colored "Last Deployment Date" "${CYAN}${DEPLOY_DATE}${RESET}"
else
    # Fallback to web container start time
    WEB_START=$(${DOCKER_COMPOSE_CMD} ps --format json web 2>/dev/null | grep -o '"StartedAt": *"[^"]*"' | cut -d'"' -f4 | cut -d'.' -f1 | tr 'T' ' ' || echo "Unknown")
    print_row "Last Deployment Date" "${WEB_START:-Unknown}"
fi

print_footer

# ==============================================================================
# 3. CORE DATA STORES, VOLUMES & SIZES
# ==============================================================================
print_header "DATA STORE / VOLUME" "STATUS & STORAGE FOOTPRINT"

RUNNING_SERVICES=$(${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null || echo "")

# PostgreSQL Status & Database Size
if echo "${RUNNING_SERVICES}" | grep -qw "db"; then
    DB_USER=$(grep -E '^(POSTGRES_USER|DB_USER)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_NAME=$(grep -E '^(POSTGRES_DB|DB_NAME)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
    DB_PASS=$(grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")

    if ${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
        DB_SIZE=$(${DOCKER_COMPOSE_CMD} exec -T -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT pg_size_pretty(pg_database_size('${DB_NAME}'));" 2>/dev/null | tr -d ' \r\n' || echo "Unknown")
        print_row_colored "PostgreSQL ('${DB_NAME}')" "${GREEN}ONLINE${RESET} (Database Size: ${BOLD}${DB_SIZE:-N/A}${RESET})"
    else
        print_row_colored "PostgreSQL ('${DB_NAME}')" "${RED}UNRESPONSIVE / OFFLINE${RESET}"
    fi
else
    print_row_colored "PostgreSQL" "${RED}CONTAINER NOT RUNNING${RESET}"
fi

# Redis Status
if echo "${RUNNING_SERVICES}" | grep -qw "redis"; then
    if [[ "$(${DOCKER_COMPOSE_CMD} exec -T redis redis-cli ping 2>/dev/null | tr -d '\r')" == "PONG" ]]; then
        print_row_colored "Redis Cache Server" "${GREEN}ONLINE (PONG)${RESET}"
    else
        print_row_colored "Redis Cache Server" "${YELLOW}RUNNING BUT FAILED PING${RESET}"
    fi
else
    print_row_colored "Redis Cache Server" "${RED}CONTAINER NOT RUNNING${RESET}"
fi

# Uploaded Media Size
MEDIA_SIZE="Unknown"
if echo "${RUNNING_SERVICES}" | grep -qw "web"; then
    MEDIA_SIZE=$(${DOCKER_COMPOSE_CMD} exec -T web du -sh /app/media 2>/dev/null | cut -f1 | tr -d '\r' || echo "0B")
elif [[ -d "${PROJECT_ROOT}/media" ]]; then
    MEDIA_SIZE=$(du -sh "${PROJECT_ROOT}/media" 2>/dev/null | cut -f1 || echo "0B")
fi
print_row "Uploaded Media Size" "${MEDIA_SIZE}"

# Docker Volumes List & Count
VOL_COUNT=$(docker volume ls --filter name=edunaukri -q 2>/dev/null | wc -l || echo "0")
VOL_NAMES=$(docker volume ls --filter name=edunaukri --format "{{.Name}}" 2>/dev/null | sed 's/.*edunaukri_//' | tr '\n' ', ' | sed 's/, $//' || echo "None")
print_row "Docker Volumes (${VOL_COUNT})" "${VOL_NAMES:-None}"

print_footer

# ==============================================================================
# 4. BACKGROUND WORKERS & REVERSE PROXY HEALTH
# ==============================================================================
print_header "APPLICATION SERVICE" "OPERATIONAL HEALTH STATUS"

# Celery Worker
if echo "${RUNNING_SERVICES}" | grep -qw "celery_worker"; then
    if ${DOCKER_COMPOSE_CMD} exec -T celery_worker celery -A config inspect ping -d "celery@\$(hostname)" >/dev/null 2>&1; then
        print_row_colored "Celery Worker" "${GREEN}ONLINE (Connected & Active)${RESET}"
    else
        print_row_colored "Celery Worker" "${YELLOW}RUNNING (Ping Timeout/Processing)${RESET}"
    fi
else
    print_row_colored "Celery Worker" "${RED}OFFLINE${RESET}"
fi

# Celery Beat
if echo "${RUNNING_SERVICES}" | grep -qw "celery_beat"; then
    if ${DOCKER_COMPOSE_CMD} exec -T celery_beat ps aux 2>/dev/null | grep -v grep | grep -q "celery -A config beat"; then
        print_row_colored "Celery Beat Scheduler" "${GREEN}ONLINE (Active Process)${RESET}"
    else
        print_row_colored "Celery Beat Scheduler" "${YELLOW}RUNNING (Process Not Verified)${RESET}"
    fi
else
    print_row_colored "Celery Beat Scheduler" "${RED}OFFLINE${RESET}"
fi

# Nginx Proxy
if echo "${RUNNING_SERVICES}" | grep -qw "nginx"; then
    if ${DOCKER_COMPOSE_CMD} exec -T nginx nginx -t >/dev/null 2>&1; then
        print_row_colored "Nginx Reverse Proxy" "${GREEN}ONLINE (Syntax Verified)${RESET}"
    else
        print_row_colored "Nginx Reverse Proxy" "${RED}CONFIG ERROR / FAILING${RESET}"
    fi

    # SSL Expiry
    CERT_FILE=$(${DOCKER_COMPOSE_CMD} exec -T nginx sh -c 'ls -1 /etc/letsencrypt/live/*/fullchain.pem 2>/dev/null | head -1 | tr -d "\r"' || echo "")
    if [[ -n "${CERT_FILE}" ]]; then
        EXPIRY_DATE=$(${DOCKER_COMPOSE_CMD} exec -T nginx openssl x509 -in "${CERT_FILE}" -noout -enddate 2>/dev/null | cut -d= -f2- || echo "")
        if [[ -n "${EXPIRY_DATE}" ]]; then
            EXPIRY_SEC=$(date -d "${EXPIRY_DATE}" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "${EXPIRY_DATE}" +%s 2>/dev/null || echo "0")
            NOW_SEC=$(date +%s)
            DAYS_LEFT=$(( (EXPIRY_SEC - NOW_SEC) / 86400 ))

            if [[ "${DAYS_LEFT}" -le 0 ]]; then
                print_row_colored "SSL Expiry Status" "${RED}EXPIRED (${EXPIRY_DATE})${RESET}"
            elif [[ "${DAYS_LEFT}" -le 14 ]]; then
                print_row_colored "SSL Expiry Status" "${YELLOW}${DAYS_LEFT} days left (${EXPIRY_DATE})${RESET}"
            else
                print_row_colored "SSL Expiry Status" "${GREEN}${DAYS_LEFT} days left (${EXPIRY_DATE})${RESET}"
            fi
        else
            print_row "SSL Expiry Status" "Unknown / Unreadable Cert Date"
        fi
    else
        # Try local port 443 probe
        if echo | openssl s_client -connect localhost:443 -servername edunaukari.com 2>/dev/null | openssl x509 -noout -enddate >/dev/null 2>&1; then
            EXP_STR=$(echo | openssl s_client -connect localhost:443 -servername edunaukari.com 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2-)
            print_row_colored "SSL Expiry Status" "${GREEN}Active on Port 443 (${EXP_STR})${RESET}"
        else
            print_row "SSL Expiry Status" "No Live Cert (HTTP / Staging)"
        fi
    fi
else
    print_row_colored "Nginx Reverse Proxy" "${RED}OFFLINE${RESET}"
    print_row "SSL Expiry Status" "N/A (Proxy Offline)"
fi

print_footer

# ==============================================================================
# 5. DOCKER CONTAINERS & IMAGES TABLE
# ==============================================================================
echo -e "\n${BOLD}${CYAN}┌──────────────────────────────────────────────────────────────────────────────┐${RESET}"
printf "${BOLD}${CYAN}│ %-76s │${RESET}\n" "DOCKER CONTAINERS & IMAGES METRICS"
echo -e "${BOLD}${CYAN}├──────────────┬──────────────────────────────┬───────────────┬────────────────┤${RESET}"
printf "${BOLD}${CYAN}│ %-12s │ %-28s │ %-13s │ %-14s │${RESET}\n" "SERVICE" "DOCKER IMAGE" "STATUS" "HEALTH"
echo -e "${BOLD}${CYAN}├──────────────┼──────────────────────────────┼───────────────┼────────────────┤${RESET}"

# Fetch detailed container list via docker compose ps format
while IFS= read -r line; do
    if [[ -z "${line}" ]]; then continue; fi
    SVC=$(echo "${line}" | awk -F'\t' '{print $1}' | cut -c1-12)
    STATUS=$(echo "${line}" | awk -F'\t' '{print $2}' | cut -c1-13)
    HEALTH=$(echo "${line}" | awk -F'\t' '{print $3}' | cut -c1-14)
    
    # Get associated image name
    IMG=$(${DOCKER_COMPOSE_CMD} images --format json 2>/dev/null | grep -i "\"Service\": *\"${SVC}\"" | grep -o '"Repository": *"[^"]*"' | cut -d'"' -f4 | head -1 || echo "custom/build")
    if [[ -z "${IMG}" || "${IMG}" == "custom/build" ]]; then
        IMG=$(${DOCKER_COMPOSE_CMD} ps --format json "${SVC}" 2>/dev/null | grep -o '"Image": *"[^"]*"' | cut -d'"' -f4 | sed 's/.*edunaukri-//' | cut -c1-28 || echo "local-image")
    fi

    # Format health status colors
    HEALTH_COL="${HEALTH}"
    if [[ "${HEALTH}" == *"healthy"* ]]; then
        HEALTH_COL="${GREEN}${HEALTH}${RESET}"
    elif [[ "${HEALTH}" == *"unhealthy"* || "${STATUS}" == *"Exit"* ]]; then
        HEALTH_COL="${RED}${HEALTH}${RESET}"
    elif [[ -n "${HEALTH}" && "${HEALTH}" != "N/A" ]]; then
        HEALTH_COL="${YELLOW}${HEALTH}${RESET}"
    else
        HEALTH_COL="N/A"
    fi

    STATUS_COL="${STATUS}"
    if [[ "${STATUS}" == *"Up"* || "${STATUS}" == *"running"* ]]; then
        STATUS_COL="${GREEN}${STATUS}${RESET}"
    else
        STATUS_COL="${RED}${STATUS}${RESET}"
    fi

    printf "│ %-12s │ %-28s │ %-22b │ %-23b │\n" "${SVC}" "${IMG:-local}" "${STATUS_COL}" "${HEALTH_COL}"
done < <(${DOCKER_COMPOSE_CMD} ps --format "{{.Service}}\t{{.State}}\t{{.Health}}" 2>/dev/null || echo "")

echo -e "${BOLD}${CYAN}└──────────────┴──────────────────────────────┴───────────────┴────────────────┘${RESET}\n"
exit 0
