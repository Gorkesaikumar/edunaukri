"""Management command to run system diagnostic checks and dispatch email alerts."""

import json
from django.core.management.base import BaseCommand
from apps.health.services.monitoring_service import SystemHealthMonitoringService


class Command(BaseCommand):
    help = "Run comprehensive system diagnostic checks and dispatch email alerts if warning or critical thresholds are breached."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send-alerts",
            action="store_true",
            default=True,
            help="Evaluate thresholds and dispatch email alerts on warning/critical breaches (default: True).",
        )
        parser.add_argument(
            "--no-alerts",
            action="store_true",
            help="Only display metrics without dispatching email alerts.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output diagnostic report formatted as raw JSON.",
        )

    def handle(self, *args, **options):
        send_alerts = not options["no_alerts"]

        if send_alerts:
            report = SystemHealthMonitoringService.evaluate_thresholds_and_alert()
            diagnostics = report["diagnostics"]
        else:
            diagnostics = SystemHealthMonitoringService.collect_all_diagnostics()
            report = {
                "overall_status": diagnostics["status"],
                "breaches_detected": 0,
                "email_alert_sent": False,
                "diagnostics": diagnostics,
            }

        if options["json"]:
            self.stdout.write(json.dumps(report if send_alerts else diagnostics, indent=2))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("========================================================================"))
        self.stdout.write(self.style.MIGRATE_HEADING(f"EduNaukri Diagnostic Monitoring Report [{diagnostics['timestamp']}]"))
        self.stdout.write(self.style.MIGRATE_HEADING("========================================================================"))

        status_color = self.style.SUCCESS if diagnostics["status"] == "healthy" else (self.style.WARNING if diagnostics["status"] == "degraded" else self.style.ERROR)
        self.stdout.write(f"Overall System Status: {status_color(diagnostics['status'].upper())}")
        self.stdout.write(f"Application Uptime:    {diagnostics['application'].get('uptime_human')}")

        # System Snapshot
        self.stdout.write("\n[System Resources]")
        for label, disk in diagnostics["system"].get("disk", {}).items():
            s = disk.get("status", "ok")
            sc = self.style.SUCCESS if s == "ok" else self.style.ERROR
            self.stdout.write(f"  Disk ({label:7}): {disk.get('used_gb')} GB / {disk.get('total_gb')} GB ({disk.get('usage_percent')}%) [{sc(s.upper())}]")

        cpu = diagnostics["system"].get("cpu", {})
        ram = diagnostics["system"].get("ram", {})
        self.stdout.write(f"  CPU Load:        {cpu.get('usage_percent')}% (Logical Cores: {cpu.get('cores_logical')}, Load Avg: {cpu.get('load_average')})")
        self.stdout.write(f"  RAM Usage:       {ram.get('used_gb')} GB / {ram.get('total_gb')} GB ({ram.get('usage_percent')}%)")

        # Database Snapshot
        db = diagnostics["database"]
        db_s = db.get("status", "ok")
        db_sc = self.style.SUCCESS if db_s == "ok" else self.style.ERROR
        self.stdout.write(f"\n[PostgreSQL Database ({db.get('database_name')})] [{db_sc(db_s.upper())}]")
        self.stdout.write(f"  Connections:     {db.get('active_connections')} / {db.get('max_connections')} ({db.get('connection_utilization_percent')}%)")
        self.stdout.write(f"  Database Size:   {db.get('database_size_human')}")
        self.stdout.write(f"  Cache Hit Ratio: {db.get('cache_hit_ratio_percent')}%")

        # Redis Snapshot
        redis = diagnostics["redis"]
        r_s = redis.get("status", "ok")
        r_sc = self.style.SUCCESS if r_s == "ok" else self.style.ERROR
        self.stdout.write(f"\n[Redis Broker & Cache] [{r_sc(r_s.upper())}]")
        self.stdout.write(f"  Ping Latency:    {redis.get('ping_latency_ms')} ms (Version: {redis.get('version')})")
        self.stdout.write(f"  Memory Used:     {redis.get('used_memory_human')} (Peak: {redis.get('peak_memory_human')})")
        self.stdout.write(f"  Clients Connected: {redis.get('connected_clients')} (Hit Ratio: {redis.get('hit_ratio_percent')}%)")

        # Celery Snapshot
        celery = diagnostics["celery"]
        c_s = celery.get("status", "ok")
        c_sc = self.style.SUCCESS if c_s == "ok" else self.style.ERROR
        self.stdout.write(f"\n[Celery Workers & Tasks] [{c_sc(c_s.upper())}]")
        self.stdout.write(f"  Active Workers:  {celery.get('active_workers')}")
        self.stdout.write(f"  Failed Jobs 24h: {celery.get('failed_jobs_24h')}")

        if send_alerts and report["breaches_detected"] > 0:
            self.stdout.write(self.style.ERROR(f"\n[ALERT] {report['breaches_detected']} threshold breach(es) detected! Email dispatched to: {', '.join(report['recipients'])}"))
        elif send_alerts:
            self.stdout.write(self.style.SUCCESS("\n[OK] All diagnostic thresholds are within normal operational parameters."))
