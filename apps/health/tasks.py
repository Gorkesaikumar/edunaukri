"""Background tasks for system health monitoring."""

import logging
from celery import shared_task
from apps.health.services.monitoring_service import SystemHealthMonitoringService

logger = logging.getLogger(__name__)


@shared_task(name="apps.health.tasks.run_health_check_alert")
def run_health_check_alert():
    """Periodic Celery task to evaluate system diagnostic metrics and dispatch email alerts if thresholds are breached."""
    logger.info("Executing periodic background system health evaluation...")
    report = SystemHealthMonitoringService.evaluate_thresholds_and_alert()
    breaches = report["breaches_detected"]
    if breaches > 0:
        logger.warning(f"Periodic check detected {breaches} threshold breach(es). Email dispatched: {report['email_alert_sent']}")
    else:
        logger.info("Periodic health check passed cleanly. No breaches detected.")
    return report
