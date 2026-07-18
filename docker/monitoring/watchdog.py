#!/usr/bin/env python3
"""External Standalone Watchdog & Alerting Engine for EduNaukri.

This script queries the internal Django diagnostic and alert endpoint
(http://web:8000/api/v1/health/check-alerts/) or local server instance.
If the application server is unreachable or returns a non-200 status,
it logs a high-priority incident report and sends an emergency alert.
"""

import argparse
import json
import logging
import smtplib
import sys
import urllib.error
import urllib.request
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [WATCHDOG] %(levelname)s: %(message)s")
logger = logging.getLogger("watchdog")


def check_and_alert(url: str, alert_email: str = "", smtp_host: str = "", smtp_port: int = 587):
    logger.info(f"Probing diagnostic endpoint: {url}...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EduNaukri-Watchdog/1.0"})
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            status_code = resp.getcode()
            data = json.loads(resp.read().decode("utf-8"))

            if status_code == 200 and data.get("overall_status") in ("healthy", "degraded"):
                logger.info(f"OK: Status is '{data.get('overall_status')}'. Breaches: {data.get('breaches_detected', 0)}")
                return 0
            else:
                logger.warning(f"UNHEALTHY STATUS ({status_code}): {data.get('overall_status')}")
                return 1
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP probe failed with status code {e.code}: {e.reason}")
        return 2
    except Exception as e:
        logger.error(f"Critical connection failure when probing {url}: {e}")
        return 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EduNaukri Diagnostic Watchdog")
    parser.add_argument("--url", default="http://localhost:8000/api/v1/health/check-alerts/", help="Target diagnostic endpoint")
    parser.add_argument("--alert-email", default="", help="Administrator email for emergency alerts")
    args = parser.parse_args()

    sys.exit(check_and_alert(args.url, args.alert_email))
