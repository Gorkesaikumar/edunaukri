# EduNaukri Comprehensive System & Application Monitoring Engine

This directory (`docker/monitoring`) houses external watchdog tools and documentation for the full-stack diagnostic and automated alerting architecture across **EduNaukri**.

---

## 🏛️ Monitoring Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │       External Watchdog / Celery Beat        │
                    └──────────────────────┬───────────────────────┘
                                           │ HTTP Probe / Periodic Task
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │     SystemHealthMonitoringService (core)     │
                    └─┬─────────┬──────────────┬─────────────┬───┴──┬───────────┐
                      │         │              │             │      │           │
    ┌─────────────────┘         │              │             │      │           └────────────────────┐
    ▼                           ▼              ▼             ▼      ▼                                ▼
┌───────┐                  ┌─────────┐   ┌───────────┐   ┌────────┐┌──────┐                     ┌───────────────┐
│ Disk  │                  │ CPU/RAM │   │PostgreSQL │   │ Redis  ││Celery│                     │ Uptime & Env  │
│(3 dirs)                  │ (psutil)│   │(pg_stat*) │   │(ping/i)││(insp)│                     │  (time/boot)  │
└───────┘                  └─────────┘   └───────────┘   └────────┘└──────┘                     └───────────────┘
    │                           │              │             │      │                                │
    └───────────────────────────┴───────┬──────┴─────────────┴──────┴────────────────────────────────┘
                                        │ Aggregates metrics & evaluates thresholds
                                        ▼
                   ┌─────────────────────────────────────────┐
                   │  Threshold Evaluation & Email Alerting  │
                   │   (send_mail to settings.ADMINS)        │
                   └─────────────────────────────────────────┘
```

---

## 📡 Diagnostic Endpoints

All endpoints return standardized JSON format compatible with external monitors, Prometheus/Grafana scrapers, and uptime checkers:

| HTTP Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health/` | **Liveness Probe**: Fast response (`{"status": "healthy"}`) ensuring the server process is alive. |
| `GET` | `/api/v1/health/ready/` | **Readiness Probe**: Checks that PostgreSQL, Redis, and Celery brokers are connectable (`{"status": "healthy", "checks": {...}}`). |
| `GET` | `/api/v1/health/metrics/` | **Full System Metrics**: Returns real-time diagnostics across CPU, RAM, Disk, Redis, Celery, Database, and Uptime. |
| `GET` | `/api/v1/health/check-alerts/`| **Threshold Evaluation & Alerting**: Aggregates diagnostics, evaluates all warning/critical thresholds, and dispatches email notifications if breaches occur. |

---

## ⚙️ Configurable Monitoring Thresholds

You can tune the alerting sensitivity by overriding these variables in `config/settings/production.py` or `.env`:

| Setting Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MONITORING_DISK_WARNING_PERCENT` | `85.0%` | Triggers a **WARNING** email alert when any disk mount point exceeds this utilization. |
| `MONITORING_DISK_CRITICAL_PERCENT`| `95.0%` | Triggers a **CRITICAL** email alert when any disk mount point exceeds this utilization. |
| `MONITORING_CPU_WARNING_PERCENT` | `85.0%` | Triggers a **WARNING** email alert when sustained CPU utilization exceeds this limit. |
| `MONITORING_RAM_WARNING_PERCENT` | `85.0%` | Triggers a **WARNING** email alert when RAM usage exceeds this limit. |
| `MONITORING_DB_CONN_WARNING_PERCENT`| `80.0%` | Triggers a **WARNING** when active database connections exceed 80% of `max_connections`. |
| `MONITORING_FAILED_JOBS_THRESHOLD`| `10` | Triggers a **WARNING** when more than 10 Celery tasks fail within a 24-hour window. |

---

## 🖥️ Command-Line Execution & Cron Scheduling

### Run Full Diagnostic Check & Send Alerts from CLI
You can run the Django management command on demand from inside the web or worker container:
```bash
# Run diagnostics and dispatch email alerts if any breaches exist
docker compose exec web python manage.py check_system_health --send-alerts

# View full diagnostic report in terminal (without sending emails)
docker compose exec web python manage.py check_system_health --no-alerts

# Output formatted JSON metrics for automation
docker compose exec web python manage.py check_system_health --no-alerts --json
```

### Schedule Automated Checks via Cron or Celery Beat
To run checks continuously every 15 minutes, add a periodic task in **Celery Beat** or in the backup container's `crontab`:

#### Option A: Via Celery Beat (Periodic Tasks)
In your `config/settings/base.py` or `production.py`:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "system-health-check-and-alert": {
        "task": "apps.health.tasks.run_health_check_alert",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
}
```

#### Option B: Via External Watchdog (`docker/monitoring/watchdog.py`)
Run the standalone watchdog outside the main Django process to continuously probe the endpoints:
```bash
python3 /app/docker/monitoring/watchdog.py --url http://localhost:8000/api/v1/health/check-alerts/
```
