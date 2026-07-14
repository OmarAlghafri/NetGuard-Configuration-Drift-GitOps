"""Normalise a running-config into a stable, comparable form.

A raw ``show running-config`` contains a few lines that change between reads
without representing a real configuration change: the header block, byte
counts, and the NTP clock-period that drifts as the software clock is
disciplined. Comparing those would produce false positives, so they are
stripped before diffing. Security-relevant material (secret hashes, ACLs,
usernames) is deliberately left untouched so that genuine changes to it are
still detected.
"""

from __future__ import annotations

import re

_VOLATILE = (
    re.compile(r"^Building configuration"),
    re.compile(r"^Current configuration"),
    re.compile(r"^! Last configuration change"),
    re.compile(r"^! NVRAM config last updated"),
    re.compile(r"^\s*ntp clock-period"),
)


def normalize(config: str) -> list[str]:
    """Return the configuration as a list of significant, trimmed lines."""
    lines: list[str] = []
    for raw in config.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if any(pattern.search(line) for pattern in _VOLATILE):
            continue
        lines.append(line)
    return lines
