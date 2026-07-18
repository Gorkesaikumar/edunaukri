#!/usr/bin/env bash
# ==============================================================================
# Production System Cleanup & Pruning Script (`clean.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/clean.sh
#
# Description:
#   Safely cleans up orphaned resources, intermediate build caches, dangling
#   Docker images, unused containers and networks, aged deployment logs, and
#   expired backup archives. Calculates and displays exact disk space recovered.
#   Requires explicit user confirmation before executing general cleanup, plus
#   an additional dedicated confirmation prompt before pruning unused Docker volumes.
#
# Responsibilities:
#   1. Require general cleanup confirmation (`[y/N]`) or `--force` flag
#   2. Prune dangling Docker images (`docker image prune`)
#   3. Prune stopped/unused containers (`docker container prune`)
#   4. Prune unused Docker networks (`docker network prune`)
#   5. Prune intermediate Docker build cache (`docker builder prune`)
#   6. Prune unused Docker volumes with dedicated confirmation (`docker volume prune`)
#   7. Purge old deployment logs older than 14 days (`logs/deployment/*.log`)
#   8. Purge old backup archives older than 14 days (`backups/`)
#   9. Calculate and display exact disk space recovered (in KB/MB/GB)
#
# Usage:
#   ./deployment/clean.sh              # Interactive confirmation prompts
#   ./deployment/clean.sh --force      # Skip general prompt (still asks for volumes)
#   ./deployment/clean.sh --all        # Skip all prompts (prunes everything including volumes)
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
LOG_FILE="${LOGS_DIR}/clean_${LOG_TIMESTAMP}.log"

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

FORCE_GENERAL=false
FORCE_VOLUMES=false

# Parse command line flags
for arg in "$@"; do
    case "${arg}" in
        -f|--force)
            FORCE_GENERAL=true
            ;;
        --prune-volumes)
            FORCE_VOLUMES=true
            ;;
        --all)
            FORCE_GENERAL=true
            FORCE_VOLUMES=true
            ;;
        -h|--help)
            echo "Usage: $0 [-f|--force] [--prune-volumes] [--all]"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: ${arg}${RESET}" >&2
            exit 1
            ;;
    esac
done

log_header "PRODUCTION DOCKER & SYSTEM RESOURCE CLEANUP"
log_info "Project Root: ${PROJECT_ROOT}"
log_info "Log File:     ${LOG_FILE}"

# Verify Docker availability before proceeding
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    log_error "Docker binary not found or daemon is not responsive!"
    exit 1
fi

# ------------------------------------------------------------------------------
# 1. Require Confirmation Before Executing Cleanup
# ------------------------------------------------------------------------------
if [[ "${FORCE_GENERAL}" != "true" ]]; then
    echo -e "\n${BOLD}${YELLOW}┌──────────────────────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${YELLOW}│ WARNING: You are about to run system cleanup. This will permanently remove: │${RESET}"
    echo -e "${BOLD}${YELLOW}│   - All dangling/untagged Docker images                                      │${RESET}"
    echo -e "${BOLD}${YELLOW}│   - All stopped/inactive Docker containers and networks                      │${RESET}"
    echo -e "${BOLD}${YELLOW}│   - Intermediate Docker build caches                                         │${RESET}"
    echo -e "${BOLD}${YELLOW}│   - Old deployment logs and backup archives older than 14 days               │${RESET}"
    echo -e "${BOLD}${YELLOW}└──────────────────────────────────────────────────────────────────────────────┘${RESET}"
    
    read -p "Are you sure you want to proceed with system cleanup? [y/N]: " confirm_general
    if [[ ! "${confirm_general}" =~ ^[Yy]$ ]]; then
        log_info "Cleanup operation cancelled by user."
        exit 0
    fi
fi

# Capture initial available disk space (in kilobytes) on root filesystem
INITIAL_FREE_KB=$(df -k / | awk 'NR==2 {print $4}')

# ------------------------------------------------------------------------------
# 2. Prune Dangling Images
# ------------------------------------------------------------------------------
log_header "STEP 1: Pruning Dangling Docker Images"
log_info "Removing untagged and dangling Docker images (`docker image prune -f`)..."
docker image prune -f
log_success "Dangling images pruned cleanly."

# ------------------------------------------------------------------------------
# 3. Prune Unused Containers
# ------------------------------------------------------------------------------
log_header "STEP 2: Pruning Unused & Stopped Containers"
log_info "Removing all stopped container instances (`docker container prune -f`)..."
docker container prune -f
log_success "Stopped containers removed."

# ------------------------------------------------------------------------------
# 4. Prune Unused Networks
# ------------------------------------------------------------------------------
log_header "STEP 3: Pruning Unused Docker Networks"
log_info "Removing orphaned Docker networks (`docker network prune -f`)..."
docker network prune -f
log_success "Unused networks cleaned up."

# ------------------------------------------------------------------------------
# 5. Prune Build Cache
# ------------------------------------------------------------------------------
log_header "STEP 4: Pruning Intermediate Build Cache"
log_info "Reclaiming disk space from intermediate build layer caches (`docker builder prune -f`)..."
docker builder prune -f || docker system prune -f --filter "label!=preserve"
log_success "Build cache purged successfully."

