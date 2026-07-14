"""NetGuard: configuration drift detection and GitOps compliance for Cisco IOS.

The package is deliberately split into small, single-responsibility modules so
that each stage of the pipeline (inventory, retrieval, normalisation, diffing,
classification, alerting, remediation, audit) can be reasoned about and tested
in isolation.
"""

__version__ = "1.0.0"
