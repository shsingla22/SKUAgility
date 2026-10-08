#!/usr/bin/env python3
"""Build the Azure Database for PostgreSQL SKU catalog.

Emits:

    data/azure-postgresql.json   machine-readable catalog + release milestones
    data/skus.csv                flat table
    docs/azure-postgresql-skus.md

Azure SQL is NOT built here. It is owned end to end by the
Skills/AzureSQL/CurrentAzureSQLSKUInfo skill, which reads the Microsoft Learn
article sources directly instead of carrying a hand-maintained SKU list.

Run with:  python3 tools/build_catalog.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict, dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
DOCS = os.path.join(ROOT, "docs")

CATALOG_AS_OF = "2026-08-17"


# ---------------------------------------------------------------------------
# Release milestones
#
# Every SKU points at one of these. `ga` / `preview` are ISO dates truncated to
# the precision we can actually defend from a public Microsoft source, and
# `confidence` says how much weight to put on that date:
#
#   high   - a dated Microsoft announcement / release note names this exact thing
#   medium - a Microsoft page dates the change to a month, or a reputable
#            secondary source corroborates a first-party announcement
#   low    - the date is reconstructed from context; treat as approximate
# ---------------------------------------------------------------------------


@dataclass
class Milestone:
    key: str
    label: str
    preview: str | None
    ga: str | None
    confidence: str
    source: str
    note: str = ""


MILESTONES: dict[str, Milestone] = {}


def milestone(**kwargs) -> str:
    m = Milestone(**kwargs)
    MILESTONES[m.key] = m
    return m.key


# --- Azure Database for PostgreSQL ---------------------------------------

PG_FLEX = milestone(
    key="pg-flexible-server",
    label="Azure Database for PostgreSQL flexible server",
    preview="2020-11",
    ga="2021-11",
    confidence="high",
    source="https://azure.microsoft.com/updates?id=general-availability-azure-database-for-postgresql-flexible-server",
)

PG_V3 = milestone(
    key="pg-v3",
    label="v3 compute series (Dsv3 General Purpose, Esv3 Memory Optimized)",
    preview="2020-11",
    ga="2021-11",
    confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/release-notes/release-notes",
    note="v3 was the launch compute series for flexible server; it reached GA with the service.",
)

PG_V4 = milestone(
    key="pg-v4",
    label="v4 compute series (Ddsv4 General Purpose, Edsv4 Memory Optimized)",
    preview=None,
    ga="2021-10",
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/adforpostgresql/flexible-server-now-supports-v4-compute-series-in-postgresql-on-azure/2815092",
)

PG_BURST_SMALL = milestone(
    key="pg-burstable-small",
    label="Burstable tier, B1ms / B2s / B2ms",
    preview="2020-11",
    ga="2021-11",
    confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
    note="The original burstable sizes; GA with flexible server.",
)

PG_BURST_LARGE = milestone(
    key="pg-burstable-large",
    label="Burstable tier, B4ms / B8ms / B12ms / B16ms / B20ms",
    preview=None,
    ga="2023-04",
    confidence="high",
    source="https://azure.microsoft.com/updates/generally-available-new-burstable-skus-for-azure-database-for-postgresql-flexible-server/",
)

PG_V5_INTEL = milestone(
    key="pg-v5-intel",
    label="Intel v5 compute series (Ddsv5 General Purpose, Edsv5 Memory Optimized)",
    preview=None,
    ga="2023-05",
    confidence="high",
    source="https://techcommunity.microsoft.com/t5/azure-database-for-postgresql/introducing-intel-v5-compute-and-32-tb-storage-support-on-azure/ba-p/3839849",
    note="Announced 2023-06-05 covering the May 2023 release; listed in the May 2023 release notes.",
)

PG_V5_AMD = milestone(
    key="pg-v5-amd",
    label="AMD v5 compute series (Dadsv5 General Purpose, Eadsv5 Memory Optimized)",
    preview=None,
    ga="2023",
    confidence="low",
    source="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
    note="Rolled out during 2023 after the Intel v5 series; reserved capacity for both Intel "
    "and AMD v5 SKUs landed in September 2024. Exact GA month not confirmed.",
)

PG_V6 = milestone(
    key="pg-v6",
    label="v6 compute series (Ddsv6 / Dadsv6 General Purpose, Edsv6 / Eadsv6 Memory Optimized)",
    preview="2025",
    ga=None,
    confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/overview",
    note="PUBLIC PREVIEW as of the catalog date. Scaling between Burstable and v6 is not "
    "supported, and virtual network integration is not supported on v6.",
)

PG_SINGLE = milestone(
    key="pg-single-server",
    label="Azure Database for PostgreSQL single server (Basic / General Purpose / Memory Optimized)",
    preview="2017-05",
    ga="2018-03",
    confidence="low",
    source="https://learn.microsoft.com/azure/postgresql/single-server/whats-happening-to-postgresql-single-server",
    note="RETIRED on 2025-03-28. Listed for historical completeness only; not orderable.",
)


# ---------------------------------------------------------------------------
# SKU records
# ---------------------------------------------------------------------------


@dataclass
class Sku:
    sku: str
    service: str
    deployment_model: str
    purchasing_model: str
    service_tier: str
    compute_tier: str
    hardware: str
    capacity_unit: str
    capacity: float
    memory_gb: float | None
    memory_gb_per_vcore: float | None
    status: str
    milestone: str
    lifecycle_status: str = "Generally available"
    inventory_doc: str = ""
    guidance_key: str = ""
    release_date: str = ""
    preview_date: str | None = None
    ga_date: str | None = None
    date_confidence: str = ""
    release_doc: str = ""
    recommend_when: list[str] = field(default_factory=list)
    recommend_sources: list[str] = field(default_factory=list)
    notes: str = ""

    def resolve(self) -> "Sku":
        m = MILESTONES[self.milestone]
        self.preview_date = m.preview
        self.ga_date = m.ga
        self.date_confidence = m.confidence
        self.release_doc = m.source
        if m.note and not self.notes:
            self.notes = m.note

        if self.lifecycle_status == "Public preview":
            self.release_date = self.preview_date or "unknown"
        else:
            self.release_date = self.ga_date or self.preview_date or "unknown"

        if self.guidance_key:
            note, note_src = PURCHASING_MODEL_NOTE[self.purchasing_model]
            when: list[str] = [note]
            sources: list[str] = [note_src]
            # A SKU can inherit guidance from more than one axis, e.g. a managed
            # instance SKU inherits both its service tier and its hardware family.
            for key in self.guidance_key.split("+"):
                entry = GUIDANCE[key]
                when += list(entry["when"])
                sources += [s for s in entry["sources"] if s not in sources]
            self.recommend_when = when
            self.recommend_sources = sources
        return self


SKUS: list[Sku] = []


DEFAULT_LIFECYCLE = {
    "GA": "Generally available",
    "Preview": "Public preview",
    "Retired": "Retired",
}


def add(**kwargs) -> None:
    kwargs.setdefault("lifecycle_status", DEFAULT_LIFECYCLE[kwargs["status"]])
    SKUS.append(Sku(**kwargs).resolve())


# ---- Azure Database for PostgreSQL flexible server -----------------------

PG = "Azure Database for PostgreSQL"

PG_BURSTABLE = [
    ("B1ms", 1, 2, PG_BURST_SMALL),
    ("B2s", 2, 4, PG_BURST_SMALL),
    ("B2ms", 2, 8, PG_BURST_SMALL),
    ("B4ms", 4, 16, PG_BURST_LARGE),
    ("B8ms", 8, 32, PG_BURST_LARGE),
    ("B12ms", 12, 48, PG_BURST_LARGE),
    ("B16ms", 16, 64, PG_BURST_LARGE),
    ("B20ms", 20, 80, PG_BURST_LARGE),
]

for name, vcores, memory, ms in PG_BURSTABLE:
    add(
        inventory_doc="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
        sku=f"Standard_{name}",
        service=PG,
        deployment_model="Flexible server",
        purchasing_model="vCore",
        service_tier="Burstable",
        compute_tier="Burstable",
        hardware="B-series",
        capacity_unit="vCore",
        capacity=vcores,
        memory_gb=float(memory),
        memory_gb_per_vcore=round(memory / vcores, 2),
        status="GA",
        milestone=ms,
        notes="Not recommended for production; CPU credit model.",
    )

# (series, tier, template, sizes, GB/vCore, milestone, status, overrides)
PG_SERIES = [
    ("Dsv3-series", "General Purpose", "Standard_D{n}s_v3",
     [2, 4, 8, 16, 32, 48, 64], 4, PG_V3, "GA", {}),
    ("Ddsv4-series", "General Purpose", "Standard_D{n}ds_v4",
     [2, 4, 8, 16, 32, 48, 64], 4, PG_V4, "GA", {}),
    ("Ddsv5-series", "General Purpose", "Standard_D{n}ds_v5",
     [2, 4, 8, 16, 32, 48, 64, 96], 4, PG_V5_INTEL, "GA", {}),
    ("Dadsv5-series", "General Purpose", "Standard_D{n}ads_v5",
     [2, 4, 8, 16, 32, 48, 64, 96], 4, PG_V5_AMD, "GA", {}),
    ("Ddsv6-series", "General Purpose", "Standard_D{n}ds_v6",
     [2, 4, 8, 16, 32, 48, 64, 96, 128, 192], 4, PG_V6, "Preview", {}),
    ("Dadsv6-series", "General Purpose", "Standard_D{n}ads_v6",
     [2, 4, 8, 16, 32, 48, 64, 96], 4, PG_V6, "Preview", {}),
    ("Esv3-series", "Memory Optimized", "Standard_E{n}s_v3",
     [2, 4, 8, 16, 32, 48, 64], 8, PG_V3, "GA", {64: 432}),
    ("Edsv4-series", "Memory Optimized", "Standard_E{n}ds_v4",
     [2, 4, 8, 16, 20, 32, 48, 64], 8, PG_V4, "GA", {64: 432}),
    ("Edsv5-series", "Memory Optimized", "Standard_E{n}ds_v5",
     [2, 4, 8, 16, 20, 32, 48, 64, 96], 8, PG_V5_INTEL, "GA", {96: 672}),
    ("Eadsv5-series", "Memory Optimized", "Standard_E{n}ads_v5",
     [2, 4, 8, 16, 20, 32, 48, 64, 96], 8, PG_V5_AMD, "GA", {96: 672}),
    ("Edsv6-series", "Memory Optimized", "Standard_E{n}ds_v6",
     [2, 4, 8, 16, 20, 32, 48, 64, 96, 128, 192], 8, PG_V6, "Preview",
     {96: 768, 128: 1024, 192: 1832}),
    ("Eadsv6-series", "Memory Optimized", "Standard_E{n}ads_v6",
     [2, 4, 8, 16, 20, 32, 48, 64, 96], 8, PG_V6, "Preview", {96: 672}),
]

for series, tier, template, sizes, ratio, ms, status, overrides in PG_SERIES:
    for vcores in sizes:
        memory = float(overrides.get(vcores, vcores * ratio))
        add(
            inventory_doc="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
            sku=template.format(n=vcores),
            service=PG,
            deployment_model="Flexible server",
            purchasing_model="vCore",
            service_tier=tier,
            compute_tier="Provisioned",
            hardware=series,
            capacity_unit="vCore",
            capacity=vcores,
            memory_gb=memory,
            memory_gb_per_vcore=round(memory / vcores, 2),
            status=status,
            milestone=ms,
        )

# ---- Azure Database for PostgreSQL single server (retired) ---------------

PG_SINGLE_TIERS = [
    ("Basic", "B_Gen5_{n}", [1, 2]),
    ("General Purpose", "GP_Gen5_{n}", [2, 4, 8, 16, 32, 64]),
    ("Memory Optimized", "MO_Gen5_{n}", [2, 4, 8, 16, 32]),
]

for tier, template, sizes in PG_SINGLE_TIERS:
    for vcores in sizes:
        add(
            inventory_doc="https://learn.microsoft.com/azure/postgresql/single-server/whats-happening-to-postgresql-single-server",
            sku=template.format(n=vcores),
            service=PG,
            deployment_model="Single server (retired)",
            purchasing_model="vCore",
            service_tier=tier,
            compute_tier="Provisioned",
            hardware="Gen5",
            capacity_unit="vCore",
            capacity=vcores,
            memory_gb=None,
            memory_gb_per_vcore=None,
            status="Retired",
            milestone=PG_SINGLE,
        )


# ---------------------------------------------------------------------------
# Emitters
# ---------------------------------------------------------------------------


def payload(services: list[str]) -> dict:
    rows = [asdict(s) for s in SKUS if s.service in services]
    used = {r["milestone"] for r in rows}
    return {
        "catalog_as_of": CATALOG_AS_OF,
        "services": services,
        "sku_count": len(rows),
        "date_confidence_legend": {
            "high": "a dated Microsoft announcement or release note names this exact change",
            "medium": "a Microsoft page dates the change to a month, or a reputable secondary "
                      "source corroborates a first-party announcement",
            "low": "reconstructed from context; treat the date as approximate",
        },
        "release_milestones": [asdict(MILESTONES[k]) for k in MILESTONES if k in used],
        "skus": rows,
    }


def write_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def write_csv(path: str) -> None:
    fields = list(asdict(SKUS[0]).keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for s in SKUS:
            writer.writerow(asdict(s))


def date_cell(s: Sku) -> str:
    if s.status == "Preview":
        return f"{s.preview_date or '?'} (preview)"
    if s.status == "Retired":
        return f"{s.ga_date or '?'} (retired)"
    return s.ga_date or (s.preview_date or "?")


def md_table(rows: list[Sku]) -> list[str]:
    out = [
        "| SKU | Tier | Hardware | vCores/DTU | Memory (GB) | Status | Released | Confidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in rows:
        capacity = f"{s.capacity:g}"
        memory = f"{s.memory_gb:g}" if s.memory_gb is not None else "—"
        out.append(
            f"| `{s.sku}` | {s.service_tier} | {s.hardware} | {capacity} | {memory} | "
            f"{s.status} | {date_cell(s)} | {s.date_confidence} |"
        )
    return out


def write_markdown(path: str, title: str, intro: str, services: list[str],
                   group_by) -> None:
    rows = [s for s in SKUS if s.service in services]
    lines = [f"# {title}", "", f"Catalog as of **{CATALOG_AS_OF}**. "
             f"{len(rows)} SKUs.", "", intro, ""]

    groups: dict[str, list[Sku]] = {}
    for s in rows:
        groups.setdefault(group_by(s), []).append(s)

    for name, items in groups.items():
        lines += [f"## {name}", ""]
        lines += md_table(items)
        lines += [""]

    used = {s.milestone for s in rows}
    lines += ["## Release milestones", "",
              "The `Released` column above is the GA date of the milestone a SKU belongs to "
              "(or its preview date when the SKU is still in preview).", "",
              "| Milestone | Preview | GA | Confidence | Source |",
              "| --- | --- | --- | --- | --- |"]
    for key in MILESTONES:
        if key not in used:
            continue
        m = MILESTONES[key]
        lines.append(
            f"| {m.label} | {m.preview or '—'} | {m.ga or '—'} | {m.confidence} | "
            f"[link]({m.source}) |"
        )
    lines.append("")

    notes = [MILESTONES[k] for k in MILESTONES if k in used and MILESTONES[k].note]
    if notes:
        lines += ["### Milestone notes", ""]
        for m in notes:
            lines.append(f"- **{m.label}** — {m.note}")
        lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)

    write_json(os.path.join(DATA, "azure-postgresql.json"), payload([PG]))
    write_csv(os.path.join(DATA, "azure-postgresql.csv"))

    write_markdown(
        os.path.join(DOCS, "azure-postgresql-skus.md"),
        "Azure Database for PostgreSQL SKU catalog",
        "Covers Azure Database for PostgreSQL flexible server, plus the retired single "
        "server deployment model for historical reference.",
        [PG],
        lambda s: f"{s.deployment_model} — {s.service_tier} — {s.hardware}",
    )

    print(f"{len(SKUS)} SKUs written")
    for svc in (PG,):
        print(f"  {svc}: {sum(1 for s in SKUS if s.service == svc)}")


if __name__ == "__main__":
    main()
