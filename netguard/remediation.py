"""Safe auto-remediation.

Remediation restores a device to its golden baseline. It is deliberately
conservative:

* it acts only on the drift the caller passes in (typically CRITICAL);
* ``dry_run`` is the default: it prints the exact commands without touching the
  device, mirroring the safety pattern used throughout this project;
* every real revert is returned to the caller so it can be logged and alerted
  on. Remediation is never silent.

A line added on the device is negated with ``no``; a line removed from the
device is re-applied. When a change belongs to a block (an interface, a routing
process) the corrective commands are wrapped in that block so they apply in the
right sub-mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .connector import DeviceConnection
from .differ import Change, DriftResult
from .inventory import Device


@dataclass
class RemediationPlan:
    device: str
    commands: list[str] = field(default_factory=list)
    applied: bool = False
    output: str = ""


def _corrective_line(change: Change) -> str:
    if change.op == "+":
        return change.line if change.line.startswith("no ") else f"no {change.line}"
    return change.line


def build_revert_commands(result: DriftResult) -> list[str]:
    """Translate detected drift into the IOS commands that undo it.

    Additions are negated before removals are re-applied. This matters for
    replace-semantics commands such as ``switchport access vlan``: negating the
    drifted value first returns the setting to its default, after which the
    baseline value is re-applied cleanly, instead of the negation wiping out the
    value just restored.
    """
    commands: list[str] = []
    current_block = None
    ordered = sorted(result.changes, key=lambda c: 0 if c.op == "+" else 1)
    for change in ordered:
        correction = _corrective_line(change)
        if change.parent:
            if change.parent != current_block:
                commands.append(change.parent)
                current_block = change.parent
            commands.append(f" {correction}")
        else:
            if current_block is not None:
                commands.append("exit")
                current_block = None
            commands.append(correction)
    return commands


def remediate(device: Device, result: DriftResult, dry_run: bool = True) -> RemediationPlan:
    commands = build_revert_commands(result)
    plan = RemediationPlan(device=device.name, commands=commands)
    if dry_run or not commands:
        return plan
    plan.output = DeviceConnection(device).apply_config(commands)
    plan.applied = True
    return plan
