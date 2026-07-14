# NetGuard - Audit Log

Append-only record of every drift check; one row per device per run, whether or
not drift was found. Rows are appended automatically by `drift_engine.py`.

| Timestamp | Device | Result | Severity | Action | Notes |
|-----------|--------|--------|----------|--------|-------|
