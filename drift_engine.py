#!/usr/bin/env python
"""NetGuard command-line interface.

Subcommands
    check             compare each device against its golden baseline
    capture-baseline  read each device's running-config and commit it as golden
    diff              offline compare of two config files (no device needed)

Configuration is read from a live device over SSH by default. Passing
``--source dir --source-dir DIR`` reads ``DIR/<device>.cfg`` instead, which makes
the whole pipeline runnable and reproducible without the lab powered on.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from netguard import __version__, gitops
from netguard.alerting import Alerter
from netguard.audit import record
from netguard.classifier import Classifier, Severity
from netguard.connector import DeviceConnection
from netguard.differ import DriftResult, diff_configs
from netguard.inventory import Device, load_inventory
from netguard.remediation import remediate
from netguard.reporting import write_report

REPO = Path(__file__).resolve().parent
DEFAULT_INVENTORY = REPO / "devices.yaml"

RULE = "=" * 60


def _running_config(device: Device, source: str, source_dir: str) -> str:
    if source == "dir":
        return (Path(source_dir) / f"{device.name}.cfg").read_text(encoding="utf-8")
    return DeviceConnection(device).get_running_config()


def _print_result(name: str, result: DriftResult, severity: Severity) -> None:
    if not result.has_drift:
        print(f"  {name:<6} clean")
        return
    print(f"  {name:<6} {severity.label.upper():<9} {len(result.changes)} change(s)")
    for change in result.changes:
        context = f"{change.parent} :: " if change.parent else ""
        print(f"      {change.op} [{change.severity.upper():<8}] {context}{change.line}")


def _apply_plan(plan, dry_run: bool) -> str:
    if not plan.commands:
        return "detected"
    header = "  [dry-run] revert preview:" if dry_run else "  [revert] applied:"
    print(f"\n{header}")
    for command in plan.commands:
        print(f"      {command}")
    return "dry-run-revert" if dry_run else "reverted"


def cmd_check(args: argparse.Namespace) -> int:
    devices = load_inventory(args.inventory)
    classifier = Classifier()
    alerter = Alerter(threshold=Severity[args.alert_threshold.upper()])
    findings: list[tuple[str, DriftResult, Severity]] = []
    exit_code = 0

    print(RULE)
    print(" NetGuard drift check")
    print(RULE)
    for device in devices:
        if not gitops.has_baseline(device.name):
            print(f"  {device.name:<6} no baseline (run capture-baseline first)")
            continue
        try:
            running = _running_config(device, args.source, args.source_dir)
        except Exception as exc:  # noqa: BLE001 - surface any transport error per device
            print(f"  {device.name:<6} error: {exc}")
            exit_code = max(exit_code, 2)
            continue

        result = diff_configs(device.name, gitops.read_baseline(device.name), running)
        severity = classifier.classify(result)
        _print_result(device.name, result, severity)

        action = "detected" if result.has_drift else "verified"
        if result.has_drift and severity >= alerter.threshold:
            alerter.notify(result, severity)
        if result.has_drift and args.auto_revert and severity == Severity.CRITICAL:
            action = _apply_plan(remediate(device, result, dry_run=args.dry_run), args.dry_run)

        record(device.name, result, severity, action)
        findings.append((device.name, result, severity))
        if result.has_drift:
            exit_code = max(exit_code, 1)

    if args.report and findings:
        print(f"\nReport written: {write_report(findings).relative_to(REPO)}")
    print(RULE)
    return exit_code


def cmd_capture(args: argparse.Namespace) -> int:
    devices = load_inventory(args.inventory)
    for device in devices:
        try:
            running = _running_config(device, args.source, args.source_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"  {device.name:<6} error: {exc}")
            continue
        path = gitops.write_baseline(device.name, running)
        committed = gitops.commit_baseline(
            device.name, f"baseline: approve {device.name} configuration"
        )
        state = "committed" if committed else "no change"
        print(f"  {device.name:<6} baseline saved to {path.relative_to(REPO)} ({state})")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    baseline = Path(args.baseline).read_text(encoding="utf-8")
    running = Path(args.running).read_text(encoding="utf-8")
    name = args.name or Path(args.running).stem
    result = diff_configs(name, baseline, running)
    severity = Classifier().classify(result)
    _print_result(name, result, severity)
    return 1 if result.has_drift else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="drift_engine", description="NetGuard drift detection engine.")
    parser.add_argument("--version", action="version", version=f"NetGuard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_source(p: argparse.ArgumentParser) -> None:
        p.add_argument("--inventory", default=str(DEFAULT_INVENTORY), help="device inventory YAML")
        p.add_argument("--source", choices=["ssh", "dir"], default="ssh", help="config source")
        p.add_argument("--source-dir", default="", help="directory of <device>.cfg when --source dir")

    check = sub.add_parser("check", help="compare devices against their baselines")
    add_source(check)
    check.add_argument("--auto-revert", action="store_true", help="revert CRITICAL drift")
    check.add_argument("--dry-run", action="store_true", help="with --auto-revert, only preview commands")
    check.add_argument("--alert-threshold", default="warning", choices=["info", "warning", "critical"])
    check.add_argument("--report", action="store_true", help="write a markdown report under reports/")
    check.set_defaults(func=cmd_check)

    capture = sub.add_parser("capture-baseline", help="save and commit current configs as golden")
    add_source(capture)
    capture.set_defaults(func=cmd_capture)

    diff = sub.add_parser("diff", help="offline diff of two config files")
    diff.add_argument("--baseline", required=True)
    diff.add_argument("--running", required=True)
    diff.add_argument("--name", default="")
    diff.set_defaults(func=cmd_diff)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
