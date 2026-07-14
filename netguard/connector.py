"""SSH access to network devices via Netmiko.

Retrieval and remediation both flow through this single wrapper so the rest of
the codebase never touches Netmiko directly. Connections are short lived: each
call opens a session, does its work and closes cleanly.
"""

from __future__ import annotations

from netmiko import ConnectHandler

from .inventory import Device


class DeviceConnection:
    def __init__(self, device: Device) -> None:
        self.device = device

    def _params(self) -> dict:
        return {
            "device_type": self.device.device_type,
            "host": self.device.host,
            "username": self.device.username,
            "password": self.device.password,
            "secret": self.device.secret or self.device.password,
            "port": self.device.port,
            "fast_cli": False,
        }

    def get_running_config(self) -> str:
        """Return the device's current running-config."""
        with ConnectHandler(**self._params()) as conn:
            conn.enable()
            return conn.send_command("show running-config")

    def apply_config(self, commands: list[str]) -> str:
        """Apply configuration commands and persist them to startup-config."""
        with ConnectHandler(**self._params()) as conn:
            conn.enable()
            output = conn.send_config_set(commands)
            conn.save_config()
            return output
