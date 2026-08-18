"""Azure SQL Database and Azure SQL Managed Instance.

This provider does not re-implement Azure SQL. The sibling skill
Skills/AzureSQL/CurrentAzureSQLSKUInfo already reads the Azure SQL articles,
parses every service-level objective out of them and carries a reviewed set of
release milestones and doc-sourced guidance. Duplicating that here would create
a second source of truth that drifts.

Instead this runs that skill and adapts its output. If the sibling skill is not
present the provider says so plainly and the workload is reported as
unavailable, rather than the catalog quietly shipping without Azure SQL.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from common import Sku
from milestones import MILESTONES, Milestone

WORKLOAD = "azure_sql"
SERVICE = "Azure SQL"
SOURCES: list[str] = []          # it owns its own sources, via the sibling skill

SKILL_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "AzureSQL", "CurrentAzureSQLSKUInfo"))


def available() -> bool:
    return os.path.exists(os.path.join(SKILL_DIR, "scripts", "refresh.py"))


def run_sibling(cache: str, offline: bool = False) -> dict:
    out_dir = os.path.join(cache, "azure_sql")
    os.makedirs(out_dir, exist_ok=True)
    cmd = [sys.executable, os.path.join(SKILL_DIR, "scripts", "refresh.py"),
           "--out-dir", out_dir,
           "--cache", os.path.join(cache, "azure_sql_docs"),
           "--skip-links"]          # this skill link-checks everything itself
    if offline:
        cmd.append("--offline")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    # exit 2 means "built and verified, but the inventory moved" — still usable,
    # and this skill's own diff will report the movement.
    if proc.returncode not in (0, 2):
        raise RuntimeError(
            "the CurrentAzureSQLSKUInfo skill failed:\n"
            + (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:])
    with open(os.path.join(out_dir, "azure-sql-skus.json"), encoding="utf-8") as fh:
        return json.load(fh)


def collect(docs: dict, cache: str = "", offline: bool = False) -> list[Sku]:
    if not available():
        raise RuntimeError(
            f"the sibling skill is missing at {SKILL_DIR}. Azure SQL is produced by "
            "Skills/AzureSQL/CurrentAzureSQLSKUInfo; restore it or drop azure_sql "
            "from the provider registry.")

    data = run_sibling(cache, offline=offline)

    # Adopt the sibling's milestones so dates and confidence survive intact.
    for m in data["release_milestones"]:
        MILESTONES.setdefault(m["key"], Milestone(
            key=m["key"], label=m["label"], preview=m["preview"], ga=m["ga"],
            confidence=m["confidence"], source=m["source"], note=m.get("note", "")))

    rows = []
    for s in data["skus"]:
        rows.append(Sku(
            workload=WORKLOAD,
            service=s["service"],
            sku=s["sku"],
            tier=s["service_tier"] + ("" if s["compute_tier"] == "Provisioned"
                                      else f" - {s['compute_tier']}"),
            series=s["hardware"],
            capacity=s["capacity"],
            capacity_unit=s["capacity_unit"],
            memory_gb=s["memory_gb"],
            lifecycle_status=s["lifecycle_status"],
            milestone=s["milestone"],
            inventory_doc=s["inventory_doc"],
            recommend_when=s["recommend_when"],
            recommend_sources=s["recommend_sources"],
            notes=s.get("notes", ""),
        ).resolve())
    return rows
