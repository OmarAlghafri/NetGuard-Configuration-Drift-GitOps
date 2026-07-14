"""
NetGuard — Alerting module
==========================
Raises an alert whenever Critical or Warning drift is detected.

v1 channels:
    - console  (always on)
    - email    (optional, via smtplib; disabled by default)

Telegram is intentionally OUT OF SCOPE for this build.

STATUS: scaffolding only.
"""

# TODO(Phase 3): console_alert(device, severity, diff)
# TODO(Phase 3): email_alert(...) via smtplib — config-driven, off by default
