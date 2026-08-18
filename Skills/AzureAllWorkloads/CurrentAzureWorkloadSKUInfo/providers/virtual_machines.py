"""Azure Virtual Machines, recorded at size-family level.

Azure documents roughly 800 individual VM sizes across dozens of series, spread
over more than a hundred pages, and the authoritative per-size list is the
Resource SKUs API rather than the documentation. What the documentation does
state cleanly, in one table per workload type, is the family: what it is for and
which series it contains. That is the level this provider records, and the level
at which the "which VM should I use" question is actually answered.

Individual series carry their own release dates on their own pages; a family
spans many years, so no family-level release date is asserted.
"""

from __future__ import annotations

import re

from common import GA, Sku, sentences
from milestones import VM_FAMILY

WORKLOAD = "virtual_machines"
SERVICE = "Azure Virtual Machines"
SOURCES = ["vm_sizes"]

TYPES = {"General purpose", "Compute optimized", "Memory optimized",
         "Storage optimized", "GPU accelerated", "FPGA accelerated",
         "High performance compute"}


def collect(docs: dict) -> list[Sku]:
    doc = docs["vm_sizes"]

    rows: list[Sku] = []
    vm_type = ""
    for section in doc.sections:
        heading = section.heading.strip()
        if heading in TYPES:
            vm_type = heading
            continue
        for table in section.tables:
            if table.column("Family") < 0 or table.column("Workloads") < 0:
                continue
            if not vm_type:
                continue
            i_series = table.column("Series")
            for row in table.body:
                family = row[0].strip()
                if not family:
                    continue
                series = []
                if i_series >= 0 and len(row) > i_series:
                    series = [s.strip() for s in
                              re.split(r"\s{2,}|,", row[i_series]) if s.strip()]
                current = [s for s in series if "Previous-gen" not in s]
                when = sentences(row[1], limit=6)
                when.insert(0, f"Choose from the {family} when the workload is "
                               f"{vm_type.lower()}.")
                if current:
                    when.append("Current series in this family: "
                                + ", ".join(current[:8]) + ".")
                if len(series) > len(current):
                    when.append("This family also has previous-generation series; "
                                "prefer a current series for new deployments.")
                when.append("Check the family page for per-series specifications, "
                            "regional availability and any retirement notice.")
                rows.append(Sku(
                    workload=WORKLOAD, service=SERVICE, sku=family, tier=vm_type,
                    series=f"{len(current)} current series",
                    capacity=len(current) or None, capacity_unit="series",
                    memory_gb=None, lifecycle_status=GA, milestone=VM_FAMILY,
                    inventory_doc=doc.url,
                    recommend_when=when,
                    recommend_sources=[doc.url],
                ).resolve())

    if len(rows) < 10:
        raise RuntimeError(f"Virtual Machines: only {len(rows)} families parsed — "
                           "the sizes overview page changed shape")
    return rows
