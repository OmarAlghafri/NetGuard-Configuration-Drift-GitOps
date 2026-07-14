"""
lab_console.py
==============
GNS3 lab bridge for NetGuard.

On Windows, bridging host-originated IP traffic into GNS3 through Npcap is
unreliable, so in the lab the devices are reached over their console instead of
over SSH. (In production the same NetGuard engine reads and writes devices over
SSH; see docs/architecture.md.) This helper reads each node's console port from
the GNS3 API and speaks to the device over that console to:

    capture   snapshot every device's running-config into a directory, which
              drift_engine.py then inspects with --source dir
    inject    apply a named drift scenario to a device (for demonstrations)
    revert    compute the corrective commands from the golden baseline using the
              NetGuard engine and apply them

Usage
    python lab_console.py capture --out snapshots/current
    python lab_console.py inject R1 --scenario rogue-user
    python lab_console.py revert R1
"""

from __future__ import annotations

import argparse
import base64
import configparser
import json
import os
import socket
import sys
import time
import urllib.request
from pathlib import Path

from netguard import gitops
from netguard.differ import diff_configs
from netguard.remediation import build_revert_commands

HERE = Path(__file__).resolve().parent
ENABLE_SECRET = "NetGuardLab123"

SCENARIOS = {
    "rogue-user": ["username backdoor privilege 15 secret 0 Pwned123"],
    "ospf-hijack": ["router ospf 1", "network 0.0.0.0 255.255.255.255 area 0"],
    "acl-open": ["line vty 0 4", "no access-class 10 in"],
    "vlan-rogue": ["vlan 666", "name ROGUE"],
    "vlan-hop": ["interface FastEthernet1/0", "switchport access vlan 20"],
}


def _gns3():
    cfg = configparser.ConfigParser()
    cfg.read(Path(os.environ["APPDATA"]) / "GNS3" / "2.2" / "gns3_server.ini")
    s = cfg["Server"]
    base = f"http://{s['host']}:{s['port']}/v2"
    auth = base64.b64encode(f"{s['user']}:{s['password']}".encode()).decode()
    return base, auth


def _api(path: str):
    base, auth = _gns3()
    req = urllib.request.Request(base + path)
    req.add_header("Authorization", "Basic " + auth)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def console_ports() -> dict[str, int]:
    pid = next(p["project_id"] for p in _api("/projects") if p["name"].startswith("NetGuard"))
    return {n["name"]: n["console"] for n in _api(f"/projects/{pid}/nodes") if n["node_type"] == "dynamips"}


class Console:
    def __init__(self, port: int) -> None:
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)
        self.sock.settimeout(2.0)

    def _read(self) -> str:
        buf = b""
        try:
            while True:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
        except socket.timeout:
            pass
        return buf.decode(errors="ignore")

    def run(self, command: str, wait: float = 2.0) -> str:
        self.sock.sendall(command.encode() + b"\r")
        time.sleep(wait)
        return self._read()

    def enable(self) -> None:
        self.run("")
        out = self.run("enable")
        if "Password" in out:
            self.run(ENABLE_SECRET)
        self.run("terminal length 0")

    def running_config(self) -> str:
        raw = self.run("show running-config", wait=4)
        lines = raw.splitlines()
        start = next((i for i, l in enumerate(lines) if l.strip().startswith("version ")), 0)
        end = next((i for i, l in enumerate(lines) if l.strip() == "end"), len(lines) - 1)
        return "\n".join(l.rstrip() for l in lines[start:end + 1]) + "\n"

    def configure(self, commands: list[str]) -> None:
        self.run("configure terminal")
        for command in commands:
            self.run(command.strip())
        self.run("end")
        self.run("write memory", wait=6)

    def close(self) -> None:
        self.sock.close()


def cmd_capture(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, port in console_ports().items():
        console = Console(port)
        console.enable()
        (out / f"{name}.cfg").write_text(console.running_config(), encoding="utf-8")
        console.close()
        print(f"  {name:<6} snapshot -> {(out / f'{name}.cfg')}")
    return 0


def cmd_inject(args: argparse.Namespace) -> int:
    commands = SCENARIOS[args.scenario] if args.scenario else args.command
    port = console_ports()[args.device]
    console = Console(port)
    console.enable()
    console.configure(commands)
    console.close()
    print(f"  {args.device}: applied drift ({args.scenario or 'custom'})")
    return 0


def cmd_revert(args: argparse.Namespace) -> int:
    if not gitops.has_baseline(args.device):
        print(f"  {args.device}: no baseline to revert to")
        return 1
    port = console_ports()[args.device]
    console = Console(port)
    console.enable()
    running = console.running_config()
    result = diff_configs(args.device, gitops.read_baseline(args.device), running)
    commands = build_revert_commands(result)
    if not commands:
        print(f"  {args.device}: already matches baseline")
        console.close()
        return 0
    console.configure(commands)
    console.close()
    print(f"  {args.device}: reverted {len(result.changes)} drifted line(s) to baseline")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lab_console", description="GNS3 console bridge for the NetGuard lab.")
    sub = parser.add_subparsers(dest="command", required=True)

    capture = sub.add_parser("capture", help="snapshot running-configs to a directory")
    capture.add_argument("--out", default="snapshots/current")
    capture.set_defaults(func=cmd_capture)

    inject = sub.add_parser("inject", help="apply a drift scenario to a device")
    inject.add_argument("device")
    inject.add_argument("--scenario", choices=sorted(SCENARIOS))
    inject.add_argument("--command", action="append", help="raw config line (repeatable)")
    inject.set_defaults(func=cmd_inject)

    revert = sub.add_parser("revert", help="restore a device to its golden baseline")
    revert.add_argument("device")
    revert.set_defaults(func=cmd_revert)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
