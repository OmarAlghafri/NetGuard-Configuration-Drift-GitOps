"""Append-only audit trail.

Every drift check appends one row to ``audit_log.md`` whether or not drift was
found, so the log is a continuous record of when the network was verified, not
only when it failed.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .classifier import Severity
from .differ import DriftResult

AUDIT_FILE = Path(__file__).resolve().parent.parent / "audit_log.md"
_HEADER = (
    "# NetGuard - Audit Log\n\n"
    "Append-only record of every drift check (one row per run).\n\n"
    "| Timestamp | Device | Result | Severity | Action | Notes |\n"
    "|-----------|--------|--------|----------|--------|-------|\n"
)


def _ensure_header(path: Path) -> None:
    if not path.exists() or "| Timestamp |" not in path.read_text(encoding="utf-8"):
        path.write_text(_HEADER, encoding="utf-8")


def record(
    device: str,
    result: DriftResult,
    severity: Severity,
    action: str,
    notes: str = "",
    path: Path = AUDIT_FILE,
    timestamp: str | None = None,
) -> str:
    path = Path(path)
    _ensure_header(path)
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    outcome = "DRIFT" if result.has_drift else "clean"
    sev = severity.label if result.has_drift else "-"
    notes = notes or f"{len(result.changes)} changed line(s)"
    row = f"| {ts} | {device} | {outcome} | {sev} | {action} | {notes} |"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(row + "\n")
    return row
