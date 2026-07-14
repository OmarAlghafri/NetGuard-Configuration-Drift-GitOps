"""Operator alerting.

Drift at or above a configurable threshold raises an alert. The console channel
is always active; email is optional and only engages when SMTP settings are
supplied, so the tool runs with no external dependencies out of the box.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .classifier import Severity
from .differ import DriftResult


def format_alert(result: DriftResult, severity: Severity) -> str:
    lines = [
        f"NetGuard drift alert: {result.device}",
        f"Highest severity: {severity.label}",
        f"Changed lines: {len(result.changes)}",
        "",
    ]
    for change in result.changes:
        lines.append(f"  [{change.severity.upper():<8}] {change.op} {change.line}")
    return "\n".join(lines)


class Alerter:
    def __init__(self, threshold: Severity = Severity.WARNING, smtp: dict | None = None) -> None:
        self.threshold = threshold
        self.smtp = smtp or {}

    def notify(self, result: DriftResult, severity: Severity) -> bool:
        """Send an alert if ``severity`` meets the threshold. Returns True if sent."""
        if severity < self.threshold:
            return False
        body = format_alert(result, severity)
        print(body)
        if self.smtp.get("enabled"):
            self._send_email(result.device, severity, body)
        return True

    def _send_email(self, device: str, severity: Severity, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = f"[NetGuard] {severity.label} drift on {device}"
        msg["From"] = self.smtp["sender"]
        msg["To"] = ", ".join(self.smtp["recipients"])
        msg.set_content(body)
        with smtplib.SMTP(self.smtp["host"], int(self.smtp.get("port", 25))) as server:
            if self.smtp.get("starttls"):
                server.starttls()
            if self.smtp.get("username"):
                server.login(self.smtp["username"], self.smtp["password"])
            server.send_message(msg)
