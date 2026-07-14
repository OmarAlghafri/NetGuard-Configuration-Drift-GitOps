"""Git-backed golden baseline store.

The approved configuration of each device lives under ``baselines/`` and is
version controlled. Git is the source of truth: capturing a baseline commits it,
so the history answers "what was approved, and when" for every device. Drift is
always measured against the committed baseline, never against an ad-hoc copy.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASELINES = REPO / "baselines"


def baseline_path(device: str) -> Path:
    return BASELINES / f"{device}.cfg"


def has_baseline(device: str) -> bool:
    return baseline_path(device).exists()


def read_baseline(device: str) -> str:
    return baseline_path(device).read_text(encoding="utf-8")


def write_baseline(device: str, config: str) -> Path:
    BASELINES.mkdir(parents=True, exist_ok=True)
    path = baseline_path(device)
    path.write_text(config, encoding="utf-8")
    return path


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=False
    )


def commit_baseline(device: str, message: str) -> bool:
    """Stage and commit a device's baseline. Returns True if a commit was made."""
    _git("add", str(baseline_path(device).relative_to(REPO)))
    status = _git("status", "--porcelain", "--", str(baseline_path(device).relative_to(REPO)))
    if not status.stdout.strip():
        return False
    result = _git("commit", "-m", message)
    return result.returncode == 0


def baseline_history(device: str) -> str:
    """Return the git log for a device's baseline (approval history)."""
    result = _git("log", "--oneline", "--", str(baseline_path(device).relative_to(REPO)))
    return result.stdout.strip()
