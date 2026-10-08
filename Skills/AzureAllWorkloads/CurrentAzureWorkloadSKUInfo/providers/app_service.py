"""Azure App Service plans.

The hosting-plans page groups tiers into shared, dedicated and isolated compute
categories and explains what each category is for. Individual instance sizes
(B1, P1v3 and so on) are documented per tier on the pricing page rather than in
a single table, so this provider records the tier, which is the unit the
category guidance and the lifecycle actually apply to.
"""

from __future__ import annotations

import re

from common import GA, Sku, sentences
from milestones import (
    APPSVC_BASE, APPSVC_ISOLATED, APPSVC_PV2, APPSVC_PV3, APPSVC_PV4,
)

WORKLOAD = "app_service"
SERVICE = "Azure App Service"
SOURCES = ["appservice_plans"]

MILESTONE_FOR = {
    "PremiumV4": APPSVC_PV4,
    "PremiumV3": APPSVC_PV3,
    "PremiumV2": APPSVC_PV2,
    "IsolatedV2": APPSVC_ISOLATED,
}


def collect(docs: dict) -> list[Sku]:
    doc = docs["appservice_plans"]
    table = doc.find_table("Category", "Tiers")
    if table is None:
        raise RuntimeError("App Service: the pricing-tier table is no longer on "
                           "the hosting-plans page")

    rows: list[Sku] = []
    for row in table.body:
        category, tier_list, description = row[0].strip(), row[1], row[2]
        guidance = sentences(description)
        for tier in [t.strip() for t in re.split(r",| and ", tier_list) if t.strip()]:
            when = list(guidance)
            when.insert(0, f"This tier belongs to the {category.lower()} category "
                           f"of App Service plans.")
            if category.startswith("Shared"):
                when.append("Do not use for production: the shared tiers are "
                            "intended only for development and testing, and "
                            "cannot scale out.")
            rows.append(Sku(
                workload=WORKLOAD, service=SERVICE, sku=tier, tier=tier,
                series=category, capacity=None, capacity_unit="tier",
                memory_gb=None, lifecycle_status=GA,
                milestone=MILESTONE_FOR.get(tier, APPSVC_BASE),
                inventory_doc=doc.url,
                recommend_when=when,
                recommend_sources=[doc.url],
            ).resolve())

    if len(rows) < 5:
        raise RuntimeError(f"App Service: only {len(rows)} tiers parsed")
    return rows
