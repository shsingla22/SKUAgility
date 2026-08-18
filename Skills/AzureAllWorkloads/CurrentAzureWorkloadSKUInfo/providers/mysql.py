"""Azure Database for MySQL flexible server.

Each compute tier has its own compute-size table on the service-tiers page, so
the tier is the section heading and the rows are the SKUs. Tier guidance comes
from the "Target workloads" table on the same page.
"""

from __future__ import annotations

from common import GA, Sku, num, sentences
from milestones import MYSQL_BUSINESS_CRITICAL, MYSQL_FLEX

WORKLOAD = "mysql"
SERVICE = "Azure Database for MySQL"
SOURCES = ["mysql_tiers"]

TIERS = {"Burstable": "Burstable",
         "General Purpose": "General Purpose",
         "Memory-Optimized": "Business Critical"}


def collect(docs: dict) -> list[Sku]:
    doc = docs["mysql_tiers"]

    guide = doc.find_table("Compute tier", "Target workloads")
    guidance = {r[0].strip(): sentences(r[1]) for r in guide.body} if guide else {}

    rows: list[Sku] = []
    for section in doc.sections:
        tier_doc_name = section.heading.strip()
        if tier_doc_name not in TIERS:
            continue
        for table in section.tables:
            if table.column("Compute size") < 0:
                continue
            for row in table.body:
                sku = row[0].strip()
                if not sku.startswith("Standard_"):
                    continue
                tier = TIERS[tier_doc_name]
                when = list(guidance.get(tier_doc_name, []))
                if tier == "Business Critical":
                    when.append("This tier is the former Memory Optimized tier, "
                                "renamed after it gained lower IO latency, higher "
                                "availability and greater scalability.")
                when.append("Confirm the compute size is offered in your target "
                            "region before committing to it.")
                rows.append(Sku(
                    workload=WORKLOAD, service=SERVICE, sku=sku, tier=tier,
                    series=sku.split("_")[1].rstrip("0123456789ms") or "B-series",
                    capacity=num(row[1]), capacity_unit="vCore",
                    memory_gb=num(row[2]) if len(row) > 2 else None,
                    lifecycle_status=GA,
                    milestone=(MYSQL_BUSINESS_CRITICAL if tier == "Business Critical"
                               else MYSQL_FLEX),
                    inventory_doc=doc.url,
                    recommend_when=when,
                    recommend_sources=[doc.url],
                ).resolve())

    if len(rows) < 20:
        raise RuntimeError(f"MySQL: only {len(rows)} compute sizes parsed — the "
                           "service-tiers page changed shape")
    return rows
