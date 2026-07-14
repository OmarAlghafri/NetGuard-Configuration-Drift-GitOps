# Architecture

NetGuard treats each device's approved configuration as version-controlled code
and continuously verifies the live network against it. The system is a short
pipeline; each stage is a small module under `netguard/` that can be tested on
its own.

## Pipeline

```
inventory ->  retrieve  ->  normalise  ->  diff  ->  classify  ->  act
 (YAML)       (SSH or       (strip        (vs      (policy.yaml   (alert /
              snapshot)     volatile)     golden)  severity)      revert /
                                                                   audit /
                                                                   report)
```

1. **Inventory** (`inventory.py`) - devices and shared credentials are read from
   `devices.yaml`. A `defaults` block is merged into each device entry.
2. **Retrieve** (`connector.py`) - the running-config is pulled with Netmiko over
   SSH. For offline analysis and CI the same config can be read from a directory
   of files (`--source dir`), which keeps the engine testable without a device.
3. **Normalise** (`normalize.py`) - lines that legitimately vary between reads
   (the header block, byte counts, `ntp clock-period`) are removed so they never
   register as drift. Security-relevant material is left untouched.
4. **Diff** (`differ.py`) - the normalised live config is compared to the golden
   baseline. Each changed line is captured with its parent block, resolved with
   ciscoconfparse, so an `ip address` change is reported against the interface it
   belongs to rather than as a floating line.
5. **Classify** (`classifier.py`) - every change is assigned a severity by the
   ordered rules in `policy.yaml`: CRITICAL for routing, access-control and
   authentication, WARNING for VLAN and interface changes, INFO for cosmetic
   changes. The policy is data, not code, so the severity model can be reviewed
   and extended without touching the engine.
6. **Act** - drift at or above a threshold raises an alert (`alerting.py`); every
   check is written to the audit trail (`audit.py`); a Markdown report can be
   generated (`reporting.py`); and CRITICAL drift can be reverted to baseline
   (`remediation.py`), which negates additions and re-applies removals, wrapping
   interface-scoped commands in their block.

## Git as the source of truth

The approved configuration of each device lives under `baselines/` and is
committed. Capturing a baseline commits it (`gitops.py`), so the history answers
"what was approved, and when" for every device. Drift is always measured against
the committed baseline, never an ad-hoc copy. This is the GitOps property the
project is built around: the repository, not the device, defines intended state.

## The lab management path

The engine reads and writes devices over SSH. In this GNS3 lab on Windows,
bridging host-originated IP traffic into the emulated nodes through Npcap is
unreliable (the node can reach the host, but not the reverse), which is a known
GNS3-on-Windows limitation. Rather than depend on it, the lab is driven over the
device console: `lab_console.py` reads each node's console port from the GNS3 API
and snapshots or configures the device that way, then `drift_engine.py` analyses
the snapshot with `--source dir`. The detection, classification, remediation and
GitOps logic are identical regardless of how the config was obtained; only the
transport differs between the lab and a production deployment.

## Why the modules are split this way

Each module has a single responsibility and no knowledge of the others beyond a
small data type (`Device`, `Change`, `DriftResult`). That makes the severity
policy swappable, lets the diff engine be unit-tested against fixtures with no
device present, and keeps the transport (SSH vs. console vs. file) independent of
the analysis. The CLI (`drift_engine.py`) is a thin orchestrator over these
parts.
