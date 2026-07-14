"""
NetGuard — Configuration Drift Detection Engine
================================================
Connects to each device (Netmiko/SSH), pulls the running-config, compares it
against the git-tracked "golden" baseline, classifies drift severity, and
optionally auto-reverts unauthorized Critical changes.

STATUS: scaffolding only. Logic is implemented after Phase 1 (baseline capture).

Planned CLI:
    python drift_engine.py --check                # detect + report drift
    python drift_engine.py --check --dry-run      # show what a revert WOULD do
    python drift_engine.py --check --auto-revert  # revert Critical drift (always logged)

Severity tiers:
    Critical -> routing / ACL / AAA changes
    Warning  -> VLAN / interface-description changes
    Info     -> cosmetic (banner, comments)
"""

# TODO(Phase 2): connect() + pull_running_config()  via Netmiko
# TODO(Phase 2): diff_against_baseline()             via difflib / ciscoconfparse
# TODO(Phase 2): classify_severity() -> "critical" | "warning" | "info"
# TODO(Phase 4): auto_revert() guarded by --dry-run
# TODO(Phase 5): append_audit_log()


def main() -> None:
    raise NotImplementedError(
        "drift_engine is scaffolding; implemented after the golden baseline is captured (Phase 1)."
    )


if __name__ == "__main__":
    main()