# ------------------------------------------------------------------------------
# 6. Prune Unused Volumes (Requires Dedicated Confirmation)
# ------------------------------------------------------------------------------
log_header "STEP 5: Unused Docker Volumes Cleanup"

if [[ "${FORCE_VOLUMES}" != "true" ]]; then
    echo -e "\n${BOLD}${RED}┌──────────────────────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${RED}│ CRITICAL WARNING: Pruning unused Docker volumes will PERMANENTLY DELETE      │${RESET}"
    echo -e "${BOLD}${RED}│ any database volumes, redis storage, or static assets not currently attached │${RESET}"
    echo -e "${BOLD}${RED}│ to a running container!                                                      │${RESET}"
    echo -e "${BOLD}${RED}└──────────────────────────────────────────────────────────────────────────────┘${RESET}"
    
    read -p "Do you want to PRUNE UNUSED DOCKER VOLUMES? [y/N]: " confirm_volumes
    if [[ "${confirm_volumes}" =~ ^[Yy]$ ]]; then
        FORCE_VOLUMES=true
    fi
fi

if [[ "${FORCE_VOLUMES}" == "true" ]]; then
    log_info "Removing unreferenced Docker volumes (`docker volume prune -f`)..."
    docker volume prune -f
    log_success "Unused Docker volumes pruned."
else
    log_info "Skipping Docker volume pruning to preserve offline data."
fi

# ------------------------------------------------------------------------------
# 7. Purge Old Deployment Logs Older Than 14 Days
# ------------------------------------------------------------------------------
log_header "STEP 6: Purging Old Deployment Logs (>14 Days)"
log_info "Scanning ${LOGS_DIR} for log files older than 14 days..."

LOGS_REMOVED=$(find "${LOGS_DIR}" -type f -name "*.log" -mtime +14 -print | wc -l | tr -d ' ')
if [[ "${LOGS_REMOVED}" -gt 0 ]]; then
    find "${LOGS_DIR}" -type f -name "*.log" -mtime +14 -delete
    log_success "Removed ${LOGS_REMOVED} aged log file(s)."
else
    log_info "No deployment logs older than 14 days found."
fi

# ------------------------------------------------------------------------------
# 8. Purge Old Backups Older Than 14 Days
# ------------------------------------------------------------------------------
log_header "STEP 7: Purging Old Backups (>14 Days)"
BACKUPS_DIR="${PROJECT_ROOT}/backups"

if [[ -d "${BACKUPS_DIR}" ]]; then
    log_info "Scanning ${BACKUPS_DIR} for archive files (.gz/.sql/.tar) older than 14 days..."
    BACKUPS_REMOVED=$(find "${BACKUPS_DIR}" -type f \( -name "*.gz" -o -name "*.sql" -o -name "*.tar" \) -mtime +14 -print | wc -l | tr -d ' ')
    if [[ "${BACKUPS_REMOVED}" -gt 0 ]]; then
        find "${BACKUPS_DIR}" -type f \( -name "*.gz" -o -name "*.sql" -o -name "*.tar" \) -mtime +14 -delete
        log_success "Removed ${BACKUPS_REMOVED} expired backup archive(s)."
    else
        log_info "No backup archives older than 14 days found."
    fi
else
    log_info "Backups directory (${BACKUPS_DIR}) does not exist yet; skipping."
fi

# ------------------------------------------------------------------------------
# 9. Calculate and Display Recovered Disk Space
# ------------------------------------------------------------------------------
log_header "CLEANUP SUMMARY & RECOVERED DISK SPACE"

FINAL_FREE_KB=$(df -k / | awk 'NR==2 {print $4}')
RECOVERED_KB=$((FINAL_FREE_KB - INITIAL_FREE_KB))

# Format recovered space
if [[ "${RECOVERED_KB}" -le 0 ]]; then
    RECOVERED_STR="0 B (No significant disk space difference measured)"
elif [[ "${RECOVERED_KB}" -ge 1048576 ]]; then
    # Convert to GB with 2 decimal places using awk
    RECOVERED_STR=$(awk -v kb="${RECOVERED_KB}" 'BEGIN {printf "%.2f GB", kb / 1048576}')
elif [[ "${RECOVERED_KB}" -ge 1024 ]]; then
    # Convert to MB with 2 decimal places using awk
    RECOVERED_STR=$(awk -v kb="${RECOVERED_KB}" 'BEGIN {printf "%.2f MB", kb / 1024}')
else
    RECOVERED_STR="${RECOVERED_KB} KB"
fi

log_info "Initial Free Space: $(awk -v kb="${INITIAL_FREE_KB}" 'BEGIN {printf "%.2f GB", kb / 1048576}')"
log_info "Final Free Space:   $(awk -v kb="${FINAL_FREE_KB}" 'BEGIN {printf "%.2f GB", kb / 1048576}')"
echo -e "\n${BOLD}${GREEN}✔ Total Disk Space Recovered: ${RECOVERED_STR}${RESET}\n"

log_success "Production system cleanup completed successfully."
exit 0
