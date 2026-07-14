"""Classify configuration changes by operational severity.

The rules live in ``policy.yaml`` rather than in code, so the severity model can
be reviewed and extended without touching the engine. Rules are evaluated in
order and the first match wins; anything unmatched is treated as informational.

Severity tiers:
    CRITICAL  routing, access-control and authentication changes
    WARNING   VLAN, interface and addressing changes
    INFO      descriptions, banners and other cosmetic changes
"""

from __future__ import annotations

import re
from enum import IntEnum
from pathlib import Path

import yaml

from .differ import Change, DriftResult

DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "policy.yaml"


class Severity(IntEnum):
    INFO = 1
    WARNING = 2
    CRITICAL = 3

    @property
    def label(self) -> str:
        return self.name.capitalize()


class Classifier:
    def __init__(self, policy_path: str | Path = DEFAULT_POLICY) -> None:
        data = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
        self._rules: list[tuple[Severity, str, list[re.Pattern]]] = []
        for rule in data.get("rules", []):
            severity = Severity[rule["severity"].upper()]
            patterns = [re.compile(p) for p in rule["patterns"]]
            self._rules.append((severity, rule.get("description", ""), patterns))

    def classify_line(self, line: str) -> tuple[Severity, str]:
        for severity, description, patterns in self._rules:
            if any(p.search(line) for p in patterns):
                return severity, description
        return Severity.INFO, "Cosmetic or unclassified change"

    def classify(self, result: DriftResult) -> Severity:
        """Annotate every change in ``result`` and return the highest severity."""
        highest = Severity.INFO
        for change in result.changes:
            severity, reason = self.classify_line(change.line)
            change.severity = severity.name.lower()
            change.reason = reason
            highest = max(highest, severity)
        return highest if result.changes else Severity.INFO
