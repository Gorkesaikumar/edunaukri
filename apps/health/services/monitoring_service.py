"""System and Application Diagnostic Monitoring & Alerting Service."""

import logging
import os
import shutil
import sys
import time
from datetime import timedelta
from typing import Any, Dict, List, Tuple

import django
from django.conf import settings
from django.core.mail import send_mail
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)

# Process start time anchor to calculate application uptime precisely
PROCESS_START_TIME = time.time()

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SystemHealthMonitoringService:
    """Core diagnostic and metrics aggregation service with automated email alerting."""

    # Configurable monitoring thresholds
    DISK_WARNING_THRESHOLD_PERCENT = getattr(settings, "MONITORING_DISK_WARNING_PERCENT", 85.0)
    DISK_CRITICAL_THRESHOLD_PERCENT = getattr(settings, "MONITORING_DISK_CRITICAL_PERCENT", 95.0)
    CPU_WARNING_THRESHOLD_PERCENT = getattr(settings, "MONITORING_CPU_WARNING_PERCENT", 85.0)
    RAM_WARNING_THRESHOLD_PERCENT = getattr(settings, "MONITORING_RAM_WARNING_PERCENT", 85.0)
    DB_CONN_WARNING_PERCENT = getattr(settings, "MONITORING_DB_CONN_WARNING_PERCENT", 80.0)
    FAILED_JOBS_ALERT_THRESHOLD = getattr(settings, "MONITORING_FAILED_JOBS_THRESHOLD", 10)

    @classmethod
    def collect_all_diagnostics(cls) -> Dict[str, Any]:
        """Aggregate real-time diagnostics across CPU, RAM, Disk, DB, Redis, Celery, and Uptime."""
        system_metrics = cls.get_system_metrics()
        db_metrics = cls.get_database_metrics()
        redis_metrics = cls.get_redis_metrics()
        celery_metrics = cls.get_celery_metrics()
        app_metrics = cls.get_application_metrics()

        # Determine overall system health status
        component_statuses = [
            db_metrics.get("status", "error"),
            redis_metrics.get("status", "error"),
            celery_metrics.get("status", "error"),
        ]

        if all(status == "ok" for status in component_statuses):
            overall_status = "healthy"
        elif any(status == "error" for status in component_statuses):
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "timestamp": timezone.now().isoformat(),
            "status": overall_status,
            "system": system_metrics,
            "database": db_metrics,
            "redis": redis_metrics,
            "celery": celery_metrics,
            "application": app_metrics,
        }

    @classmethod
    def get_system_metrics(cls) -> Dict[str, Any]:
        """Retrieve Disk, CPU, and RAM utilization metrics."""
        metrics = {
            "cpu": {"status": "ok", "usage_percent": 0.0, "load_average": [0.0, 0.0, 0.0]},
            "ram": {"status": "ok", "total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "usage_percent": 0.0},
            "disk": {},
        }

        # Disk Monitoring across critical mount points
        mount_points = [
            ("root", "/"),
            ("media", getattr(settings, "MEDIA_ROOT", "/app/media")),
            ("backups", "/backups"),
        ]

        for label, path in mount_points:
            try:
                if os.path.exists(path):
                    usage = shutil.disk_usage(path)
                    total_gb = round(usage.total / (1024**3), 2)
                    used_gb = round(usage.used / (1024**3), 2)
                    free_gb = round(usage.free / (1024**3), 2)
                    percent = round((usage.used / usage.total) * 100, 2) if usage.total > 0 else 0.0

                    status = "ok"
                    if percent >= cls.DISK_CRITICAL_THRESHOLD_PERCENT:
                        status = "critical"
                    elif percent >= cls.DISK_WARNING_THRESHOLD_PERCENT:
                        status = "warning"

                    metrics["disk"][label] = {
                        "status": status,
                        "path": path,
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "usage_percent": percent,
                    }
            except Exception as e:
                logger.warning(f"Failed to check disk usage for path {path}: {e}")
                metrics["disk"][label] = {"status": "error", "path": path, "error": str(e)}

        # CPU and RAM via psutil if available
        if HAS_PSUTIL:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                try:
                    load_avg = list(psutil.getloadavg())
                except AttributeError:
                    load_avg = [0.0, 0.0, 0.0]

                cpu_status = "warning" if cpu_percent >= cls.CPU_WARNING_THRESHOLD_PERCENT else "ok"
                metrics["cpu"] = {
                    "status": cpu_status,
                    "usage_percent": round(cpu_percent, 2),
                    "cores_logical": psutil.cpu_count(logical=True) or 1,
                    "cores_physical": psutil.cpu_count(logical=False) or 1,
                    "load_average": [round(x, 2) for x in load_avg],
                }

                mem = psutil.virtual_memory()
                ram_percent = round(mem.percent, 2)
                ram_status = "warning" if ram_percent >= cls.RAM_WARNING_THRESHOLD_PERCENT else "ok"
                metrics["ram"] = {
                    "status": ram_status,
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "free_gb": round(mem.available / (1024**3), 2),
                    "usage_percent": ram_percent,
                }

                swap = psutil.swap_memory()
                metrics["swap"] = {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "usage_percent": round(swap.percent, 2),
                }
            except Exception as e:
                logger.warning(f"Error collecting psutil metrics: {e}")

        return metrics

    @classmethod
    def get_database_metrics(cls) -> Dict[str, Any]:
        """Collect PostgreSQL connection counts, database size, and buffer cache efficiency."""
        try:
            with connection.cursor() as cursor:
                # Active vs Max connections
                cursor.execute("SELECT count(*) FROM pg_stat_activity;")
                active_conns = cursor.fetchone()[0]

                cursor.execute("SHOW max_connections;")
                max_conns = int(cursor.fetchone()[0])

                conn_percent = round((active_conns / max_conns) * 100, 2) if max_conns > 0 else 0.0
                status = "warning" if conn_percent >= cls.DB_CONN_WARNING_PERCENT else "ok"

                # Database size
                cursor.execute("SELECT pg_database_size(current_database()), pg_size_pretty(pg_database_size(current_database()));")
                db_size_bytes, db_size_human = cursor.fetchone()

                # Buffer cache hit ratio
                cursor.execute("""
                    SELECT round(sum(heap_blks_hit) / nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2)
                    FROM pg_statio_user_tables;
                """)
                hit_ratio_row = cursor.fetchone()
                cache_hit_ratio = float(hit_ratio_row[0]) if hit_ratio_row and hit_ratio_row[0] is not None else 100.0

            return {
                "status": status,
                "engine": connection.settings_dict.get("ENGINE", "").split(".")[-1],
                "database_name": connection.settings_dict.get("NAME", ""),
                "active_connections": active_conns,
                "max_connections": max_conns,
                "connection_utilization_percent": conn_percent,
                "database_size_bytes": db_size_bytes,
                "database_size_human": db_size_human,
                "cache_hit_ratio_percent": cache_hit_ratio,
            }
        except Exception as e:
            logger.error(f"Database diagnostics failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    def get_redis_metrics(cls) -> Dict[str, Any]:
        """Collect Redis memory utilization, uptime, connected clients, and hit/miss ratio."""
        try:
            import redis

            start_time = time.monotonic()
            client = redis.from_url(settings.REDIS_URL, socket_timeout=3.0)
            client.ping()
            ping_ms = round((time.monotonic() - start_time) * 1000, 2)

            info_mem = client.info("memory")
            info_clients = client.info("clients")
            info_stats = client.info("stats")
            info_server = client.info("server")

            hits = info_stats.get("keyspace_hits", 0)
            misses = info_stats.get("keyspace_misses", 0)
            hit_ratio = round((hits / (hits + misses)) * 100, 2) if (hits + misses) > 0 else 100.0

            return {
                "status": "ok",
                "ping_latency_ms": ping_ms,
                "version": info_server.get("redis_version", "unknown"),
                "uptime_days": info_server.get("uptime_in_days", 0),
                "connected_clients": info_clients.get("connected_clients", 0),
                "used_memory_human": info_mem.get("used_memory_human", "0B"),
                "peak_memory_human": info_mem.get("used_memory_peak_human", "0B"),
                "hit_ratio_percent": hit_ratio,
            }
        except Exception as e:
            logger.error(f"Redis diagnostics failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    def get_celery_metrics(cls) -> Dict[str, Any]:
        """Collect active Celery worker nodes, task execution status, and failed job counts."""
        metrics = {"status": "ok", "active_workers": 0, "worker_details": {}, "failed_jobs_24h": 0}
        try:
            from config.celery import app

            inspect = app.control.inspect(timeout=3.0)
            active_tasks = inspect.active()

            if active_tasks is None:
                metrics["status"] = "error"
                metrics["error"] = "No Celery workers responded to inspection probe."
            else:
                metrics["active_workers"] = len(active_tasks)
                for worker_name, tasks in active_tasks.items():
                    metrics["worker_details"][worker_name] = {"active_task_count": len(tasks)}

            # Check failed tasks count over the past 24 hours via django-celery-results if present
            try:
                from django_celery_results.models import TaskResult

                cutoff = timezone.now() - timedelta(hours=24)
                failed_count = TaskResult.objects.filter(status="FAILURE", date_done__gte=cutoff).count()
                metrics["failed_jobs_24h"] = failed_count

                if failed_count >= cls.FAILED_JOBS_ALERT_THRESHOLD:
                    metrics["status"] = "warning"
            except (ImportError, LookupError, Exception):
                pass

            return metrics
        except Exception as e:
            logger.error(f"Celery diagnostics failed: {e}")
            return {"status": "error", "error": str(e)}

    @classmethod
    def get_application_metrics(cls) -> Dict[str, Any]:
        """Calculate application uptime duration, versions, and runtime parameters."""
        uptime_seconds = int(time.time() - PROCESS_START_TIME)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_human = f"{days}d {hours}h {minutes}m {seconds}s"

        return {
            "status": "ok",
            "uptime_seconds": uptime_seconds,
            "uptime_human": uptime_human,
            "python_version": sys.version.split(" ")[0],
            "django_version": django.get_version(),
            "debug_mode": settings.DEBUG,
            "time_zone": getattr(settings, "TIME_ZONE", "UTC"),
        }

    @classmethod
    def evaluate_thresholds_and_alert(cls) -> Dict[str, Any]:
        """Evaluate diagnostics against warning/critical thresholds and dispatch email alerts if breached."""
        diagnostics = cls.collect_all_diagnostics()
        breaches: List[Tuple[str, str, str]] = []  # (Level, Component, Message)

        # Check Component Availability
        if diagnostics["database"].get("status") == "error":
            breaches.append(("CRITICAL", "Database", f"PostgreSQL unreachable: {diagnostics['database'].get('error')}"))
        if diagnostics["redis"].get("status") == "error":
            breaches.append(("CRITICAL", "Redis", f"Redis broker unreachable: {diagnostics['redis'].get('error')}"))
        if diagnostics["celery"].get("status") == "error":
            breaches.append(("CRITICAL", "Celery", f"Celery workers down: {diagnostics['celery'].get('error')}"))

        # Check Disk Usage
        for label, disk_info in diagnostics["system"].get("disk", {}).items():
            status = disk_info.get("status", "ok")
            if status in ("warning", "critical"):
                percent = disk_info.get("usage_percent", 0.0)
                path = disk_info.get("path", "")
                level = "CRITICAL" if status == "critical" else "WARNING"
                breaches.append((level, f"Disk ({label})", f"Mount point {path} utilization at {percent}%"))

        # Check CPU & RAM
        if diagnostics["system"].get("cpu", {}).get("status") == "warning":
            percent = diagnostics["system"]["cpu"].get("usage_percent", 0.0)
            breaches.append(("WARNING", "CPU", f"System CPU utilization high at {percent}%"))
        if diagnostics["system"].get("ram", {}).get("status") == "warning":
            percent = diagnostics["system"]["ram"].get("usage_percent", 0.0)
            breaches.append(("WARNING", "RAM", f"System RAM utilization high at {percent}%"))

        # Check Database Connections
        if diagnostics["database"].get("status") == "warning":
            percent = diagnostics["database"].get("connection_utilization_percent", 0.0)
            breaches.append(("WARNING", "Database", f"PostgreSQL connection pool utilization high at {percent}%"))

        # Check Failed Celery Jobs
        failed_jobs = diagnostics["celery"].get("failed_jobs_24h", 0)
        if failed_jobs >= cls.FAILED_JOBS_ALERT_THRESHOLD:
            breaches.append(("WARNING", "Celery Jobs", f"Failed background task count reached {failed_jobs} over the past 24 hours."))

        alert_sent = False
        recipients = []

        if breaches:
            alert_sent, recipients = cls.dispatch_email_alert(diagnostics, breaches)

        return {
            "timestamp": diagnostics["timestamp"],
            "overall_status": diagnostics["status"],
            "breaches_detected": len(breaches),
            "breach_details": [{"level": b[0], "component": b[1], "message": b[2]} for b in breaches],
            "email_alert_sent": alert_sent,
            "recipients": recipients,
            "diagnostics": diagnostics,
        }

    @classmethod
    def dispatch_email_alert(cls, diagnostics: Dict[str, Any], breaches: List[Tuple[str, str, str]]) -> Tuple[bool, List[str]]:
        """Format and dispatch HTML/Plain-text email notifications to administrators."""
        recipients = [email for name, email in getattr(settings, "ADMINS", [])]
        if not recipients:
            fallback_email = os.environ.get("PGADMIN_DEFAULT_EMAIL") or getattr(settings, "DEFAULT_FROM_EMAIL", "")
            if fallback_email:
                recipients = [fallback_email]

        if not recipients:
            logger.warning("Monitoring alert triggered, but no email recipients found in settings.ADMINS or environment.")
            return False, []

        highest_level = "CRITICAL" if any(b[0] == "CRITICAL" for b in breaches) else "WARNING"
        subject = f"[{highest_level}] EduNaukri System Health Alert - {len(breaches)} Issue(s) Detected"

        # Plain Text Body
        body_lines = [
            "EduNaukri Automated Monitoring Alert",
            f"Timestamp: {diagnostics['timestamp']}",
            f"Overall Status: {diagnostics['status'].upper()}",
            "------------------------------------------------------------------------",
            "DETECTED ISSUES:",
        ]
        for level, component, message in breaches:
            body_lines.append(f"  [{level}] {component}: {message}")

        body_lines.extend([
            "------------------------------------------------------------------------",
            "SYSTEM SUMMARY:",
            f"  Uptime: {diagnostics['application'].get('uptime_human')}",
            f"  Active Celery Workers: {diagnostics['celery'].get('active_workers')}",
            f"  Database Active Connections: {diagnostics['database'].get('active_connections')} / {diagnostics['database'].get('max_connections')}",
            f"  Redis Used Memory: {diagnostics['redis'].get('used_memory_human')}",
            "========================================================================",
        ])
        plain_message = "\n".join(body_lines)

        # HTML Body
        html_breaches = "".join(
            f'<tr style="background-color: {"#ffebee" if level == "CRITICAL" else "#fff3e0"};">'
            f'<td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: {"#c62828" if level == "CRITICAL" else "#ef6c00"};">{level}</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd;">{component}</td>'
            f'<td style="padding: 8px; border: 1px solid #ddd;">{message}</td></tr>'
            for level, component, message in breaches
        )

        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 650px; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
            <h2 style="color: {'#c62828' if highest_level == 'CRITICAL' else '#ef6c00'}; margin-top: 0;">
                ⚠️ EduNaukri System Health Alert ({highest_level})
            </h2>
            <p>The automated monitoring engine detected <strong>{len(breaches)}</strong> diagnostic issue(s) at <code>{diagnostics['timestamp']}</code>.</p>
            
            <h3>Detected Breaches</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #f5f5f5;">
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Severity</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Component</th>
                        <th style="padding: 8px; border: 1px solid #ddd; text-align: left;">Detail</th>
                    </tr>
                </thead>
                <tbody>
                    {html_breaches}
                </tbody>
            </table>

            <h3>Quick System Snapshot</h3>
            <ul style="line-height: 1.6;">
                <li><strong>Application Uptime:</strong> {diagnostics['application'].get('uptime_human')}</li>
                <li><strong>Database Connections:</strong> {diagnostics['database'].get('active_connections')} / {diagnostics['database'].get('max_connections')} ({diagnostics['database'].get('connection_utilization_percent')}%)</li>
                <li><strong>Redis Memory & Clients:</strong> {diagnostics['redis'].get('used_memory_human')} ({diagnostics['redis'].get('connected_clients')} clients)</li>
                <li><strong>Celery Active Workers:</strong> {diagnostics['celery'].get('active_workers')}</li>
            </ul>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #777;">This notification was generated automatically by the EduNaukri Diagnostic Monitoring Service.</p>
        </div>
        """

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@edunaukari.com"),
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Dispatched system health alert email to {len(recipients)} recipients.")
            return True, recipients
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False, recipients
