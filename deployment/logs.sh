#!/usr/bin/env bash
# ==============================================================================
# Production Interactive & CLI Logs Viewer Script (`logs.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/logs.sh
#
# Description:
#   Provides a unified interactive menu and CLI interface to inspect, stream,
#   filter, and search log output across all Docker container services and past
#   deployment run logs.
#
# Features:
#   - Interactive menu (Web, Nginx, PG, Redis, Celery Worker, Beat, Deployments)
#   - CLI flag support (--service, --tail, --grep, --follow, --since, --until)
#   - Live stream following (`docker compose logs -f`)
#   - Pattern matching via grep filtering (`--grep "ERROR|Exception"`)
#   - Date/time range filtering (`--since 1h`, `--until 10m`, `--since 2026-07-18`)
#
# Usage:
#   ./deployment/logs.sh                                  # Interactive menu
#   ./deployment/logs.sh -s web -f -n 100                 # Follow web logs (last 100)
#   ./deployment/logs.sh -s celery_worker -g "ERROR"      # Search celery logs for ERROR
#   ./deployment/logs.sh -s deploy -n 50                  # View last deployment log
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

# Detect Docker Compose command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}[ERROR] Docker Compose ('docker compose' or 'docker-compose') not found.${RESET}" >&2
    exit 1
fi

# Default CLI parameters
SELECTED_SERVICE=""
TAIL_LINES=100
FOLLOW_MODE=false
GREP_PATTERN=""
SINCE_TIME=""
UNTIL_TIME=""

# Parse command line flags
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--service)
            SELECTED_SERVICE="$2"
            shift 2
            ;;
        -n|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW_MODE=true
            shift
            ;;
        -g|--grep)
            GREP_PATTERN="$2"
            shift 2
            ;;
        --since)
            SINCE_TIME="$2"
            shift 2
            ;;
        --until)
            UNTIL_TIME="$2"
            shift 2
            ;;
        1|2|3|4|5|6|7|8)
            SELECTED_SERVICE="$1"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [-s SERVICE] [-n TAIL_LINES] [-f] [-g PATTERN] [--since TIME] [--until TIME]"
            echo "Services: web, nginx, db, redis, celery_worker, celery_beat, deploy, all"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${RESET}" >&2
            exit 1
            ;;
    esac
done

# Map menu number choices to service identifiers
map_service_choice() {
    case "$1" in
        1|web|django|daphne)    echo "web" ;;
        2|nginx|proxy)          echo "nginx" ;;
        3|db|postgres|pg)       echo "db" ;;
        4|redis|cache)          echo "redis" ;;
        5|celery_worker|worker) echo "celery_worker" ;;
        6|celery_beat|beat)     echo "celery_beat" ;;
        7|deploy|deployment)    echo "deploy" ;;
        8|all|live|combined)    echo "all" ;;
        *)                      echo "" ;;
    esac
}

# Interactive Menu if no service pre-selected
if [[ -z "${SELECTED_SERVICE}" ]]; then
    echo -e "\n${BOLD}${CYAN}┌─────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${CYAN}│                  EDUNAUKRI LOGS VIEWER MENU                 │${RESET}"
    echo -e "${BOLD}${CYAN}├─────────────────────────────────────────────────────────────┤${RESET}"
    echo -e "│  ${BOLD}${GREEN}1${RESET}) Web Logs          (Django / Daphne API Server)        │"
    echo -e "│  ${BOLD}${GREEN}2${RESET}) Nginx Logs        (Reverse Proxy & SSL Access/Errors) │"
    echo -e "│  ${BOLD}${GREEN}3${RESET}) PostgreSQL Logs   (Database Engine & Queries)         │"
    echo -e "│  ${BOLD}${GREEN}4${RESET}) Redis Logs        (Caching Tier & Persistence)        │"
    echo -e "│  ${BOLD}${GREEN}5${RESET}) Celery Worker     (Background Task Processing)        │"
    echo -e "│  ${BOLD}${GREEN}6${RESET}) Celery Beat       (Periodic Task Scheduler)           │"
    echo -e "│  ${BOLD}${GREEN}7${RESET}) Last Deployment   (deploy_*.log History)              │"
    echo -e "│  ${BOLD}${GREEN}8${RESET}) Follow Live Logs  (All Container Services Combined)   │"
    echo -e "│  ${BOLD}${RED}q${RESET}) Quit                                                  │"
    echo -e "${BOLD}${CYAN}└─────────────────────────────────────────────────────────────┘${RESET}"

    read -p "Select a log option [1-8 or q]: " choice
    if [[ "${choice}" == "q" || "${choice}" == "Q" || -z "${choice}" ]]; then
        echo -e "${BLUE}Exiting logs viewer.${RESET}"
        exit 0
    fi

    SELECTED_SERVICE=$(map_service_choice "${choice}")
    if [[ -z "${SELECTED_SERVICE}" ]]; then
        echo -e "${RED}[ERROR] Invalid menu choice: ${choice}${RESET}" >&2
        exit 1
    fi

    # Interactive prompts for filtering options if viewing via menu
    read -p "Number of tail lines to display [Default: ${TAIL_LINES}]: " input_tail
    if [[ -n "${input_tail}" && "${input_tail}" =~ ^[0-9]+$ ]]; then
        TAIL_LINES="${input_tail}"
    fi

    read -p "Filter pattern (grep string, press Enter for none): " input_grep
    if [[ -n "${input_grep}" ]]; then
        GREP_PATTERN="${input_grep}"
    fi

    read -p "Stream live logs (-f follow)? [y/N]: " input_follow
    if [[ "${input_follow}" =~ ^[Yy]$ ]]; then
        FOLLOW_MODE=true
    fi
