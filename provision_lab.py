"""
provision_lab.py
================
Builds the NetGuard lab topology inside GNS3 from code, using the GNS3 v2 REST
API. Treating the lab itself as reproducible infrastructure means the whole
environment can be torn down and rebuilt identically in one command, which is
exactly the property NetGuard relies on when it compares live state to a known
baseline.

Topology
    R1 Fa0/0 ------ 10.0.12.0/30 (OSPF area 0) ------ Fa0/0 R2
    R1 Fa0/1 --.                                    .-- Fa0/1 R2
               |                                    |
              MGMT-SW (Ethernet switch) --- Cloud (host-only 192.168.56.0/24)
               |
    SW1 Fa0/0 -'      SW1 Fa1/0-3: VLAN 10/20 access ports

Management addressing (192.168.56.0/24, VirtualBox host-only):
    R1  192.168.56.20    R2  192.168.56.21    SW1 192.168.56.22

Usage
    python provision_lab.py            # build (idempotent: wipes and rebuilds)
    python provision_lab.py --start    # build, then power on all nodes

The GNS3 server host, port and credentials are read from the local GNS3 server
configuration file so no secrets are stored in this repository.
"""

from __future__ import annotations

import argparse
import base64
import configparser
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTENDED = HERE / "configs" / "intended"
PROJECT_NAME = "NetGuard — Configuration Drift Detection & GitOps Compliance Engine"

# Dynamips template identifiers registered in this GNS3 installation. Built-in
# node types (Ethernet switch, Cloud) are created directly on the local compute.
TPL_ROUTER = "954d4a9f-de03-4e3e-b61b-ec48946640c2"   # c3725
TPL_SWITCH = "c919bf3e-6fcf-4cbc-9e95-148fc90ed8da"   # c3725 + NM-16ESW
HOST_UPLINK = "Ethernet"  # host adapter bridged to 192.168.56.0/24 (host-only)


def gns3_server_ini() -> Path:
    appdata = os.environ.get("APPDATA", "")
    return Path(appdata) / "GNS3" / "2.2" / "gns3_server.ini"


