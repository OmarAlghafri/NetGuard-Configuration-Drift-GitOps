# Capture guide

The images referenced by the README are captured here. Most are still
screenshots; two are optional short recordings.

## Tools

- Still screenshots: the Windows Snipping Tool (`Win`+`Shift`+`S`), saved as PNG.
- Recordings (optional): ScreenToGif (free) records a screen region and exports a
  GIF directly.

## One-time setup

Open a PowerShell window in the project folder (Shift+right-click the folder,
"Open PowerShell window here") and activate the virtual environment so `python`
resolves to the project interpreter:

```
.venv\Scripts\Activate.ps1
```

After that, the `python ...` commands below run as written.

## The quick way

`demo.ps1` runs the whole story and pauses between stages so a screenshot can be
taken at each one:

```
.\demo.ps1
```

That single script covers images 02 through 05 below. Use the per-image notes
for the GNS3 canvas shots and the test run, which are separate.

Suggested terminal: a maximised window, readable font size, dark background.

## diagrams/topology.png
The GNS3 canvas with R1, R2, SW1, the management switch and the host cloud, links
visible. Take this after `provision_lab.py` runs and the nodes are started
(green play indicators).

## diagrams/ospf-neighbors.png
On the R1 console: `show ip ospf neighbor` and `show ip route ospf`, showing the
FULL adjacency with R2 and the learned loopback route.

The five stage images below are produced in one pass by `demo.ps1`, which pauses
after each stage so it can be captured.

## screenshots/01-baseline.png
Stage 1: every device reports `clean` and `git log` shows the baseline-approval
commits, making the GitOps flow visible.

## screenshots/02-inject.png
Stage 2: the three drift scenarios are applied to the live devices.

## screenshots/03-detect.png
Stage 3 (the key image): R1 and R2 report CRITICAL drift and SW1 reports WARNING,
each with per-line severity and an alert.

## screenshots/04-dryrun.png
Stage 4: the revert preview prints the corrective commands for the CRITICAL drift
only, without touching any device.

## screenshots/05-remediate.png
Stage 5: the devices are reverted and every one returns to `clean`.

## screenshots/06-tests.png (optional)
The test suite passing:
```
python -m pytest
```
