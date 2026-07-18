#!/usr/bin/env bash
# ==============================================================================
# Production Interactive Container Shell Launcher (`shell.sh`)
# ==============================================================================
# Suite:       Django + Daphne + Celery + Nginx + PostgreSQL + Redis
# Directory:   ./deployment/shell.sh
#
# Description:
#   Provides an interactive menu and direct CLI interface to open interactive
#   terminal sessions (TTY) into any running Docker service container.
#   Automatically resolves container names, loads database credentials from .env
#   for PostgreSQL psql, and handles fallback shells (`sh` vs `bash`).
#
# Menu Options:
#   1. Django shell     (`python manage.py shell` inside `web` container)
#   2. Bash shell       (`bash` / `sh` terminal inside `web` container)
#   3. PostgreSQL shell (`psql` interactive prompt inside `db` container)
#   4. Redis CLI        (`redis-cli` interactive prompt inside `redis` container)
#   5. Celery shell     (`bash` / `sh` terminal inside `celery_worker` container)
#   6. Nginx shell      (`sh` terminal inside `nginx` reverse proxy container)
#
# Usage:
#   ./deployment/shell.sh           # Open interactive menu
#   ./deployment/shell.sh 1         # Open Django shell directly
#   ./deployment/shell.sh psql      # Open PostgreSQL shell directly
# ==============================================================================

set -uo pipefail

# Determine script and project root directories dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Load optional deployment environment overrides
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
    RESET='\033[0m'
else
    BOLD='' CYAN='' GREEN='' YELLOW='' RED='' BLUE='' RESET=''
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

# Verify Docker daemon responsiveness
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Docker daemon is not running or socket connection denied.${RESET}" >&2
    exit 1
fi

CHOICE="${1:-}"

# Display Interactive Menu if no argument provided
if [[ -z "${CHOICE}" ]]; then
    echo -e "\n${BOLD}${CYAN}┌─────────────────────────────────────────────────────────────┐${RESET}"
    echo -e "${BOLD}${CYAN}│             EDUNAUKRI INTERACTIVE SHELL MENU                │${RESET}"
    echo -e "${BOLD}${CYAN}├─────────────────────────────────────────────────────────────┤${RESET}"
    echo -e "│  ${BOLD}${GREEN}1${RESET}) Django shell     (python manage.py shell in web)      │"
    echo -e "│  ${BOLD}${GREEN}2${RESET}) Bash shell       (Interactive bash/sh in web)         │"
    echo -e "│  ${BOLD}${GREEN}3${RESET}) PostgreSQL shell (psql prompt in db container)       │"
    echo -e "│  ${BOLD}${GREEN}4${RESET}) Redis CLI        (redis-cli prompt in redis)          │"
    echo -e "│  ${BOLD}${GREEN}5${RESET}) Celery shell     (Interactive terminal in worker)     │"
    echo -e "│  ${BOLD}${GREEN}6${RESET}) Nginx shell      (Interactive sh in proxy container)  │"
    echo -e "│  ${BOLD}${RED}q${RESET}) Quit                                                  │"
    echo -e "${BOLD}${CYAN}└─────────────────────────────────────────────────────────────┘${RESET}"

    read -p "Select a shell option [1-6 or q]: " choice_input
    if [[ "${choice_input}" == "q" || "${choice_input}" == "Q" || -z "${choice_input}" ]]; then
        echo -e "${BLUE}Exiting shell launcher.${RESET}"
        exit 0
    fi
    CHOICE="${choice_input}"
fi

# Verify container is running before attempting attachment
check_service_running() {
    local svc="$1"
    if ! ${DOCKER_COMPOSE_CMD} ps --services --filter "status=running" 2>/dev/null | grep -q "^${svc}$"; then
        echo -e "${RED}[ERROR] Target service container '${svc}' is NOT running! Cannot open shell.${RESET}" >&2
        exit 1
    fi
}

# Execute requested shell connection
case "${CHOICE}" in
    1|django|web-shell)
        check_service_running "web"
        echo -e "${BLUE}[INFO] Opening Django Python interactive shell inside 'web' container...${RESET}"
        # Try shell_plus first if django-extensions is installed, otherwise fallback to regular shell
        ${DOCKER_COMPOSE_CMD} exec web python manage.py shell_plus 2>/dev/null || \
        ${DOCKER_COMPOSE_CMD} exec web python manage.py shell
        ;;
    2|bash|web|sh)
        check_service_running "web"
        echo -e "${BLUE}[INFO] Opening interactive bash/sh terminal inside 'web' container...${RESET}"
        ${DOCKER_COMPOSE_CMD} exec web bash 2>/dev/null || \
        ${DOCKER_COMPOSE_CMD} exec web sh
        ;;
    3|postgres|psql|db)
        check_service_running "db"
        DB_USER=$(grep -E '^(POSTGRES_USER|DB_USER)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
        DB_NAME=$(grep -E '^(POSTGRES_DB|DB_NAME)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")
        DB_PASS=$(grep -E '^(POSTGRES_PASSWORD|DB_PASSWORD)=' "${PROJECT_ROOT}/.env" | tail -1 | cut -d '=' -f2- | tr -d '"'\'' ' || echo "edunaukri")

        echo -e "${BLUE}[INFO] Connecting to PostgreSQL database '${DB_NAME}' as user '${DB_USER}'...${RESET}"
        ${DOCKER_COMPOSE_CMD} exec -e PGPASSWORD="${DB_PASS}" db psql -U "${DB_USER}" -d "${DB_NAME}"
        ;;
    4|redis|redis-cli|cache)
        check_service_running "redis"
        echo -e "${BLUE}[INFO] Opening Redis CLI inside 'redis' container...${RESET}"
        ${DOCKER_COMPOSE_CMD} exec redis redis-cli
        ;;
    5|celery|celery_worker|worker)
        check_service_running "celery_worker"
        echo -e "${BLUE}[INFO] Opening interactive terminal inside 'celery_worker' container...${RESET}"
        ${DOCKER_COMPOSE_CMD} exec celery_worker bash 2>/dev/null || \
        ${DOCKER_COMPOSE_CMD} exec celery_worker sh
        ;;
    6|nginx|proxy)
        check_service_running "nginx"
        echo -e "${BLUE}[INFO] Opening interactive shell inside 'nginx' reverse proxy container...${RESET}"
        ${DOCKER_COMPOSE_CMD} exec nginx sh 2>/dev/null || \
        ${DOCKER_COMPOSE_CMD} exec nginx bash
        ;;
    *)
        echo -e "${RED}[ERROR] Invalid option selected: '${CHOICE}'${RESET}" >&2
        echo -e "${YELLOW}Valid choices: 1 (Django), 2 (Bash), 3 (PostgreSQL), 4 (Redis), 5 (Celery), 6 (Nginx)${RESET}"
        exit 1
        ;;
esac

echo -e "${GREEN}[INFO] Shell session closed cleanly.${RESET}"
exit 0
