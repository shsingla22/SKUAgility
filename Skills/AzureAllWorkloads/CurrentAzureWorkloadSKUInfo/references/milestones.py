"""Release milestones across Azure workloads.

Azure announces SKUs by family or tier, not by individual size, so every SKU
points at one of these rather than carrying an invented date.

`confidence` grades how firmly the date is sourced:

  high    - a dated Microsoft announcement or release note names this change
  medium  - a Microsoft page dates it to a month, or a reputable secondary
            source corroborates a first-party announcement
  low     - reconstructed from context; treat as approximate
  unknown - NOT ESTABLISHED. No date could be sourced. These ship with
            release_date "not established" rather than a guess, and verify.py
            counts them so the gap stays visible.

Adding a workload means adding milestones here and a provider that references
them. Never invent a month to make an `unknown` entry look firmer.
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
    retirement: str | None = None


MILESTONES: dict[str, Milestone] = {}


def milestone(**kwargs) -> str:
    m = Milestone(**kwargs)
    MILESTONES[m.key] = m
    return m.key


NOT_ESTABLISHED = "not established"


def release_date_for(key: str, lifecycle: str) -> tuple[str, str]:
    """(date, confidence) for a milestone, honouring preview status."""
    m = MILESTONES[key]
    if m.confidence == "unknown":
        return NOT_ESTABLISHED, "unknown"
    if "preview" in lifecycle.lower() and m.preview:
        return m.preview, m.confidence
    return (m.ga or m.preview or NOT_ESTABLISHED), m.confidence


# --------------------------------------------------------------------------
# Azure Database for PostgreSQL
# --------------------------------------------------------------------------

PG_FLEX = milestone(
    key="pg-flexible-server",
    label="Azure Database for PostgreSQL flexible server",
    preview="2020-11", ga="2021-11", confidence="high",
    source="https://azure.microsoft.com/updates?id=general-availability-azure-database-for-postgresql-flexible-server",
)
PG_V3 = milestone(
    key="pg-v3", label="PostgreSQL v3 compute series (Dsv3, Esv3)",
    preview="2020-11", ga="2021-11", confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/release-notes/release-notes",
    note="v3 was the launch compute series for flexible server and reached GA with it.",
)
PG_V4 = milestone(
    key="pg-v4", label="PostgreSQL v4 compute series (Ddsv4, Edsv4)",
    preview=None, ga="2021-10", confidence="high",
    source="https://techcommunity.microsoft.com/blog/adforpostgresql/flexible-server-now-supports-v4-compute-series-in-postgresql-on-azure/2815092",
)
PG_BURST_SMALL = milestone(
    key="pg-burstable-small", label="PostgreSQL Burstable B1ms / B2s / B2ms",
    preview="2020-11", ga="2021-11", confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
    note="The original burstable sizes; GA with flexible server.",
)
PG_BURST_LARGE = milestone(
    key="pg-burstable-large", label="PostgreSQL Burstable B4ms - B20ms",
    preview=None, ga="2023-04", confidence="high",
    source="https://azure.microsoft.com/updates/generally-available-new-burstable-skus-for-azure-database-for-postgresql-flexible-server/",
)
PG_V5_INTEL = milestone(
    key="pg-v5-intel", label="PostgreSQL Intel v5 compute series (Ddsv5, Edsv5)",
    preview=None, ga="2023-05", confidence="high",
    source="https://techcommunity.microsoft.com/t5/azure-database-for-postgresql/introducing-intel-v5-compute-and-32-tb-storage-support-on-azure/ba-p/3839849",
    note="Announced 2023-06-05 covering the May 2023 release.",
)
PG_V5_AMD = milestone(
    key="pg-v5-amd", label="PostgreSQL AMD v5 compute series (Dadsv5, Eadsv5)",
    preview=None, ga="2023", confidence="low",
    source="https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute",
    note="Rolled out during 2023 after the Intel v5 series. Exact GA month not confirmed.",
)
PG_V6 = milestone(
    key="pg-v6", label="PostgreSQL v6 compute series (Ddsv6, Dadsv6, Edsv6, Eadsv6)",
    preview="2025", ga=None, confidence="medium",
    source="https://learn.microsoft.com/azure/postgresql/flexible-server/overview",
    note="PUBLIC PREVIEW. Scaling between Burstable and v6 is not supported, and "
         "virtual network integration is not supported on v6.",
)

# --------------------------------------------------------------------------
# Azure Database for MySQL
# --------------------------------------------------------------------------

MYSQL_FLEX = milestone(
    key="mysql-flexible-server", label="Azure Database for MySQL flexible server",
    preview="2020-09", ga="2021-12", confidence="high",
    source="https://techcommunity.microsoft.com/t5/azure-database-for-mysql-blog/announcing-azure-database-for-mysql-flexible-server-for-business/ba-p/3361718",
    note="General availability announced November 2021, effective 1 December 2021.",
)
MYSQL_BUSINESS_CRITICAL = milestone(
    key="mysql-business-critical",
    label="MySQL Business Critical tier (the renamed Memory Optimized tier)",
    preview=None, ga="2022-05", confidence="medium",
    source="https://techcommunity.microsoft.com/blog/adformysql/leverage-flexible-server%E2%80%99s-business-critical-service-tier-for-mission-critical-a/3709525",
    note="The Memory Optimized tier was enhanced and renamed Business Critical; the "
         "80 and 96 vCore sizes became generally available at the same time.",
)

# --------------------------------------------------------------------------
# Azure Cache for Redis  — every tier is on a retirement path
# --------------------------------------------------------------------------

REDIS_OSS = milestone(
    key="redis-oss-tiers", label="Azure Cache for Redis Basic / Standard / Premium tiers",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/azure-cache-for-redis/cache-whats-new",
    note="Original GA predates the dated release history on the what's-new page, so no "
         "first-party date could be sourced. RETIRING 2028-09-30; new customers were "
         "blocked from creating caches on 2026-04-01.",
    retirement="2028-09-30",
)
REDIS_ENTERPRISE = milestone(
    key="redis-enterprise", label="Azure Cache for Redis Enterprise and Enterprise Flash tiers",
    preview="2020-10", ga="2021-03", confidence="medium",
    source="https://learn.microsoft.com/azure/azure-cache-for-redis/cache-whats-new",
    note="Announced generally available at Microsoft Ignite on 2021-03-02. "
         "RETIRING 2027-03-31; creation blocked from 2026-04-01.",
    retirement="2027-03-31",
)

# --------------------------------------------------------------------------
# Azure App Service plans
# --------------------------------------------------------------------------

APPSVC_BASE = milestone(
    key="appsvc-base", label="App Service shared and dedicated tiers (Free, Shared, Basic, Standard, Premium)",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/app-service/overview-hosting-plans",
    note="These tiers predate the dated announcement record that is still published; "
         "no first-party GA date could be sourced.",
)
APPSVC_PV2 = milestone(
    key="appsvc-pv2", label="App Service PremiumV2 plan",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/app-service/overview-hosting-plans",
    note="No dated first-party announcement located during this refresh.",
)
APPSVC_PV3 = milestone(
    key="appsvc-pv3", label="App Service PremiumV3 plan",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/app-service/overview-hosting-plans",
    note="No dated first-party announcement located during this refresh.",
)
APPSVC_PV4 = milestone(
    key="appsvc-pv4", label="App Service PremiumV4 plan",
    preview="2025-05", ga="2025-09-01", confidence="high",
    source="https://techcommunity.microsoft.com/blog/appsonazureblog/announcing-general-availability-of-premium-v4-for-azure-app-service/4446204",
    note="Runs on AMD Dadsv6 / Eadsv6 virtual machines with NVMe temporary storage.",
)
APPSVC_ISOLATED = milestone(
    key="appsvc-isolatedv2", label="App Service IsolatedV2 plan (App Service Environment v3)",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/app-service/overview-hosting-plans",
    note="No dated first-party announcement located during this refresh.",
)

# --------------------------------------------------------------------------
# Azure Kubernetes Service
# --------------------------------------------------------------------------

AKS_TIERS = milestone(
    key="aks-free-standard", label="AKS Free and Standard pricing tiers",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/aks/free-standard-pricing-tiers",
    note="The Standard tier replaced the earlier paid Uptime SLA option; no dated "
         "first-party GA announcement located during this refresh.",
)
AKS_PREMIUM = milestone(
    key="aks-premium", label="AKS Premium pricing tier (with Long Term Support)",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/aks/free-standard-pricing-tiers",
    note="24-month Long Term Support across every supported Kubernetes version was "
         "announced 2025-07-25, but that is an LTS scope change rather than the "
         "Premium tier's own GA date, which could not be sourced.",
)

# --------------------------------------------------------------------------
# Azure Virtual Machines — recorded at family level
# --------------------------------------------------------------------------

VM_FAMILY = milestone(
    key="vm-family", label="Azure Virtual Machine size family",
    preview=None, ga=None, confidence="unknown",
    source="https://learn.microsoft.com/azure/virtual-machines/sizes/overview",
    note="A VM family spans many series introduced over many years, so a single "
         "release date is not meaningful at family level. Individual series carry "
         "their own dates on their series pages.",
)
