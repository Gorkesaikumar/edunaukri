# EduNaukri Automated Backup & Disaster Recovery Engine

This directory (`docker/backup`) contains the enterprise-grade automated backup, retention, and self-verifying restoration suite for **EduNaukri**.

---

## 🏛️ Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Cron Daemon / Manual Invocation                       │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Trigger: Daily (02:00 UTC) / Weekly (Sun 03:00 UTC)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       backup.sh (Master Orchestrator)                       │
├─────────────────┬───────────────────┬──────────────────┬────────────────────┤
│ 1. PostgreSQL   │ 2. Media Files    │ 3. App Logs      │ 4. System Config   │
│    (pg_dump -Fc)│    (tar -czf)     │    (tar -czf)    │    (tar -czf)      │
└────────┬────────┴─────────┬─────────┴────────┬─────────┴─────────┬──────────┘
         │                  │                  │                   │
         ▼                  ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              /backups/daily/ & /backups/weekly/ Volume Storage              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Immediate Automated Test
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 restore-test.sh (Isolated Verification Loop)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Boots isolated, temporary PostgreSQL cluster on port 5433 (zero DB load)  │
│ • Restores database dump cleanly via pg_restore                             │
│ • Executes data integrity & schema validation queries (SELECT count(*)...)  │
│ • Verifies Media & Config tarball gzip/archive integrity                    │
│ • Outputs PASSED/FAILED report & cleans up temporary scratch cluster        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 What Gets Backed Up

| Component | Format | Source | Description |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Database** | Custom Compressed (`.dump`) | `db:5432` | Full PostgreSQL database backup (`pg_dump -Fc`). Supports parallel restore, selective table restoration, and direct validation. |
| **Media Files** | Gzipped Archive (`.tar.gz`) | `/app/media` | User uploaded candidate resumes, profile images, institutional documents, and video attachments. |
| **Application Logs** | Gzipped Archive (`.tar.gz`) | `/app/logs` | Historical application and security audit logs. |
| **System Configuration**| Gzipped Archive (`.tar.gz`) | `/app/config_source` | Core environment configurations and deployment settings. |

---

## ⏰ Cron Schedules & Retention Policies

The backup service runs via Alpine `crond` using the schedules in `crontab`:

* **Daily Backups (`0 2 * * *`)**: Runs every night at **02:00 UTC**.
  * **Retention**: Kept for **7 days** (`BACKUP_RETENTION_DAILY=7`). Older daily archives are automatically pruned.
* **Weekly Backups (`0 3 * * 0`)**: Runs every Sunday night at **03:00 UTC**.
  * **Retention**: Kept for **5 weeks** (`BACKUP_RETENTION_WEEKLY=5`). Older weekly archives are automatically pruned.

---

## 🧪 Automated Restore Verification (`restore-test.sh`)

Every time `backup.sh` completes a backup, it immediately runs `restore-test.sh` to ensure the backup is structurally sound and truly restorable:
1. **Isolated Sandbox**: Initializes a temporary database directory inside `/tmp/restore_test_XXXXXX` and boots an isolated Postgres server on port `5433` (bound to `127.0.0.1` with `fsync=off` for speed). This has **zero performance impact** on your live production database on port `5432`.
2. **Real Restoration**: Restores the custom compressed dump using `pg_restore` into a test database (`test_restore_db`).
3. **Validation**: Queries schema table counts (`information_schema.tables`) and database size to confirm structural completeness.
4. **Tarball Checks**: Runs `tar -tzf` across `media_*.tar.gz` and `config_*.tar.gz` to verify file headers and gzip integrity.
5. **Clean Teardown**: Shuts down the temporary server and removes temporary directories.
6. **Logging**: Reports status directly to `/backups/logs/restore_test_latest.log` and main cron logs.

---

## 🚨 Disaster Recovery & Manual Operations

### Run a Manual Backup On-Demand
```bash
# Run an immediate daily-style backup with verification
docker compose exec backup /app/docker/backup/backup.sh daily

# Run an immediate weekly-style backup with verification
docker compose exec backup /app/docker/backup/backup.sh weekly
```

### Perform a Disaster Recovery Restore
To restore the latest daily backup into the live production database and unpack media files:
```bash
# Interactive mode (will prompt for 'RESTORE' confirmation)
docker compose exec backup /app/docker/backup/restore.sh daily latest

# Non-interactive / emergency automated restore of a specific timestamp
docker compose exec backup /app/docker/backup/restore.sh daily 2026-07-17_02-00-00 --force
```

### Check Backup Logs and Verification Status
```bash
# View recent cron executions and backup reports
docker compose logs -f backup

# View the latest automated verification report
docker compose exec backup cat /backups/logs/restore_test_latest.log
```