else
    SELECTED_SERVICE=$(map_service_choice "${SELECTED_SERVICE}")
    if [[ -z "${SELECTED_SERVICE}" ]]; then
        echo -e "${RED}[ERROR] Invalid target service selected.${RESET}" >&2
        exit 1
    fi
fi

echo -e "\n${BOLD}${BLUE}--------------------------------------------------------------------------------${RESET}"
echo -e "${BOLD}${BLUE}Target Service: ${CYAN}${SELECTED_SERVICE}${BLUE} | Tail: ${CYAN}${TAIL_LINES}${BLUE} | Follow: ${CYAN}${FOLLOW_MODE}${BLUE} | Filter: ${CYAN}${GREP_PATTERN:-none}${RESET}"
echo -e "${BOLD}${BLUE}--------------------------------------------------------------------------------${RESET}\n"

# Handle special case: Last Deployment Log viewing
if [[ "${SELECTED_SERVICE}" == "deploy" ]]; then
    DEPLOY_LOGS_DIR="${PROJECT_ROOT}/logs/deployment"
    LATEST_LOG=$(find "${DEPLOY_LOGS_DIR}" -name "deploy_*.log" -type f 2>/dev/null | sort -r | head -1 || echo "")

    if [[ -z "${LATEST_LOG}" || ! -f "${LATEST_LOG}" ]]; then
        echo -e "${YELLOW}[WARNING] No past deployment logs (deploy_*.log) found in ${DEPLOY_LOGS_DIR}.${RESET}"
        exit 0
    fi

    echo -e "${BOLD}${CYAN}Displaying deployment log file: ${LATEST_LOG}${RESET}\n"

    if [[ "${FOLLOW_MODE}" == "true" ]]; then
        if [[ -n "${GREP_PATTERN}" ]]; then
            tail -n "${TAIL_LINES}" -f "${LATEST_LOG}" | grep --color=always -E "${GREP_PATTERN}"
        else
            tail -n "${TAIL_LINES}" -f "${LATEST_LOG}"
        fi
    else
        if [[ -n "${GREP_PATTERN}" ]]; then
            tail -n "${TAIL_LINES}" "${LATEST_LOG}" | grep --color=always -E "${GREP_PATTERN}" || echo -e "${YELLOW}No matching lines for filter '${GREP_PATTERN}'.${RESET}"
        else
            tail -n "${TAIL_LINES}" "${LATEST_LOG}"
        fi
    fi
    exit 0
fi

# Build Docker Compose logs command arguments array
CMD_ARGS=("logs" "--tail=${TAIL_LINES}")

if [[ "${FOLLOW_MODE}" == "true" ]]; then
    CMD_ARGS+=("-f")
fi

if [[ -n "${SINCE_TIME}" ]]; then
    CMD_ARGS+=("--since=${SINCE_TIME}")
fi

if [[ -n "${UNTIL_TIME}" ]]; then
    CMD_ARGS+=("--until=${UNTIL_TIME}")
fi

# Add target container service if not 'all'
if [[ "${SELECTED_SERVICE}" != "all" ]]; then
    CMD_ARGS+=("${SELECTED_SERVICE}")
fi

# Execute command and pipe through grep if filter specified
if [[ -n "${GREP_PATTERN}" ]]; then
    # --no-log-prefix can be omitted or kept depending on desired output format
    ${DOCKER_COMPOSE_CMD} "${CMD_ARGS[@]}" 2>&1 | grep --color=always -E "${GREP_PATTERN}" || echo -e "${YELLOW}No matching lines found for pattern '${GREP_PATTERN}'.${RESET}"
else
    ${DOCKER_COMPOSE_CMD} "${CMD_ARGS[@]}" 2>&1
fi

exit 0
