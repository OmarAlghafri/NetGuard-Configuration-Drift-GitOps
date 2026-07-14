# Lab runbook

End-to-end steps to bring up the lab, establish a baseline, and exercise drift
detection and remediation. Commands are run from the repository root with the
virtual environment's Python.

## Prerequisites

- GNS3 2.2 with the local server running and the project
  `NetGuard - Configuration Drift Detection & GitOps Compliance Engine` open.
- The c3725 template and its IOS image registered in GNS3.
- Python virtual environment created and dependencies installed:

  ```
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  ```

## 1. Provision the topology

```
.venv\Scripts\python provision_lab.py --start
```

This builds R1, R2, SW1, the management switch and the host cloud, pushes each
device's intended startup-config, and powers the nodes on.

## 2. One-time SSH key bootstrap

The devices need an RSA key pair before SSH is available; this is generated at
the console once per build. Open each device console in GNS3 and run:

```
enable
configure terminal
crypto key generate rsa modulus 1024
end
write memory
```

## 3. Establish the golden baseline

Snapshot the live configuration and commit it as the approved baseline:

```
.venv\Scripts\python lab_console.py capture --out snapshots/current
.venv\Scripts\python drift_engine.py capture-baseline --source dir --source-dir snapshots/current
```

Each device's baseline is written to `baselines/<device>.cfg` and committed, so
git now records the approved state.

## 4. Verify (no drift expected)

```
.venv\Scripts\python lab_console.py capture --out snapshots/current
.venv\Scripts\python drift_engine.py check --source dir --source-dir snapshots/current
```

All devices report `clean`.

## 5. Introduce drift and detect it

```
.venv\Scripts\python lab_console.py inject R1 --scenario rogue-user
.venv\Scripts\python lab_console.py inject R2 --scenario ospf-hijack
.venv\Scripts\python lab_console.py inject SW1 --scenario vlan-hop

.venv\Scripts\python lab_console.py capture --out snapshots/current
.venv\Scripts\python drift_engine.py check --source dir --source-dir snapshots/current --report
```

R1 and R2 report CRITICAL drift and SW1 reports WARNING drift, an alert is
printed for each, a report is written under `reports/`, and each check is
appended to `audit_log.md`.

## 6. Preview the remediation (safe)

```
.venv\Scripts\python drift_engine.py check --source dir --source-dir snapshots/current --auto-revert --dry-run --alert-threshold critical
```

The exact corrective commands are printed without touching any device. Only
CRITICAL drift is targeted.

## 7. Remediate and confirm

```
.venv\Scripts\python lab_console.py revert R1
.venv\Scripts\python lab_console.py revert R2
.venv\Scripts\python lab_console.py revert SW1

.venv\Scripts\python lab_console.py capture --out snapshots/current
.venv\Scripts\python drift_engine.py check --source dir --source-dir snapshots/current
```

Every device returns to `clean`, closing the loop.

## Production note

Outside the lab, `drift_engine.py` reaches devices directly over SSH
(`--source ssh`, the default) using the credentials in `devices.yaml`; the
console bridge in `lab_console.py` exists only because host-to-node IP bridging
is unreliable under GNS3 on Windows. See `docs/architecture.md`.
