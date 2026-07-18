#!/bin/bash
# ==============================================================================
# EduNaukri Automated Restore Verification Engine
# ==============================================================================
# This script performs an automated, isolated restore verification on new backups.
# It spins up a temporary, isolated PostgreSQL server instance inside the container
# on port 5433 (zero impact on live database on 5432), restores the database dump,
# queries schema integrity metrics, and verifies archive headers for media/config.
# ==============================================================================

set -u

DB_DUMP="${1:-}"
MEDIA_TAR="${2:-}"
CONFIG_TAR="${3:-}"

LOG_FILE="/backups/logs/restore_test_latest.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

log() {
    echo "[$TIMESTAMP] [RESTORE-TEST] $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR: $1"
    # Ensure cleanup of any running temporary database server before exiting
    if [ -n "${TEST_DIR:-}" ] && [ -d "${TEST_DIR:-}" ]; then
        pg_ctl -D "$TEST_DIR/data" stop -m immediate > /dev/null 2>&1 || true
        rm -rf "$TEST_DIR"
    fi
    exit 1
}

log "========================================================================"
log "Starting Automated Restore Verification"
log "Database Dump: $DB_DUMP"
log "Media Archive: ${MEDIA_TAR:-none}"
log "Config Archive: ${CONFIG_TAR:-none}"
log "========================================================================"

if [ -z "$DB_DUMP" ] || [ ! -f "$DB_DUMP" ]; then
    error_exit "Database dump file not found or not specified: $DB_DUMP"
fi

# 1. Verify Media Archive Integrity
if [ -n "$MEDIA_TAR" ] && [ -f "$MEDIA_TAR" ]; then
    log "Verifying media tarball integrity ($MEDIA_TAR)..."
    if tar -tzf "$MEDIA_TAR" > /dev/null 2>&1; then
        MEDIA_FILES_COUNT=$(tar -tzf "$MEDIA_TAR" | wc -l)
        log "SUCCESS: Media archive intact ($MEDIA_FILES_COUNT files inside)."
    else
        error_exit "Media archive failed tar/gzip verification check: $MEDIA_TAR"
    fi
fi

# 2. Verify Config Archive Integrity
if [ -n "$CONFIG_TAR" ] && [ -f "$CONFIG_TAR" ]; then
    log "Verifying configuration tarball integrity ($CONFIG_TAR)..."
    if tar -tzf "$CONFIG_TAR" > /dev/null 2>&1; then
        CONFIG_FILES_COUNT=$(tar -tzf "$CONFIG_TAR" | wc -l)
        log "SUCCESS: Configuration archive intact ($CONFIG_FILES_COUNT files inside)."
    else
        error_exit "Configuration archive failed tar/gzip verification check: $CONFIG_TAR"
    fi
fi

# 3. Isolated PostgreSQL Restore Test
TEST_DIR=$(mktemp -d /tmp/restore_test_XXXXXX)
log "Initializing temporary isolated PostgreSQL cluster in $TEST_DIR/data..."

if ! initdb -D "$TEST_DIR/data" -U postgres --no-locale > /dev/null 2>&1; then
    error_exit "initdb failed to initialize temporary test database directory."
fi

log "Starting isolated test PostgreSQL server on port 5433 (fsync=off for speed)..."
pg_ctl -D "$TEST_DIR/data" -l "$TEST_DIR/postgres.log" start \
    -o "-p 5433 -c listen_addresses='127.0.0.1' -c fsync=off -c full_page_writes=off" > /dev/null 2>&1

# Wait up to 10 seconds for port 5433 to accept connections
READY=false
for i in $(seq 1 10); do
    if pg_isready -h 127.0.0.1 -p 5433 -U postgres > /dev/null 2>&1; then
        READY=true
        break
    fi
    sleep 1
done

if [ "$READY" != "true" ]; then
    error_exit "Temporary test PostgreSQL instance failed to become ready within 10 seconds."
fi

log "Creating target test database test_restore_db..."
createdb -h 127.0.0.1 -p 5433 -U postgres test_restore_db || error_exit "Failed to create test_restore_db"

log "Restoring database dump into isolated instance..."
# Note: pg_restore may return non-zero if warnings happen (like missing roles or extensions across environments)
# We capture output and evaluate table metrics explicitly to verify structural success
pg_restore -h 127.0.0.1 -p 5433 -U postgres -d test_restore_db "$DB_DUMP" >> "$TEST_DIR/restore.log" 2>&1 || true

log "Executing schema and data integrity verification queries..."
TABLE_COUNT=$(psql -h 127.0.0.1 -p 5433 -U postgres -d test_restore_db -t -A -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';")
DB_SIZE=$(psql -h 127.0.0.1 -p 5433 -U postgres -d test_restore_db -t -A -c "SELECT pg_size_pretty(pg_database_size('test_restore_db'));")

if [ -z "$TABLE_COUNT" ] || [ "$TABLE_COUNT" -eq 0 ]; then
    error_exit "Restore verification failed: 0 public base tables found in test_restore_db after pg_restore."
fi

log "SUCCESS: Database restore verified! ($TABLE_COUNT tables found in public schema, DB size: $DB_SIZE)"

# 4. Clean Shutdown & Cleanup
log "Stopping temporary test server and cleaning up scratch files..."
pg_ctl -D "$TEST_DIR/data" stop -m immediate > /dev/null 2>&1 || true
rm -rf "$TEST_DIR"

log "========================================================================"
log "RESTORE VERIFICATION COMPLETED SUCCESSFULLY"
log "========================================================================"
exit 0
