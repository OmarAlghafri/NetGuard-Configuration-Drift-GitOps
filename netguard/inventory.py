"""Device inventory loading.

Devices are described in a YAML file (see devices.yaml.example). A ``defaults``
block supplies shared credentials and connection settings; each device entry
overrides only what differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Device:
    name: str
    host: str
    role: str = "router"
    device_type: str = "cisco_ios"
    username: str = "admin"
    password: str = ""
    secret: str = ""
    port: int = 22


def load_inventory(path: str | Path) -> list[Device]:
    """Return the list of devices described by the YAML inventory at ``path``."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    defaults = data.get("defaults", {}) or {}
    devices: list[Device] = []
    for entry in data.get("devices", []) or []:
        merged = {**defaults, **entry}
        if "name" not in merged or "host" not in merged:
            raise ValueError(f"inventory entry missing name/host: {entry!r}")
        devices.append(
            Device(
                name=merged["name"],
                host=merged["host"],
                role=merged.get("role", "router"),
                device_type=merged.get("device_type", "cisco_ios"),
                username=merged.get("username", "admin"),
                password=merged.get("password", ""),
                secret=merged.get("secret", ""),
                port=int(merged.get("port", 22)),
            )
        )
    if not devices:
        raise ValueError(f"no devices defined in {path}")
    return devices
