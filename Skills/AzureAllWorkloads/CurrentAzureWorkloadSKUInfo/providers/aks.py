"""Azure Kubernetes Service pricing tiers.

The pricing-tier table on the AKS page has a literal "When to use" column, so
the recommendation conditions here are Microsoft's own wording with almost no
transformation.
"""

from __future__ import annotations

from common import GA, Sku, sentences
from milestones import AKS_PREMIUM, AKS_TIERS

WORKLOAD = "aks"
SERVICE = "Azure Kubernetes Service"
SOURCES = ["aks_tiers"]


def collect(docs: dict) -> list[Sku]:
    doc = docs["aks_tiers"]
    table = doc.find_table("Tier", "When to use")
    if table is None:
        raise RuntimeError("AKS: the pricing-tier comparison table is no longer "
                           "on the pricing-tiers page")

    i_when = table.column("When to use")
    i_types = table.column("Supported cluster types")
    i_features = table.column("Feature comparison")

    rows: list[Sku] = []
    for row in table.body:
        tier = row[0].strip()
        if not tier:
            continue
        when = sentences(row[i_when]) if i_when >= 0 else []
        if i_types >= 0:
            when += sentences(row[i_types])
        if i_features >= 0:
            when += sentences(row[i_features])
        rows.append(Sku(
            workload=WORKLOAD, service=SERVICE, sku=tier, tier=tier,
            series="Cluster management tier", capacity=None,
            capacity_unit="tier", memory_gb=None, lifecycle_status=GA,
            milestone=AKS_PREMIUM if tier.lower() == "premium" else AKS_TIERS,
            inventory_doc=doc.url,
            recommend_when=when,
            recommend_sources=[doc.url],
        ).resolve())

    if len(rows) < 3:
        raise RuntimeError(f"AKS: only {len(rows)} tiers parsed, expected Free, "
                           "Standard and Premium")
    return rows
