"""Provider registry.

Adding a workload is: write a module here, add its sources to
references/sources.json and its milestones to references/milestones.py, then add
it to PROVIDERS. Nothing else in the skill needs to change.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aks                  # noqa: E402
import app_service          # noqa: E402
import azure_sql            # noqa: E402
import mysql                # noqa: E402
import postgresql           # noqa: E402
import redis                # noqa: E402
import virtual_machines     # noqa: E402

PROVIDERS = [
    azure_sql,
    postgresql,
    mysql,
    redis,
    app_service,
    aks,
    virtual_machines,
]

# Providers that publish corrections to typographical errors in the source docs.
def applied_errata() -> list[dict]:
    out = []
    for p in PROVIDERS:
        out += list(getattr(p, "APPLIED_ERRATA", []))
    return out
