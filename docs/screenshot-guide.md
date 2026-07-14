# Capture guide

The images referenced by the README are captured here. Run each command in a
clean terminal (or the GNS3 GUI) and capture the result. Recordings are saved as
GIFs under `screenshots/`; still images and the topology diagram under
`diagrams/`.

Suggested terminal: a maximised window, readable font size, dark background.

## diagrams/topology.png
The GNS3 canvas with R1, R2, SW1, the management switch and the host cloud, links
visible. Take this after `provision_lab.py` runs and the nodes are started
(green play indicators).

## diagrams/ospf-neighbors.png
On the R1 console: `show ip ospf neighbor` and `show ip route ospf`, showing the
FULL adjacency with R2 and the learned loopback route.

## screenshots/01-provision.gif
Record running:
```
python provision_lab.py --start
```
Then switch to the GNS3 canvas to show the topology appear and the nodes boot.

## screenshots/02-baseline.gif
Record:
```
python lab_console.py capture --out snapshots/current
python drift_engine.py capture-baseline --source dir --source-dir snapshots/current
git log --oneline
```
The last command shows the baseline-approval commits, making the GitOps flow
visible.

## screenshots/03-detect.gif
Record injecting drift and detecting it:
```
python lab_console.py inject R1 --scenario rogue-user
python lab_console.py inject R2 --scenario ospf-hijack
python lab_console.py inject SW1 --scenario vlan-hop
python lab_console.py capture --out snapshots/current
python drift_engine.py check --source dir --source-dir snapshots/current --report
```
This is the key image: CRITICAL and WARNING drift, per-line severity and the
alerts.

## screenshots/04-dryrun.gif
Record the safe preview:
```
python drift_engine.py check --source dir --source-dir snapshots/current --auto-revert --dry-run --alert-threshold critical
```
Show that the corrective commands are printed and no device is touched.

## screenshots/05-remediate.gif
Record remediation closing the loop:
```
python lab_console.py revert R1
python lab_console.py revert R2
python lab_console.py revert SW1
python lab_console.py capture --out snapshots/current
python drift_engine.py check --source dir --source-dir snapshots/current
```
End on all devices reporting `clean`.

## screenshots/06-tests.png
Record or screenshot:
```
python -m pytest
```
Showing the suite passing.

## Tip

`audit_log.md` and the newest file under `reports/` are good still images to
include as well; they show the persistent record produced by the run.
