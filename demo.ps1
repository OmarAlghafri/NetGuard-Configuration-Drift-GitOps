# NetGuard guided demo.
# Run from a PowerShell window opened in the project folder:  .\demo.ps1
# It pauses between stages so each result can be captured before continuing.

Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Stage([int]$n, [string]$title) {
    Write-Host ""
    Write-Host ("=" * 66) -ForegroundColor Cyan
    Write-Host ("  STAGE {0} :: {1}" -f $n, $title) -ForegroundColor Cyan
    Write-Host ("=" * 66) -ForegroundColor Cyan
}
function Wait-Capture([string]$msg) {
    Write-Host ""
    Read-Host ("[capture now] {0} - then press Enter" -f $msg) | Out-Null
}

Stage 1 "Baseline is clean and committed (GitOps)"
& $py lab_console.py capture --out snapshots/current
& $py drift_engine.py check --source dir --source-dir snapshots/current
git log --oneline -8
Wait-Capture "screenshot the clean check and baseline commits"

Stage 2 "Inject unauthorised changes on the live devices"
& $py lab_console.py inject R1 --scenario rogue-user
& $py lab_console.py inject R2 --scenario ospf-hijack
& $py lab_console.py inject SW1 --scenario vlan-hop
Wait-Capture "drift injected"

Stage 3 "Detect and classify the drift (key result)"
& $py lab_console.py capture --out snapshots/current
& $py drift_engine.py check --source dir --source-dir snapshots/current --report
Wait-Capture "screenshot the CRITICAL/WARNING detection and alerts"

Stage 4 "Preview the auto-revert (safe: no device is touched)"
& $py drift_engine.py check --source dir --source-dir snapshots/current --auto-revert --dry-run --alert-threshold critical
Wait-Capture "screenshot the revert preview"

Stage 5 "Remediate and verify the network is clean again"
& $py lab_console.py revert R1
& $py lab_console.py revert R2
& $py lab_console.py revert SW1
& $py lab_console.py capture --out snapshots/current
& $py drift_engine.py check --source dir --source-dir snapshots/current
Wait-Capture "screenshot all devices clean - demo complete"

Write-Host "`nDone." -ForegroundColor Green