class GNS3:
    """Thin GNS3 v2 REST client."""

    def __init__(self) -> None:
        cfg = configparser.ConfigParser()
        cfg.read(gns3_server_ini())
        srv = cfg["Server"]
        self.base = f"{srv.get('protocol', 'http')}://{srv.get('host', 'localhost')}:{srv.get('port', '3080')}/v2"
        token = f"{srv.get('user', '')}:{srv.get('password', '')}".encode()
        self.auth = base64.b64encode(token).decode()

    def _request(self, method: str, path: str, body=None, raw: bool = False):
        data = None
        if raw:
            data = body.encode() if isinstance(body, str) else body
        elif body is not None:
            data = json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_header("Authorization", "Basic " + self.auth)
        if data is not None:
            req.add_header("Content-Type", "application/octet-stream" if raw else "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = resp.read().decode()
                return resp.status, (payload if raw else (json.loads(payload) if payload else None))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{method} {path} -> HTTP {exc.code}: {exc.read().decode()[:300]}") from None

    def get(self, path):
        return self._request("GET", path)[1]

    def post(self, path, body=None):
        return self._request("POST", path, body)[1]

    def put(self, path, body):
        return self._request("PUT", path, body)[1]

    def delete(self, path):
        return self._request("DELETE", path)[1]

    def post_raw(self, path, text):
        return self._request("POST", path, text, raw=True)[0]


def find_project(gns3: GNS3) -> str:
    for proj in gns3.get("/projects"):
        if proj["name"] == PROJECT_NAME:
            if proj["status"] != "opened":
                gns3.post(f"/projects/{proj['project_id']}/open")
            return proj["project_id"]
    raise SystemExit(f"Project not found in GNS3: {PROJECT_NAME!r}. Create it in the GNS3 GUI first.")


def wipe(gns3: GNS3, pid: str) -> None:
    for link in gns3.get(f"/projects/{pid}/links"):
        gns3.delete(f"/projects/{pid}/links/{link['link_id']}")
    for node in gns3.get(f"/projects/{pid}/nodes"):
        gns3.delete(f"/projects/{pid}/nodes/{node['node_id']}")


def add_from_template(gns3: GNS3, pid: str, template_id: str, name: str, x: int, y: int) -> dict:
    node = gns3.post(f"/projects/{pid}/templates/{template_id}", {"x": x, "y": y})
    gns3.put(f"/projects/{pid}/nodes/{node['node_id']}", {"name": name})
    node["name"] = name
    return node


def add_builtin(gns3: GNS3, pid: str, node_type: str, name: str, x: int, y: int, properties=None) -> dict:
    body = {"name": name, "node_type": node_type, "compute_id": "local", "x": x, "y": y}
    if properties:
        body["properties"] = properties
    return gns3.post(f"/projects/{pid}/nodes", body)


def push_startup_config(gns3: GNS3, pid: str, node: dict, cfg_file: Path) -> None:
    dynamips_id = node["properties"]["dynamips_id"]
    text = cfg_file.read_text(encoding="utf-8")
    path = f"/projects/{pid}/nodes/{node['node_id']}/files/configs/i{dynamips_id}_startup-config.cfg"
    status = gns3.post_raw(path, text)
    if status not in (200, 201, 204):
        raise RuntimeError(f"failed to push config to {node['name']}: HTTP {status}")


def link(gns3: GNS3, pid: str, a: dict, ap: int, an: int, b: dict, bp: int, bn: int) -> None:
    gns3.post(
        f"/projects/{pid}/links",
        {
            "nodes": [
                {"node_id": a["node_id"], "adapter_number": an, "port_number": ap},
                {"node_id": b["node_id"], "adapter_number": bn, "port_number": bp},
            ]
        },
    )


def build(start: bool) -> None:
    gns3 = GNS3()
    pid = find_project(gns3)
    print(f"[*] project: {PROJECT_NAME}")
    print("[*] wiping existing nodes/links")
    wipe(gns3, pid)

    print("[*] creating nodes")
    r1 = add_from_template(gns3, pid, TPL_ROUTER, "R1", -350, 40)
    r2 = add_from_template(gns3, pid, TPL_ROUTER, "R2", 300, 40)
    sw1 = add_from_template(gns3, pid, TPL_SWITCH, "SW1", -30, 320)
    mgmt = add_builtin(gns3, pid, "ethernet_switch", "MGMT-SW", -30, 180)
    cloud = add_builtin(
        gns3, pid, "cloud", "Host", -30, -110,
        {"ports_mapping": [{"interface": HOST_UPLINK, "name": HOST_UPLINK, "port_number": 0, "type": "ethernet"}]},
    )

    print("[*] pushing intended startup-configs")
    push_startup_config(gns3, pid, r1, INTENDED / "R1.cfg")
    push_startup_config(gns3, pid, r2, INTENDED / "R2.cfg")
    push_startup_config(gns3, pid, sw1, INTENDED / "SW1.cfg")

    print("[*] wiring links")
    link(gns3, pid, r1, 0, 0, r2, 0, 0)      # R1 Fa0/0 <-> R2 Fa0/0  (OSPF)
    link(gns3, pid, r1, 1, 0, mgmt, 0, 0)    # R1 Fa0/1 <-> MGMT-SW p0
    link(gns3, pid, r2, 1, 0, mgmt, 1, 0)    # R2 Fa0/1 <-> MGMT-SW p1
    link(gns3, pid, sw1, 0, 0, mgmt, 2, 0)   # SW1 Fa0/0 <-> MGMT-SW p2
    link(gns3, pid, mgmt, 7, 0, cloud, 0, 0)  # MGMT-SW p7 <-> Host uplink

    if start:
        print("[*] powering on nodes")
        gns3.post(f"/projects/{pid}/nodes/start")
        time.sleep(2)

    print("[+] lab provisioned")
    print("    next: start the nodes, then run the one-time SSH bootstrap (see docs/runbook.md)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the NetGuard GNS3 lab topology from code.")
    parser.add_argument("--start", action="store_true", help="power on all nodes after building")
    args = parser.parse_args()
    try:
        build(args.start)
    except (RuntimeError, SystemExit) as exc:
        print(f"[!] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
