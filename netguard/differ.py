"""Diff a live running-config against a stored golden baseline.

The comparison runs over the normalised form of each config, so only meaningful
differences survive. Every surviving line is recorded as a :class:`Change`:

    ``+``  present on the device but not in the baseline (an addition)
    ``-``  present in the baseline but not on the device (a removal)

Each change also carries the parent block it belongs to (for example the
``interface FastEthernet0/0`` that owns an ``ip address`` line). That context is
resolved with ciscoconfparse and is what allows remediation to re-enter the
correct configuration sub-mode instead of blindly replaying flat lines.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from ciscoconfparse import CiscoConfParse

from .normalize import normalize

# ciscoconfparse emits informational loguru messages on every parse; they are
# noise for a CLI tool, so silence that library's logger on import.
try:
    from loguru import logger as _loguru_logger

    _loguru_logger.disable("ciscoconfparse")
except Exception:  # pragma: no cover - loguru is a ciscoconfparse dependency
    pass


@dataclass
class Change:
    op: str
    line: str
    parent: str = ""
    severity: str = "info"
    reason: str = ""

    def render(self) -> str:
        prefix = f"{self.parent} :: " if self.parent else ""
        return f"{self.op} {prefix}{self.line}"


@dataclass
class DriftResult:
    device: str
    changes: list[Change] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.changes)

    def by_severity(self, severity: str) -> list[Change]:
        return [c for c in self.changes if c.severity == severity]


def _parent_map(config: str) -> dict[str, str]:
    """Map each config line (as written) to its parent block, if any."""
    parse = CiscoConfParse(config.splitlines(), syntax="ios")
    mapping: dict[str, str] = {}
    for obj in parse.objs:
        parent = "" if obj.parent is obj else obj.parent.text.strip()
        mapping.setdefault(obj.text.rstrip(), parent)
    return mapping


def diff_configs(device: str, baseline: str, running: str) -> DriftResult:
    """Return the drift of ``running`` relative to ``baseline`` for ``device``."""
    base_lines = normalize(baseline)
    run_lines = normalize(running)
    parents_add = _parent_map(running)
    parents_remove = _parent_map(baseline)

    changes: list[Change] = []
    for line in difflib.unified_diff(base_lines, run_lines, lineterm=""):
        if line.startswith(("+++", "---")) or line[:1] not in {"+", "-"}:
            continue
        op, text = line[0], line[1:]
        parent = (parents_add if op == "+" else parents_remove).get(text.rstrip(), "")
        changes.append(Change(op=op, line=text.strip(), parent=parent))
    return DriftResult(device=device, changes=changes)
