"""Markdown drift reports.

A single check produces one report summarising every device, the highest
severity seen, and the exact changed lines. Reports are timestamped and written
under ``reports/`` so they can be attached to a change ticket or reviewed later.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .classifier import Severity
from .differ import DriftResult

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def build_report(findings: list[tuple[str, DriftResult, Severity]], generated: str) -> str:
    total = len(findings)
    drifted = [f for f in findings if f[1].has_drift]
    critical = [f for f in drifted if f[2] == Severity.CRITICAL]

    lines = [
        "# NetGuard drift report",
        "",
        f"Generated: {generated}",
        f"Devices checked: {total}",
        f"Devices with drift: {len(drifted)}",
        f"Devices with critical drift: {len(critical)}",
        "",
    ]
    if not drifted:
        lines.append("All devices match their golden baseline. No drift detected.")
        return "\n".join(lines) + "\n"

    for device, result, severity in drifted:
        lines.append(f"## {device} - {severity.label}")
        lines.append("")
        lines.append("```diff")
        for change in result.changes:
            tag = change.severity.upper()
            context = f"{change.parent} :: " if change.parent else ""
            lines.append(f"{change.op} [{tag}] {context}{change.line}")
        lines.append("```")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_report(
    findings: list[tuple[str, DriftResult, Severity]],
    out_dir: Path = REPORTS_DIR,
    generated: str | None = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = generated or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stamp = generated.replace(":", "").replace("-", "").replace(" ", "-")
    path = out_dir / f"drift-report-{stamp}.md"
    path.write_text(build_report(findings, generated), encoding="utf-8")
    return path
