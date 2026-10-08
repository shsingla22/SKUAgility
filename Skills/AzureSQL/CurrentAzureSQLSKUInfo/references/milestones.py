"""Release milestones for Azure SQL SKUs.

Microsoft announces SKUs by *family*, not by individual size, so every SKU in the
catalog points at one of these milestones rather than carrying an invented date.

`ga` / `preview` are ISO dates truncated to the precision a public Microsoft source
actually supports. `confidence` records how firmly:

  high   - a dated Microsoft announcement or release note names this exact change
  medium - a Microsoft page dates the change to a month, or a reputable secondary
           source corroborates a first-party announcement
  low    - reconstructed from context; treat the date as approximate

When refreshing: check the what's-new archives for newly dated entries and raise
confidence where a better source has appeared. Never invent a month to make a `low`
entry look firmer.
"""

from dataclasses import dataclass


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
