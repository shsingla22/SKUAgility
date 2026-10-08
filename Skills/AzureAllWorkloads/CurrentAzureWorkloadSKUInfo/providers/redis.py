"""Azure Cache for Redis.

Every tier of this service is on a retirement path, which dominates the
recommendation for all of them: Microsoft directs new work to Azure Managed
Redis. The retirement dates are read from the what's-new page rather than
hard-coded, so they stay correct if Microsoft moves them.
"""

from __future__ import annotations

import re

from common import Sku, retiring, sentences
from milestones import MILESTONES, REDIS_ENTERPRISE, REDIS_OSS

WORKLOAD = "redis"
SERVICE = "Azure Cache for Redis"
SOURCES = ["redis_overview", "redis_whats_new"]

OSS_TIERS = {"Basic", "Standard", "Premium"}


def retirement_dates(whats_new) -> dict[str, str]:
    """Pull the retirement dates out of the timetable tables."""
    found = {}
    for section in whats_new.sections:
        for table in section.tables:
            if table.column("Date") < 0:
                continue
            for row in table.body:
                if len(row) < 2 or "retired" not in row[1].lower():
                    continue
                date = row[0].strip()
                text = row[1].lower()
                if "enterprise" in text:
                    found["enterprise"] = date
                elif any(t.lower() in text for t in OSS_TIERS):
                    found["oss"] = date
    # The Enterprise timetable heading names the tiers rather than the row.
    for section in whats_new.sections:
        if "enterprise" in section.heading.lower():
            for table in section.tables:
                for row in table.body:
                    if len(row) > 1 and "retired" in row[1].lower():
                        found.setdefault("enterprise", row[0].strip())
    return found


def collect(docs: dict) -> list[Sku]:
    overview, whats_new = docs["redis_overview"], docs["redis_whats_new"]

    tiers = overview.find_table("Tier", "Description")
    if tiers is None:
        raise RuntimeError("Redis: the service-tier table is no longer on the "
                           "overview page")

    dates = retirement_dates(whats_new)
    rows: list[Sku] = []
    for row in tiers.body:
        tier = row[0].strip()
        if not tier:
            continue
        is_oss = tier in OSS_TIERS
        milestone = REDIS_OSS if is_oss else REDIS_ENTERPRISE
        retire = dates.get("oss" if is_oss else "enterprise") \
            or MILESTONES[milestone].retirement or "announced"

        when = sentences(row[1])
        when.insert(0, f"Do not choose this tier for new work. Microsoft has "
                       f"announced the retirement of all Azure Cache for Redis "
                       f"SKUs; this tier retires on {retire}.")
        when.append("Migrate existing caches to Azure Managed Redis, which "
                    "Microsoft names as the replacement service.")
        when.append("Creating new caches was blocked for new customers on "
                    "1 April 2026; only tenants that already had a cache can "
                    "still create one.")

        rows.append(Sku(
            workload=WORKLOAD, service=SERVICE, sku=tier, tier=tier,
            series="Enterprise" if not is_oss else "OSS Redis",
            capacity=None, capacity_unit="tier", memory_gb=None,
            lifecycle_status=retiring(retire),
            milestone=milestone,
            inventory_doc=overview.url,
            recommend_when=when,
            recommend_sources=[overview.url, whats_new.url],
        ).resolve())

    if len(rows) < 5:
        raise RuntimeError(f"Redis: only {len(rows)} tiers parsed, expected at "
                           "least Basic, Standard, Premium, Enterprise and "
                           "Enterprise Flash")
    return rows
