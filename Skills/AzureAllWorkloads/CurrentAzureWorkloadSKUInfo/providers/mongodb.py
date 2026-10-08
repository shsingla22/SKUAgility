"""Azure DocumentDB (with MongoDB compatibility) — formerly Azure Cosmos DB for MongoDB (vCore).

Microsoft renamed the service on 18 November 2025; the cluster tiers are the same
M-series tiers the vCore service shipped with. Inventory is the "Cluster tier |
vCores | One shard, GiB RAM" table on the compute-and-storage page, plus the Free
Tier, which Microsoft's own page introduces as "a new SKU". The RU-based Azure
Cosmos DB for MongoDB is a different product with no compute sizes and is not
covered here.

Guidance comes from the compute page's own configuration advice (working set,
CPU, storage IOPS) and its burstable-tier description, and from the Free Tier
page's benefits and restrictions.
"""

from __future__ import annotations

import re

from common import GA, Sku, num, sentences
from milestones import MONGO_FREE, MONGO_M10_M20, MONGO_M25, MONGO_VCORE

WORKLOAD = "mongodb"
SERVICE = "Azure DocumentDB (MongoDB-compatible)"
SOURCES = ["ddb_compute", "ddb_overview", "ddb_free", "ddb_release"]

TIER_RE = re.compile(r"^M\d+$")


def milestone_for(tier: str) -> str:
    if tier in ("M10", "M20"):
        return MONGO_M10_M20
    if tier == "M25":
        return MONGO_M25
    return MONGO_VCORE


def rename_note(release_doc) -> str:
    """The rename sentence from the release notes, with its date if stated."""
    sec = release_doc.section("Latest")
    text = sec.text if sec else ""
    m = re.search(r"This\s+(\w+ \d{1,2}, \d{4})\s+release renames the service from\s+(.+?)\s+to\s+Azure DocumentDB",
                  text)
    if m:
        return (f"Renamed from {m.group(2).strip()} to Azure DocumentDB on {m.group(1)} "
                "(service release notes). Cluster tiers are unchanged by the rename.")
    return ("Formerly Azure Cosmos DB for MongoDB (vCore); renamed Azure DocumentDB "
            "(service release notes). Cluster tiers are unchanged by the rename.")


def collect(docs: dict) -> list[Sku]:
    doc = docs["ddb_compute"]
    inv = doc.find_table("Cluster tier", "vCores")
    if inv is None:
        raise RuntimeError("DocumentDB: the cluster-tier table is no longer on the "
                           "compute-and-storage page")

    def section_text(d, needle: str) -> str:
        sec = d.section(needle)
        # The rendered page's first section carries its feedback/summarize chrome.
        return re.sub(r"^.*?Summarize this article for me\s*", "", sec.text, flags=re.S) if sec else ""

    # The configuration advice is a labelled list ("Memory : Ensure that ...").
    # Take the first sentence after each label Microsoft uses, verbatim.
    choose_text = section_text(doc, "Choose optimal configuration")
    choose = []
    for label in ("Memory", "CPU", "Storage IOPS", "Data volume", "Concurrency"):
        m = re.search(rf"{re.escape(label)}\s*:\s*(.+?\.)(?:\s|$)", choose_text)
        if m:
            choose.append(f"{label}: {m.group(1).strip()}")
    working = [t for t in sentences(section_text(doc, "Working set"), limit=8)
               if "RAM" in t]
    burst = sentences(section_text(doc, "What is burstable"), limit=3)
    if len(choose) < 3 or not burst or not working:
        raise RuntimeError("DocumentDB: the configuration, working-set or burstable-tier "
                           "guidance on the compute-and-storage page changed shape")
    note = rename_note(docs["ddb_release"])
    region = "Confirm the cluster tier is offered in your target region before committing to it."

    rows: list[Sku] = []
    for row in inv.body:
        tier = row[0].strip()
        if not TIER_RE.match(tier):
            continue
        burstable = "burstable" in row[1].lower()
        when = []
        if burstable:
            when += burst
        when += choose + working
        when.append(region)
        rows.append(Sku(
            workload=WORKLOAD, service=SERVICE, sku=tier,
            tier="Burstable" if burstable else "Regular",
            series="Cluster tier (burstable vCores)" if burstable else "Cluster tier",
            capacity=num(row[1]), capacity_unit="vCore",
            memory_gb=num(row[2]) if len(row) > 2 else None,
            lifecycle_status=GA, milestone=milestone_for(tier),
            inventory_doc=doc.url,
            recommend_when=when,
            recommend_sources=[doc.url, docs["ddb_overview"].url],
            notes=note,
        ).resolve())

    if len(rows) < 8:
        raise RuntimeError(f"DocumentDB: only {len(rows)} cluster tiers parsed — the "
                           "table changed shape")

    # The Free Tier: a named SKU on its own page, with no published vCore count.
    free = docs["ddb_free"]
    intro = free.section("Build applications")
    restrict = free.section("Restrictions")
    if intro is None or restrict is None:
        raise RuntimeError("DocumentDB: the Free Tier page changed shape")
    when = (sentences(section_text(free, "Build applications"), limit=3)
            + sentences(restrict.text, limit=4))
    when.append(region)
    rows.append(Sku(
        workload=WORKLOAD, service=SERVICE, sku="Free Tier", tier="Free",
        series="Free tier", capacity=None, capacity_unit="vCore", memory_gb=None,
        lifecycle_status=GA, milestone=MONGO_FREE,
        inventory_doc=free.url, recommend_when=when,
        recommend_sources=[free.url, docs["ddb_overview"].url],
        notes=note + " Microsoft does not publish the Free Tier's vCore count or RAM.",
    ).resolve())
    return rows
