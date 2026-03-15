from __future__ import annotations
import json
import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.models import Alert, Violation

logger = logging.getLogger(__name__)


def _format_violation(v: Violation) -> str:
    return (
        f"[{v.severity.value.upper()}] {v.vendor_name} ({v.vendor_id})\n"
        f"  SLA Term  : {v.sla_term_name}\n"
        f"  Metric    : {v.metric}\n"
        f"  Actual    : {v.actual_value} (threshold: {v.operator} {v.threshold})\n"
        f"  Period    : {v.period}\n"
        f"  Method    : {v.detection_method}\n"
        f"  Detected  : {v.detected_at.isoformat()}\n"
        f"  Notes     : {v.notes}\n"
    )


class AlertManager:
    """
    Dispatches violation alerts to configured channels.
    Channels: console | slack | email
    """

    def __init__(self, channels: list[str] | None = None):
        from config import settings
        self.channels = channels or settings.ALERT_CHANNELS
        self.alert_log: list[Alert] = []

    def __call__(self, violations: list[Violation]) -> None:
        """Called by ComplianceMonitor when new violations are detected."""
        self.send(violations)

    def send(self, violations: list[Violation]) -> list[Alert]:
        alerts: list[Alert] = []
        for violation in violations:
            for channel in self.channels:
                alert = self._dispatch(violation, channel.strip())
                alerts.append(alert)
                self.alert_log.append(alert)
        return alerts

    def _dispatch(self, violation: Violation, channel: str) -> Alert:
        message = _format_violation(violation)
        success = True

        try:
            if channel == "console":
                self._send_console(violation, message)
            elif channel == "slack":
                self._send_slack(violation, message)
            elif channel == "email":
                self._send_email(violation, message)
            else:
                logger.warning("Unknown alert channel: %s", channel)
                success = False
        except Exception as exc:
            logger.error("Alert dispatch failed for channel=%s: %s", channel, exc)
            success = False

        return Alert(
            violation_id=violation.id,
            channel=channel,
            message=message,
            success=success,
        )

    def _send_console(self, violation: Violation, message: str) -> None:
        try:
            from rich.console import Console
            from rich.panel import Panel

            color = "red" if violation.severity.value == "critical" else "yellow"
            Console().print(Panel(message, title="CONTRACT VIOLATION", border_style=color))
        except ImportError:
            print(f"\n{'='*60}\nCONTRACT VIOLATION\n{message}{'='*60}\n")

    def _send_slack(self, violation: Violation, message: str) -> None:
        import urllib.request

        from config import settings

        if not settings.SLACK_WEBHOOK_URL:
            logger.warning("SLACK_WEBHOOK_URL not configured — skipping Slack alert")
            return

        color = "danger" if violation.severity.value == "critical" else "warning"
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"Contract Violation: {violation.vendor_name}",
                    "text": message,
                    "footer": "Contract Compliance Monitor",
                    "ts": int(datetime.utcnow().timestamp()),
                }
            ]
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            settings.SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
        logger.info("Slack alert sent for violation %s", violation.id)

    def _send_email(self, violation: Violation, message: str) -> None:
        from config import settings

        if not all([settings.SMTP_HOST, settings.ALERT_EMAIL_TO]):
            logger.warning("Email not configured (SMTP_HOST / ALERT_EMAIL_TO missing)")
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = (
            f"[{violation.severity.value.upper()}] Contract Violation: {violation.vendor_name}"
        )
        msg["From"] = settings.ALERT_EMAIL_FROM
        msg["To"] = settings.ALERT_EMAIL_TO

        html = f"<pre>{message}</pre>"
        msg.attach(MIMEText(message, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.ALERT_EMAIL_FROM, settings.ALERT_EMAIL_TO, msg.as_string())

        logger.info("Email alert sent for violation %s", violation.id)
