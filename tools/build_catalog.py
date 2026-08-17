#!/usr/bin/env python3
"""Build the Azure database SKU catalog.

This script is the single source of truth for the SKU catalog. It emits:

    data/azure-sql.json          Azure SQL Database + Azure SQL Managed Instance
    data/azure-postgresql.json   Azure Database for PostgreSQL
    data/skus.csv                flat, joined view of everything above
    docs/azure-sql-skus.md       human readable catalog
    docs/azure-postgresql-skus.md

Run with:  python3 tools/build_catalog.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import asdict, dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guidance import (  # noqa: E402
    GUIDANCE,
    PURCHASING_MODEL_NOTE,
    RETIRED_FAMILIES,
)

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


# --- Azure SQL Database --------------------------------------------------

DTU_CORE = milestone(
    key="sqldb-dtu-core",
    label="DTU purchasing model: Basic, Standard, Premium service tiers",
    preview="2014-04",
    ga="2014-09",
    confidence="medium",
    source="https://azure.microsoft.com/en-us/blog/new-azure-sql-database-service-tiers-generally-available-in-september-with-reduced-pricing-and-enhanced-sla/",
    note="Basic/Standard/Premium reached GA in September 2014; GA pricing took effect 2014-11-01.",
)

DTU_P4_P11 = milestone(
    key="sqldb-dtu-p4-p11",
    label="DTU Premium performance levels P4 and P11",
    preview="2014-09",
    ga="2015",
    confidence="low",
    source="https://azure.microsoft.com/en-us/blog/new-azure-sql-database-service-tiers-generally-available-in-september-with-reduced-pricing-and-enhanced-sla/",
    note="P4 and P11 were introduced alongside the 2014 tier refresh; exact GA month not "
    "recoverable from a first-party dated announcement. Treat the year as approximate.",
)

DTU_EXPANDED = milestone(
    key="sqldb-dtu-expanded",
    label="Expanded DTU performance levels S4, S6, S7, S9, S12",
    preview="2016-02",
    ga="2016",
    confidence="low",
    source="https://azure.microsoft.com/updates/azure-sql-database-new-performance-levels-and-storage-add-ons-in-public-preview/",
    note="Announced as public preview in the 2016 'new performance levels and storage add-ons' "
    "update; GA followed later in 2016. Exact GA month not confirmed.",
)

DTU_P15 = milestone(
    key="sqldb-dtu-p15",
    label="DTU Premium performance level P15 (4000 DTU)",
    preview="2016-02",
    ga="2016-08",
    confidence="medium",
    source="https://azure.microsoft.com/updates?id=general-availability-new-azure-sql-database-premium-performance-level-p15",
    note="Azure update: 'General availability: New Azure SQL Database Premium performance level, P15'.",
)

VCORE = milestone(
    key="sqldb-vcore",
    label="vCore purchasing model (General Purpose / Business Critical, Gen4 + Gen5)",
    preview="2017-09",
    ga="2018-04",
    confidence="low",
    source="https://azure.microsoft.com/en-us/blog/a-flexible-new-way-to-purchase-azure-sql-database/",
    note="Announced as a new purchasing option in September 2017 and generally available in "
    "the first half of 2018. The GA month is approximate.",
)

GEN5_RENAME = milestone(
    key="sqldb-gen5-rename",
    label="Gen5 hardware renamed to standard-series (Gen5)",
    preview=None,
    ga="2022",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/database/doc-changes-updates-release-notes-whats-new-archive",
    note="Naming change only. The underlying hardware configuration is unchanged.",
)

SERVERLESS = milestone(
    key="sqldb-serverless",
    label="Serverless compute tier (General Purpose, standard-series)",
    preview="2018-11",
    ga="2019-11",
    confidence="medium",
    source="https://learn.microsoft.com/azure/azure-sql/database/serverless-tier-overview",
)

HYPERSCALE = milestone(
    key="sqldb-hyperscale",
    label="Hyperscale service tier",
    preview="2018-10",
    ga="2019-05",
    confidence="medium",
    source="https://azure.microsoft.com/en-us/blog/announcing-azure-sql-database-hyperscale-public-preview/",
)

HS_SERVERLESS = milestone(
    key="sqldb-hs-serverless",
    label="Serverless compute tier for Hyperscale",
    preview="2023-02",
    ga="2024-02",
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/azuresqlblog/general-availability-serverless-for-hyperscale-in-azure-sql-database/4053589",
)

FSV2 = milestone(
    key="sqldb-fsv2",
    label="Fsv2-series hardware (General Purpose only)",
    preview="2019",
    ga="2019",
    confidence="low",
    source="https://azure.microsoft.com/updates?id=485030",
    note="RETIRING: no longer available to create; retirement date 2026-10-01. "
    "Original GA year is approximate.",
)

DC_SMALL = milestone(
    key="sqldb-dc-2-8",
    label="DC-series hardware, 2-8 vCores (Intel SGX / Always Encrypted with secure enclaves)",
    preview="2019",
    ga="2021-11",
    confidence="low",
    source="https://learn.microsoft.com/azure/azure-sql/database/service-tiers-sql-database-vcore",
    note="GA month reconstructed from the DC-series rollout; treat as approximate.",
)

DC_LARGE = milestone(
    key="sqldb-dc-10-40",
    label="DC-series hardware, 10-40 vCores",
    preview="2023-07",
    ga="2023-11",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/database/doc-changes-updates-release-notes-whats-new-archive",
)

VCORE_128 = milestone(
    key="sqldb-128-vcore",
    label="128 vCore compute size (General Purpose and Business Critical, standard-series)",
    preview="2022",
    ga="2023-06",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/database/doc-changes-updates-release-notes-whats-new-archive",
    note="Learn what's-new archive, 2023: '128 vCore GA | June'. The original announcement blog post has been removed from Tech Community.",
)

HS_PREMIUM = milestone(
    key="sqldb-hs-premium",
    label="Hyperscale premium-series and premium-series memory optimized hardware",
    preview="2022",
    ga="2023-07",
    confidence="high",
    source="https://aka.ms/AAiq28n",
)

HS_PREMIUM_64 = milestone(
    key="sqldb-hs-premium-64",
    label="64 vCore option for Hyperscale premium-series and memory optimized premium-series",
    preview=None,
    ga="2023-06",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/database/doc-changes-updates-release-notes-whats-new-archive",
)

HS_PREMIUM_XL = milestone(
    key="sqldb-hs-premium-160-192",
    label="160 and 192 vCore options for Hyperscale premium-series",
    preview="2026-03",
    ga=None,
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/azuresqlblog/announcing-preview-of-160-and-192vcore-premium-series-options-for-azure-sql-data/4501367",
    note="Preview only as of the catalog date. Available for single databases and Hyperscale elastic pools.",
)

HS_ELASTIC_POOLS = milestone(
    key="sqldb-hs-elastic-pools",
    label="Hyperscale elastic pools (incl. premium-series hardware for pools)",
    preview="2023-11",
    ga="2024-09",
    confidence="high",
    source="https://aka.ms/hsep-ga",
)

GEN4_RETIRED = milestone(
    key="sqldb-gen4",
    label="Gen4 hardware",
    preview=None,
    ga="2017",
    confidence="low",
    source="https://azure.microsoft.com/updates/support-has-ended-for-gen-4-hardware-on-azure-sql-database/",
    note="RETIRED. Cannot be provisioned, scaled up, or scaled down.",
)

# --- Azure SQL Managed Instance ------------------------------------------

MI_GA = milestone(
    key="mi-ga",
    label="Azure SQL Managed Instance GA (General Purpose and Business Critical, Gen5)",
    preview="2018-03",
    ga="2018-10-01",
    confidence="medium",
    source="https://learn.microsoft.com/azure/azure-sql/managed-instance/sql-managed-instance-paas-overview",
)

MI_PREMIUM = milestone(
    key="mi-premium-series",
    label="Managed Instance premium-series hardware (G8IM)",
    preview="2021-11",
    ga="2022-07-19",
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/azuresqlblog/announcing-the-general-availability-of-premium-series-hardware-for-azure-sql-man/3576737",
)

MI_PREMIUM_MO = milestone(
    key="mi-premium-series-mo",
    label="Managed Instance memory optimized premium-series hardware (G8IH)",
    preview="2021-11",
    ga="2022-09",
    confidence="medium",
    source="https://learn.microsoft.com/azure/azure-sql/managed-instance/doc-changes-updates-release-notes-whats-new-archive",
    note="The Learn what's-new archive places 'Memory optimized premium-series hardware GA' "
    "and '16 TB support in Business Critical GA' in 2022 without a month; contemporaneous "
    "coverage dates the announcement to 2022-09-28. The original blog post has been removed "
    "from Tech Community.",
)

MI_128_VCORE = milestone(
    key="mi-128-vcore",
    label="96 and 128 vCore sizes for Business Critical on premium-series and memory "
          "optimized premium-series",
    preview=None,
    ga="2023-07",
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/azuresqlblog/128-vcores-on-azure-sql-managed-instance-business-critical/3879510",
)

MI_MID_VCORES = milestone(
    key="mi-mid-vcores",
    label="Additional Business Critical vCore sizes (6, 10, 12, 20, 48, 56) on premium-series "
          "and memory optimized premium-series",
    preview=None,
    ga="2024-01-30",
    confidence="high",
    source="https://techcommunity.microsoft.com/blog/azuresqlblog/more-vcore-options-for-sql-mi-business-critical-for-better-priceperformance-and-/4043195",
)

MI_INSTANCE_POOLS = milestone(
    key="mi-instance-pools",
    label="Instance pools (the only way to deploy a 2-vCore managed instance)",
    preview="2019",
    ga="2024-11",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/managed-instance/doc-changes-updates-release-notes-whats-new-archive",
    note="A 2-vCore instance can only be deployed inside an instance pool, so 2-vCore SKUs "
    "became generally available when instance pools did.",
)

MI_NEXTGEN = milestone(
    key="mi-nextgen-gp",
    label="Managed Instance Next-gen General Purpose service tier",
    preview="2024-03",
    ga="2025-11",
    confidence="high",
    source="https://learn.microsoft.com/azure/azure-sql/managed-instance/doc-changes-updates-release-notes-whats-new-archive",
    note="Billed as General Purpose. An architectural upgrade (Elastic SAN storage), not a "
    "separate ARM SKU name. The Learn what's-new archive dates the preview to March 2024 and "
    "GA to November 2025; the GA blog post went up on 2025-12-02.",
)

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


# ---- Azure SQL Database, DTU purchasing model ----------------------------

SQLDB = "Azure SQL Database"

DTU_SINGLE = [
    # (name, dtu, max storage GB, milestone)
    ("Basic", 5, 2, DTU_CORE),
    ("S0", 10, 250, DTU_CORE),
    ("S1", 20, 250, DTU_CORE),
    ("S2", 50, 250, DTU_CORE),
    ("S3", 100, 1024, DTU_CORE),
    ("S4", 200, 1024, DTU_EXPANDED),
    ("S6", 400, 1024, DTU_EXPANDED),
    ("S7", 800, 1024, DTU_EXPANDED),
    ("S9", 1600, 1024, DTU_EXPANDED),
    ("S12", 3000, 1024, DTU_EXPANDED),
    ("P1", 125, 1024, DTU_CORE),
    ("P2", 250, 1024, DTU_CORE),
    ("P4", 500, 1024, DTU_P4_P11),
    ("P6", 1000, 1024, DTU_CORE),
    ("P11", 1750, 4096, DTU_P4_P11),
    ("P15", 4000, 4096, DTU_P15),
]

DTU_SINGLE_LIMITS_DOC = (
    "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-single-databases"
)
DTU_POOL_LIMITS_DOC = (
    "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-elastic-pools"
)
VCORE_SINGLE_LIMITS_DOC = (
    "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-vcore-single-databases"
)
MI_LIMITS = "https://learn.microsoft.com/azure/azure-sql/managed-instance/resource-limits"

# Memory values transcribed from the Memory (GB) rows of the Azure SQL Database
# single-database resource-limit tables, keyed by service-level objective. Using the
# published numbers rather than a per-vCore ratio matters at the top of the range:
# HS_PRMS_192 is documented at 843.7 GB, not the 996 GB a linear ratio implies, and
# standard-series caps at 625 GB from 128 vCores.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "sqldb_memory.json"), encoding="utf-8") as _fh:
    DOCUMENTED_MEMORY: dict[str, float] = json.load(_fh)


def dtu_guidance(name: str) -> str:
    if name == "Basic":
        return "dtu-basic"
    if name in ("S0", "S1", "S2"):
        return "dtu-standard-low"
    if name.startswith("S"):
        return "dtu-standard-high"
    return "dtu-premium"


for name, dtu, max_gb, ms in DTU_SINGLE:
    tier = "Basic" if name == "Basic" else ("Standard" if name.startswith("S") else "Premium")
    add(
        inventory_doc=DTU_SINGLE_LIMITS_DOC,
        guidance_key=dtu_guidance(name),
        sku=name,
        service=SQLDB,
        deployment_model="Single database",
        purchasing_model="DTU",
        service_tier=tier,
        compute_tier="Provisioned",
        hardware="n/a (DTU model)",
        capacity_unit="DTU",
        capacity=dtu,
        memory_gb=None,
        memory_gb_per_vcore=None,
        status="GA",
        milestone=ms,
        notes=f"Max storage {max_gb} GB.",
    )

DTU_POOLS = {
    "Basic": [50, 100, 200, 300, 400, 800, 1200, 1600],
    "Standard": [50, 100, 200, 300, 400, 800, 1200, 1600, 2000, 2500, 3000],
    "Premium": [125, 250, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000],
}

for tier, sizes in DTU_POOLS.items():
    for edtu in sizes:
        add(
            inventory_doc=DTU_POOL_LIMITS_DOC,
            guidance_key="dtu-pool",
            sku=f"{tier}Pool_{edtu}",
            service=SQLDB,
            deployment_model="Elastic pool",
            purchasing_model="DTU",
            service_tier=tier,
            compute_tier="Provisioned",
            hardware="n/a (DTU model)",
            capacity_unit="eDTU",
            capacity=edtu,
            memory_gb=None,
            memory_gb_per_vcore=None,
            status="GA",
            milestone=DTU_CORE,
            notes=f"{tier} elastic pool, {edtu} eDTU. ARM sku name is '{tier}Pool' with "
            f"capacity {edtu}.",
        )


# ---- Azure SQL Database, vCore purchasing model --------------------------

GEN5_RATIO = 5.1875
GEN5_CAP = 625.0
DC_RATIO = 4.5
FSV2_RATIO = 1.9
FSV2_CAP = 136.0
MOPRMS_RATIO = 10.375


def mem(vcores: int, ratio: float, cap: float | None = None) -> float:
    value = round(vcores * ratio, 1)
    if cap is not None:
        value = min(value, cap)
    return value


STD_SIZES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 32, 40, 80]
DC_SIZES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 32, 40]
FSV2_SIZES = [8, 10, 12, 14, 16, 18, 20, 24, 32, 36, 72]
PRMS_SIZES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 32, 40, 64, 80, 128, 160, 192]
MOPRMS_SIZES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 32, 40, 64, 80]

# (prefix, tier, compute tier, hardware, sizes, ratio, cap, default milestone)
VCORE_FAMILIES = [
    ("GP_Gen5", "General Purpose", "Provisioned", "Standard-series (Gen5)",
     STD_SIZES + [128], GEN5_RATIO, GEN5_CAP, VCORE),
    ("BC_Gen5", "Business Critical", "Provisioned", "Standard-series (Gen5)",
     STD_SIZES + [128], GEN5_RATIO, GEN5_CAP, VCORE),
    ("HS_Gen5", "Hyperscale", "Provisioned", "Standard-series (Gen5)",
     STD_SIZES, GEN5_RATIO, GEN5_CAP, HYPERSCALE),
    ("GP_S_Gen5", "General Purpose", "Serverless", "Standard-series (Gen5)",
     [1] + STD_SIZES, None, None, SERVERLESS),
    ("HS_S_Gen5", "Hyperscale", "Serverless", "Standard-series (Gen5)",
     STD_SIZES, None, None, HS_SERVERLESS),
    ("GP_Fsv2", "General Purpose", "Provisioned", "Fsv2-series",
     FSV2_SIZES, FSV2_RATIO, FSV2_CAP, FSV2),
    ("GP_DC", "General Purpose", "Provisioned", "DC-series",
     DC_SIZES, DC_RATIO, None, DC_SMALL),
    ("BC_DC", "Business Critical", "Provisioned", "DC-series",
     DC_SIZES, DC_RATIO, None, DC_SMALL),
    ("HS_DC", "Hyperscale", "Provisioned", "DC-series",
     DC_SIZES, DC_RATIO, None, DC_SMALL),
    ("HS_PRMS", "Hyperscale", "Provisioned", "Premium-series",
     PRMS_SIZES, GEN5_RATIO, None, HS_PREMIUM),
    ("HS_MOPRMS", "Hyperscale", "Provisioned", "Premium-series memory optimized",
     MOPRMS_SIZES, MOPRMS_RATIO, None, HS_PREMIUM),
]

VCORE_GUIDANCE = {
    "GP_Gen5": "gp-gen5",
    "BC_Gen5": "bc-gen5",
    "HS_Gen5": "hs-gen5",
    "GP_S_Gen5": "serverless-gp",
    "HS_S_Gen5": "serverless-hs",
    "GP_Fsv2": "fsv2",
    "GP_DC": "dc",
    "BC_DC": "dc",
    "HS_DC": "dc",
    "HS_PRMS": "hs-prms",
    "HS_MOPRMS": "hs-moprms",
}

for prefix, tier, compute, hardware, sizes, ratio, cap, default_ms in VCORE_FAMILIES:
    for vcores in sizes:
        ms = default_ms
        status = "GA"
        notes = ""
        guidance_key = VCORE_GUIDANCE[prefix]
        lifecycle = "Generally available"

        if prefix == "GP_Fsv2":
            lifecycle = "Deprecated - cannot be created; retires 2026-10-01"

        if prefix in ("GP_Gen5", "BC_Gen5") and vcores == 128:
            ms = VCORE_128
        elif hardware == "DC-series" and vcores >= 10:
            ms = DC_LARGE
        elif prefix in ("HS_PRMS", "HS_MOPRMS") and vcores == 64:
            ms = HS_PREMIUM_64
        elif prefix == "HS_PRMS" and vcores in (160, 192):
            ms = HS_PREMIUM_XL
            status = "Preview"
            guidance_key = "hs-prms-xl"
            lifecycle = "Public preview"

        if compute == "Serverless":
            notes = (
                "Serverless autoscales compute; memory scales with usage up to 24 GB per "
                "vCore (240 GB max). The number is the max vCore setting."
            )

        add(
            inventory_doc=VCORE_SINGLE_LIMITS_DOC,
            guidance_key=guidance_key,
            lifecycle_status=lifecycle,
            sku=f"{prefix}_{vcores}",
            service=SQLDB,
            deployment_model="Single database / Elastic pool",
            purchasing_model="vCore",
            service_tier=tier,
            compute_tier=compute,
            hardware=hardware,
            capacity_unit="vCore",
            capacity=vcores,
            memory_gb=DOCUMENTED_MEMORY.get(
                f"{prefix}_{vcores}", mem(vcores, ratio, cap) if ratio else None),
            memory_gb_per_vcore=ratio,
            status=status,
            milestone=ms,
            notes=notes,
        )


# ---- Azure SQL Managed Instance ------------------------------------------

SQLMI = "Azure SQL Managed Instance"

MI_FAMILIES = [
    # (sku prefix, tier, hardware, ARM family, GB/vCore, sizes, milestone)
    ("GP_Gen5", "General Purpose", "Standard-series (Gen5)", "Gen5", 5.1,
     [2, 4, 8, 16, 24, 32, 40, 64, 80], MI_GA),
    ("BC_Gen5", "Business Critical", "Standard-series (Gen5)", "Gen5", 5.1,
     [4, 8, 16, 24, 32, 40, 64, 80], MI_GA),
    ("GP_G8IM", "General Purpose", "Premium-series", "G8IM", 7.0,
     [2, 4, 8, 16, 24, 32, 40, 64, 80], MI_PREMIUM),
    ("BC_G8IM", "Business Critical", "Premium-series", "G8IM", 7.0,
     [4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 128], MI_PREMIUM),
    ("GP_G8IH", "General Purpose", "Premium-series memory optimized", "G8IH", 13.6,
     [4, 8, 16, 24, 32, 40, 64, 80], MI_PREMIUM_MO),
    ("BC_G8IH", "Business Critical", "Premium-series memory optimized", "G8IH", 13.6,
     [4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 128], MI_PREMIUM_MO),
]

# Next-gen General Purpose reuses the General Purpose SKU names but supports the
# wider premium-series vCore grid.
MI_NEXTGEN_FAMILIES = [
    ("GP_Gen5", "Standard-series (Gen5)", "Gen5", 5.1, [4, 8, 16, 24, 32, 40, 64, 80]),
    ("GP_G8IM", "Premium-series", "G8IM", 7.0,
     [4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 128]),
    ("GP_G8IH", "Premium-series memory optimized", "G8IH", 13.6,
     [4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 128]),
]

MI_MEM_CAP = {"Premium-series": 560.0, "Premium-series memory optimized": 870.4,
              "Standard-series (Gen5)": 408.0}

MI_HW_GUIDANCE = {
    "Standard-series (Gen5)": "mi-hw-gen5",
    "Premium-series": "mi-hw-g8im",
    "Premium-series memory optimized": "mi-hw-g8ih",
}

for prefix, tier, hardware, family, ratio, sizes, ms in MI_FAMILIES:
    for vcores in sizes:
        extra = ""
        milestone_key = ms
        if vcores == 2:
            extra = "2 vCores can only be deployed inside an instance pool. "
        if vcores == 2:
            milestone_key = MI_INSTANCE_POOLS
        elif hardware != "Standard-series (Gen5)" and vcores in (96, 128):
            milestone_key = MI_128_VCORE
        elif hardware != "Standard-series (Gen5)" and vcores in (6, 10, 12, 20, 48, 56):
            milestone_key = MI_MID_VCORES
        add(
            inventory_doc=MI_LIMITS,
            guidance_key=f"{'mi-gp' if prefix.startswith('GP') else 'mi-bc'}+"
                         f"{MI_HW_GUIDANCE[hardware]}",
            sku=f"{prefix} ({vcores} vCores)",
            service=SQLMI,
            deployment_model="Managed instance",
            purchasing_model="vCore",
            service_tier=tier,
            compute_tier="Provisioned",
            hardware=hardware,
            capacity_unit="vCore",
            capacity=vcores,
            memory_gb=mem(vcores, ratio, MI_MEM_CAP[hardware]),
            memory_gb_per_vcore=ratio,
            status="GA",
            milestone=milestone_key,
            notes=f"{extra}ARM sku name '{prefix}', family '{family}', capacity {vcores}.",
        )

for prefix, hardware, family, ratio, sizes in MI_NEXTGEN_FAMILIES:
    for vcores in sizes:
        add(
            inventory_doc=MI_LIMITS,
            guidance_key=f"mi-nextgen-gp+{MI_HW_GUIDANCE[hardware]}",
            sku=f"{prefix} ({vcores} vCores)",
            service=SQLMI,
            deployment_model="Managed instance",
            purchasing_model="vCore",
            service_tier="Next-gen General Purpose",
            compute_tier="Provisioned",
            hardware=hardware,
            capacity_unit="vCore",
            capacity=vcores,
            memory_gb=mem(vcores, ratio, MI_MEM_CAP[hardware]),
            memory_gb_per_vcore=ratio,
            status="GA",
            milestone=MI_NEXTGEN,
            notes=f"ARM sku name '{prefix}', family '{family}', capacity {vcores}. Billed as "
            "General Purpose. Supports flexible memory on premium-series.",
        )


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


def numbered(items: list[str]) -> str:
    return "<br>".join(f"{i}. {text}" for i, text in enumerate(items, 1))


def links(urls: list[str]) -> str:
    return "<br>".join(f"[{i}]({u})" for i, u in enumerate(urls, 1))


def write_sql_table(path: str) -> None:
    """The single wide Azure SQL table: every SKU, status, sources, guidance."""
    rows = [s for s in SKUS if s.service in (SQLDB, SQLMI)]

    lines = [
        "# Azure SQL — complete SKU table",
        "",
        f"Every Azure SQL Database and Azure SQL Managed Instance SKU that Microsoft "
        f"currently documents: **{len(rows)} SKUs**, catalog as of **{CATALOG_AS_OF}**.",
        "",
        "Column notes:",
        "",
        "- **Release date** — the GA date of the release that made the SKU orderable, or the "
        "preview date for SKUs still in preview. Microsoft publishes release dates per SKU "
        "*family*, not per individual size, so sizes added later than their family carry "
        "their own date (for example `GP_Gen5_128`, the DC-series 10–40 vCore sizes, and the "
        "160/192 vCore Hyperscale premium-series options).",
        "- **Confidence** — how firmly the date is sourced. `high` = a dated Microsoft "
        "announcement names this exact change; `medium` = a Microsoft page dates it to a "
        "month; `low` = reconstructed from context, treat as approximate.",
        "- **Lifecycle** — read directly from the current Microsoft docs.",
        "- **When to recommend** — paraphrased from the Microsoft pages linked in the last "
        "column. No third-party or inferred advice.",
        "",
        "| # | SKU | Deployment | Service tier | Hardware | Size | Release date | Confidence "
        "| Lifecycle status | SKU data source | Release date source | When to recommend this "
        "SKU | Recommendation source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for i, s in enumerate(rows, 1):
        size = f"{s.capacity:g} {s.capacity_unit}"
        if s.memory_gb is not None:
            size += f" / {s.memory_gb:g} GB"
        lines.append(
            f"| {i} | `{s.sku}` | {s.deployment_model} | {s.service_tier}"
            f"{'' if s.compute_tier == 'Provisioned' else ' — ' + s.compute_tier} "
            f"| {s.hardware} | {size} | {s.release_date} | {s.date_confidence} "
            f"| {s.lifecycle_status} | [docs]({s.inventory_doc}) "
            f"| [announcement]({s.release_doc}) | {numbered(s.recommend_when)} "
            f"| {links(s.recommend_sources)} |"
        )

    lines += [
        "",
        "## Documentation discrepancies found while verifying",
        "",
        "- The **DC-series** row of the *Compute resources (CPU and memory)* table on the "
        "[vCore purchasing model page]"
        "(https://learn.microsoft.com/azure/azure-sql/database/service-tiers-sql-database-vcore) "
        "still says *\"Provision up to 8 vCores (physical)\"*, but the "
        "[single-database resource limits page]"
        "(https://learn.microsoft.com/azure/azure-sql/database/resource-limits-vcore-single-databases) "
        "enumerates DC-series objectives up to 40 vCores, and the what's-new archive records "
        "the 10–40 vCore GA in November 2023. This table follows the resource-limits page.",
        "- The Azure SQL Managed Instance **Next-gen General Purpose** GA date differs by "
        "source: the [Learn what's-new archive]"
        "(https://learn.microsoft.com/azure/azure-sql/managed-instance/doc-changes-updates-release-notes-whats-new-archive) "
        "says November 2025, while the [GA blog post]"
        "(https://techcommunity.microsoft.com/blog/azuresqlblog/generally-available-azure-sql-managed-instance-next-gen-general-purpose/4470970) "
        "was published 2 December 2025. This table uses the Learn date.",
        "- Two announcement blog posts cited by older documentation have been removed from "
        "Tech Community (the Azure SQL Database 128 vCore announcement and the Managed "
        "Instance memory optimized premium-series announcement). Those dates are sourced from "
        "the Microsoft Learn what's-new archives instead.",
        "",
    ]

    lines += ["## Retired and deprecated hardware families", "",
              "Gen4 and M-series no longer appear in the Microsoft resource-limit tables at "
              "all, so their individual service-level objectives cannot be enumerated from a "
              "current Microsoft page — they are recorded at family level rather than "
              "invented as SKU rows. Fsv2-series is still fully documented and its sizes "
              "appear individually in the table above.", "",
              "| Family | Status | Retired | Detail | Source |",
              "| --- | --- | --- | --- | --- |"]
    for fam in RETIRED_FAMILIES:
        lines.append(
            f"| {fam['family']} | {fam['status']} | {fam['retired']} | {fam['detail']} "
            f"| [link]({fam['source']}) |"
        )
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> None:
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)

    write_sql_table(os.path.join(DOCS, "azure-sql-sku-table.md"))
    write_json(os.path.join(DATA, "azure-sql.json"), payload([SQLDB, SQLMI]))
    write_json(os.path.join(DATA, "azure-postgresql.json"), payload([PG]))
    write_csv(os.path.join(DATA, "skus.csv"))

    write_markdown(
        os.path.join(DOCS, "azure-sql-skus.md"),
        "Azure SQL SKU catalog",
        "Covers Azure SQL Database (DTU and vCore purchasing models, single databases and "
        "elastic pools) and Azure SQL Managed Instance.\n\n"
        "Memory values for the vCore model are derived from the per-vCore ratio published in "
        "the Microsoft resource-limit docs, with documented caps applied.",
        [SQLDB, SQLMI],
        lambda s: f"{s.service} — {s.deployment_model} — {s.purchasing_model} model — "
                  f"{s.service_tier}{'' if s.compute_tier == 'Provisioned' else ' (' + s.compute_tier + ')'}"
                  f" — {s.hardware}",
    )

    write_markdown(
        os.path.join(DOCS, "azure-postgresql-skus.md"),
        "Azure Database for PostgreSQL SKU catalog",
        "Covers Azure Database for PostgreSQL flexible server, plus the retired single "
        "server deployment model for historical reference.",
        [PG],
        lambda s: f"{s.deployment_model} — {s.service_tier} — {s.hardware}",
    )

    print(f"{len(SKUS)} SKUs written")
    for svc in (SQLDB, SQLMI, PG):
        print(f"  {svc}: {sum(1 for s in SKUS if s.service == svc)}")


if __name__ == "__main__":
    main()
