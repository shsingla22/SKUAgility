"""Azure Database for PostgreSQL flexible server.

Inventory comes from the server-type table on the compute-options page, which
lists every SKU name with vCores, memory and IOPS. Tier guidance comes from the
"Target workloads" table on the same page, so the recommendation text is
Microsoft's own words rather than a paraphrase of a paraphrase.
"""

from __future__ import annotations

import re

from common import GA, PREVIEW, Sku, num, sentences
from milestones import (
    PG_BURST_LARGE, PG_BURST_SMALL, PG_V3, PG_V4, PG_V5_AMD, PG_V5_INTEL, PG_V6,
)

WORKLOAD = "postgresql"
SERVICE = "Azure Database for PostgreSQL"
SOURCES = ["pg_compute", "pg_overview"]

LARGE_BURSTABLE = {"B4ms", "B8ms", "B12ms", "B16ms", "B20ms"}

# Typographical errors in the published server-type table, corrected explicitly so
# the catalog neither repeats a wrong SKU name nor silently drops a real one. Each
# entry is surfaced in the output; none of them invents a SKU that Microsoft does
# not otherwise document (every corrected name appears elsewhere in Azure's own
# compute-series documentation and pricing).
ERRATA = {
    "D16ds_v5 / D16ds_v5": ("D16ds_v5 / D16ads_v5",
                            "the AMD half of the pair repeats the Intel name"),
    "E16ds_v5 / E16ds_v5": ("E16ds_v5 / E16ads_v5",
                            "the AMD half of the pair repeats the Intel name"),
    "E32ds_v5 / D32ads_v5": ("E32ds_v5 / E32ads_v5",
                             "a D-series name in a Memory Optimized row"),
    "E64ds_v5 / E64ads_v4": ("E64ds_v5 / E64ads_v5",
                             "the AMD half is labelled v4 in a v5 row"),
}

APPLIED_ERRATA: list[dict] = []


def series_of(sku: str) -> str:
    m = re.match(r"^[BDE](\d+)?([a-z]*)_?(v\d)?", sku)
    if sku.startswith("B"):
        return "B-series"
    m = re.search(r"^([DE])\d+(a?d?s)_(v\d)$", sku)
    if not m:
        return "unknown"
    return f"{m.group(1)}{m.group(2)}{m.group(3)}-series".replace("_", "")


def milestone_for(sku: str) -> str:
    if sku.startswith("B"):
        return PG_BURST_LARGE if sku in LARGE_BURSTABLE else PG_BURST_SMALL
    if sku.endswith("_v6"):
        return PG_V6
    if sku.endswith("_v5"):
        return PG_V5_AMD if "ads_v5" in sku else PG_V5_INTEL
    if sku.endswith("_v4"):
        return PG_V4
    return PG_V3


def collect(docs: dict) -> list[Sku]:
    doc = docs["pg_compute"]
    inv = doc.find_table("SKU name", "vCores")
    if inv is None:
        raise RuntimeError("PostgreSQL: the server-type table is no longer on the "
                           "compute-options page")

    guide = doc.find_table("Pricing tier", "Target workloads")
    guidance: dict[str, list[str]] = {}
    if guide:
        for row in guide.body:
            guidance[row[0].strip()] = sentences(row[1])

    tier_note = ("v6 SKUs are in public preview: scaling between the Burstable tier "
                 "and a v6 SKU is not supported, and virtual network integration is "
                 "not available on v6.")

    rows: list[Sku] = []
    tier = ""
    APPLIED_ERRATA.clear()
    for row in inv.body:
        name = row[0].strip()
        if not name:
            continue
        if name in ERRATA:
            fixed, why = ERRATA[name]
            APPLIED_ERRATA.append({
                "workload": WORKLOAD, "published": name, "corrected": fixed,
                "reason": why, "source": doc.url,
            })
            name = fixed
        # A row with only a bold tier name and empty cells is a group separator.
        if len(row) < 2 or not any(c.strip() for c in row[1:3]):
            tier = name
            continue
        # Cells may list two equivalent SKUs, e.g. "D2ds_v5 / D2ads_v5".
        for part in re.split(r"\s*/\s*", name):
            part = part.strip()
            if not re.match(r"^(B\d+m?s|[DE]\d+a?d?s_v\d)$", part):
                continue
            sku = f"Standard_{part}"
            preview = part.endswith("_v6")
            when = list(guidance.get(tier, []))
            when.append("Confirm the SKU is offered in your target region: "
                        "PostgreSQL compute generations are not available everywhere.")
            if preview:
                when.append(tier_note)
            rows.append(Sku(
                workload=WORKLOAD, service=SERVICE, sku=sku, tier=tier,
                series=series_of(part), capacity=num(row[1]), capacity_unit="vCore",
                memory_gb=num(row[2]) if len(row) > 2 else None,
                lifecycle_status=PREVIEW if preview else GA,
                milestone=milestone_for(part),
                inventory_doc=doc.url,
                recommend_when=when,
                recommend_sources=[doc.url, docs["pg_overview"].url],
            ).resolve())

    if len(rows) < 60:
        raise RuntimeError(f"PostgreSQL: only {len(rows)} SKUs parsed, expected many "
                           "more — the server-type table changed shape")
    # The doc lists some sizes twice across tiers; keep the first of each.
    seen, unique = set(), []
    for r in rows:
        k = (r.sku, r.tier)
        if k not in seen:
            seen.add(k)
            unique.append(r)
    return unique
