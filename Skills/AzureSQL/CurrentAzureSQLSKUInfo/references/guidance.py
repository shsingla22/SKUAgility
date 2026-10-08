"""Doc-sourced guidance for Azure SQL SKUs.

Each entry holds:
  * `when`    - numbered, plain-English conditions for recommending the SKU,
                paraphrased from the Microsoft Learn page(s) listed in `sources`
  * `sources` - the page(s) the guidance was taken from

Nothing in here is invented. Every clause traces to prose in one of the linked
pages; where a page states a hard limit (storage caps, vCore ceilings, regional
restrictions) the number is copied from that page.
"""

VCORE_DOC = "https://learn.microsoft.com/azure/azure-sql/database/service-tiers-sql-database-vcore"
DTU_DOC = "https://learn.microsoft.com/azure/azure-sql/database/service-tiers-dtu"
PURCHASING_DOC = "https://learn.microsoft.com/azure/azure-sql/database/purchasing-models"
SERVERLESS_DOC = "https://learn.microsoft.com/azure/azure-sql/database/serverless-tier-overview"
HYPERSCALE_DOC = "https://learn.microsoft.com/azure/azure-sql/database/service-tier-hyperscale"
DTU_SINGLE_LIMITS = "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-single-databases"
DTU_POOL_LIMITS = "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-elastic-pools"
VCORE_SINGLE_LIMITS = "https://learn.microsoft.com/azure/azure-sql/database/resource-limits-vcore-single-databases"
POOL_DOC = "https://learn.microsoft.com/azure/azure-sql/database/elastic-pool-overview"
MI_VCORE_DOC = "https://learn.microsoft.com/azure/azure-sql/managed-instance/service-tiers-managed-instance-vcore"
MI_LIMITS_DOC = "https://learn.microsoft.com/azure/azure-sql/managed-instance/resource-limits"
MI_NEXTGEN_DOC = "https://learn.microsoft.com/azure/azure-sql/managed-instance/service-tiers-next-gen-general-purpose-use"
FSV2_RETIREMENT = "https://azure.microsoft.com/updates?id=485030"
HS_XL_PREVIEW = "https://aka.ms/PRMS192vCores"

GUIDANCE: dict[str, dict] = {

    # ---------------- Azure SQL Database, DTU purchasing model -------------

    "dtu-basic": {
        "when": [
            "Use for development, testing, and other infrequently accessed workloads that "
            "are less sensitive to performance variability - Basic data files sit on "
            "HDD-based Standard page blob storage.",
            "Only use when the database fits in 2 GB; that is the hard storage ceiling for "
            "the Basic tier.",
            "Do not use for resource-intensive or CPU-intensive work: Basic provides less "
            "than one vCore, and Microsoft recommends S3 or greater instead.",
            "Do not use if you need more than 7 days of point-in-time restore; Basic caps "
            "backup retention at 1-7 days while Standard and Premium go to 35 days.",
            "Avoid if you need columnstore indexing or In-Memory OLTP - neither is "
            "available in Basic.",
        ],
        "sources": [DTU_DOC, DTU_SINGLE_LIMITS],
    },

    "dtu-standard-low": {
        "when": [
            "Use for development, test, and light production workloads that fit within the "
            "250 GB storage limit of S0-S2.",
            "S0 and S1 store data files on HDD-based Standard storage, so pick them only "
            "where performance variability is acceptable.",
            "Do not use for CPU-intensive workloads: S0, S1, and S2 each provide less than "
            "one vCore, and Microsoft recommends S3 or greater.",
            "Do not use as the target of a database restore - restore operations are "
            "resource-intensive and often require S3 or greater. You can scale back down "
            "afterwards.",
        ],
        "sources": [DTU_DOC, DTU_SINGLE_LIMITS],
    },

    "dtu-standard-high": {
        "when": [
            "Use for development and production workloads that need up to 1 TB of storage "
            "and up to 3000 DTU of blended compute.",
            "Choose S3 or greater whenever the workload is CPU-intensive, since S3 is the "
            "first Standard objective with a full vCore or more.",
            "Choose S3 or greater when the database is the target of a restore operation.",
            "S3 and above are the lowest Standard objectives that support columnstore "
            "indexing.",
            "Move up to Premium instead if you need In-Memory OLTP or approximately 2 ms IO "
            "latency - Standard delivers about 5 ms read and 10 ms write.",
        ],
        "sources": [DTU_DOC, DTU_SINGLE_LIMITS],
    },

    "dtu-premium": {
        "when": [
            "Use for IO-intensive production workloads: Premium delivers more than 25 IOPS "
            "per DTU versus 1-4 IOPS per DTU in Basic and Standard.",
            "Use when the workload needs low IO latency - approximately 2 ms read and write, "
            "against about 5 ms read and 10 ms write in Basic and Standard.",
            "Choose Premium when you need In-Memory OLTP, which is not available in the "
            "Basic or Standard tiers.",
            "Choose P11 or P15 when the database needs more than 1 TB of storage, up to the "
            "4 TB Premium maximum.",
            "Check region support before choosing P11 or P15 above 1 TB: storage is capped "
            "at 1 TB in China East, China North, Germany Central, and Germany Northeast.",
        ],
        "sources": [DTU_DOC, DTU_SINGLE_LIMITS],
    },

    "dtu-pool": {
        "when": [
            "Use when you have many databases with a low average resource utilization and "
            "relatively infrequent utilization spikes.",
            "Use when per-database usage is unpredictable and you want a single, predictable "
            "budget for the group rather than provisioning each database separately.",
            "Use when you want a guarantee that no single database can consume all the "
            "resources, while every database keeps a minimum reservation.",
            "Move a database out of the pool and onto a single database if it shows "
            "consistently high utilization that impacts the others.",
            "Match the pool tier to the databases: Basic pools cap at 5 eDTU and 2 GB per "
            "database, Standard pools at 3000 eDTU, Premium pools at 4000 eDTU and 100 "
            "databases per pool.",
        ],
        "sources": [DTU_DOC, DTU_POOL_LIMITS, POOL_DOC],
    },

    # ---------------- Azure SQL Database, vCore purchasing model -----------

    "gp-gen5": {
        "when": [
            "Default choice for most generic Azure SQL Database workloads that need a fully "
            "managed engine with the standard SLA.",
            "Use when storage latency between 5 ms and 10 ms is acceptable for the workload.",
            "Use for budget-oriented workloads wanting balanced compute and storage, at "
            "roughly a third the price of Business Critical for the same vCore count.",
            "Use when the database fits within 4 TB; move to Hyperscale beyond that.",
            "Standard-series (Gen5) is available in every public region worldwide, so pick "
            "it when broad regional coverage matters.",
            "Do not choose it if you need In-Memory OLTP tables or a free read-scale "
            "replica - both require Business Critical.",
        ],
        "sources": [VCORE_DOC, VCORE_SINGLE_LIMITS],
    },

    "bc-gen5": {
        "when": [
            "Use when the workload needs consistently low IO latency, about 1-2 ms on "
            "average, from locally attached SSD storage.",
            "Use when reporting, analytics, or other read-only queries can be offloaded to "
            "the free read-scale replica included in the tier.",
            "Use when you need higher resiliency and faster recovery: three secondary "
            "replicas mean a secondary is promoted immediately on failure.",
            "Use when the workload needs In-Memory OLTP, which General Purpose and "
            "Hyperscale do not offer.",
            "Use when active geo-replication must guarantee an RPO of 5 seconds and an RTO "
            "of 30 seconds.",
            "Budget for roughly 2.7 times the General Purpose price, which is what the three "
            "extra replicas cost.",
        ],
        "sources": [VCORE_DOC, VCORE_SINGLE_LIMITS],
    },

    "hs-gen5": {
        "when": [
            "Microsoft's recommended and default service tier for all new and modernizing "
            "OLTP and HTAP workloads, not only large databases.",
            "Use when the database may grow past the 4 TB ceiling of General Purpose and "
            "Business Critical - Hyperscale scales to 128 TB.",
            "Use when you want to pay only for allocated data storage rather than a "
            "provisioned maximum, with a 10 GB minimum and no charge for log storage.",
            "Use when you want to choose the number of high availability replicas from 0 to "
            "4 to trade resiliency against cost.",
            "Use when you need read scale-out through named replicas, fast scaling without "
            "waiting for data to copy, or fast restore of a large database.",
            "Do not choose it if the workload requires In-Memory OLTP tables, which "
            "Hyperscale does not support.",
            "Note that Azure Hybrid Benefit is not available for new Hyperscale databases as "
            "of December 2023.",
        ],
        "sources": [VCORE_DOC, HYPERSCALE_DOC],
    },

    "serverless-gp": {
        "when": [
            "Use for single databases with intermittent, unpredictable usage interspersed "
            "with periods of inactivity and low average compute utilization over time.",
            "Use for databases you currently rescale frequently and would rather delegate "
            "compute rescaling to the service.",
            "Use for new databases with no usage history, where compute sizing is hard or "
            "impossible to estimate before deployment.",
            "Only choose it if the workload can tolerate warm-up delay after an idle period, "
            "and the application implements connection retry logic - auto-resume "
            "connectivity errors are predictable.",
            "Do not choose it for regular, predictable usage with high average utilization; "
            "provisioned compute has a lower vCore unit price for those.",
            "Do not choose it for several intermittent databases that could instead be "
            "consolidated into an elastic pool for better price-performance.",
            "Availability constraint: serverless runs only on standard-series (Gen5), only "
            "in the vCore model, and is not offered in Business Critical.",
        ],
        "sources": [SERVERLESS_DOC, VCORE_DOC],
    },

    "serverless-hs": {
        "when": [
            "Use when you want Hyperscale's storage architecture together with automatic, "
            "per-second-billed compute autoscaling for an intermittent workload.",
            "Use for Hyperscale databases whose compute demand is unpredictable and that "
            "would otherwise be rescaled by hand.",
            "Be aware that auto-pause and auto-resume are currently supported only in "
            "General Purpose - Hyperscale serverless autoscales but does not pause to zero "
            "compute cost.",
            "Only choose it if the application implements connection retry logic.",
            "Availability constraint: standard-series (Gen5) only.",
        ],
        "sources": [SERVERLESS_DOC, HYPERSCALE_DOC],
    },

    "fsv2": {
        "when": [
            "Do not select for new deployments - Fsv2-series can no longer be created and "
            "is retired on 1 October 2026.",
            "If you are already on Fsv2-series, plan a move to Hyperscale premium-series or "
            "standard-series (Gen5), which Microsoft states give similar or better "
            "price-performance for most databases and workloads.",
            "Validate the target hardware against your own workload before migrating, as "
            "Microsoft recommends, rather than assuming parity.",
            "Historically chosen for CPU-intensive General Purpose workloads: Fsv2 sustains "
            "a 3.4 GHz all-core turbo and scales to 72 vCores.",
            "Never a fit for workloads sensitive to memory or tempdb per vCore - Fsv2 gives "
            "1.9 GB per vCore against 5.1 GB on standard-series.",
            "Only ever available in the General Purpose service tier.",
        ],
        "sources": [VCORE_DOC, FSV2_RETIREMENT],
    },

    "dc": {
        "when": [
            "Choose when you need Always Encrypted with secure enclaves backed by hardware "
            "enclaves (Intel SGX) rather than Virtualization-based Security enclaves.",
            "Choose for workloads that process sensitive data and require confidential query "
            "processing inside the enclave.",
            "Confirm your subscription qualifies: DC-series requires a paid offer type such "
            "as Pay-As-You-Go or Enterprise Agreement.",
            "Do not choose it if you need the serverless compute tier or zone redundancy - "
            "DC-series supports neither.",
            "Check regional availability first; DC-series is offered only in selected "
            "regions, unlike standard-series.",
            "Size within 2-40 vCores at 4.5 GB of memory per vCore, which is below the "
            "5.1 GB per vCore of standard-series.",
        ],
        "sources": [VCORE_DOC, VCORE_SINGLE_LIMITS],
    },

    "hs-prms": {
        "when": [
            "Choose over standard-series when you want a guarantee of running on newer CPUs; "
            "standard-series gives no such guarantee and may be placed on older hardware.",
            "Choose when a single Hyperscale database or pool needs more than the 80 vCores "
            "that standard-series tops out at - premium-series reaches 128.",
            "Cost is not a reason to avoid it: there is no price difference between "
            "premium-series and standard-series at the same vCore count.",
            "Check regional availability first - premium-series is not offered in every "
            "region, whereas standard-series is.",
            "Also available for Hyperscale elastic pools, so use it when pooled Hyperscale "
            "databases need the same CPU guarantee.",
        ],
        "sources": [VCORE_DOC, VCORE_SINGLE_LIMITS],
    },

    "hs-moprms": {
        "when": [
            "Choose when the workload needs roughly double the memory per vCore of "
            "standard-series and premium-series - about 10.4 GB per vCore instead of 5.2 GB.",
            "Choose for memory-hungry Hyperscale workloads such as large working sets or "
            "high concurrency, where cache hit rate rather than CPU is the bottleneck.",
            "Microsoft positions premium-series memory optimized as the successor to the "
            "retired M-series hardware, with more memory at a lower price.",
            "Check regional availability first - memory optimized premium-series is offered "
            "in a subset of regions.",
            "Size within 2-80 vCores; go to premium-series instead if you need more than 80.",
        ],
        "sources": [VCORE_DOC, VCORE_SINGLE_LIMITS],
    },

    "hs-prms-xl": {
        "when": [
            "Preview only - do not use for production unless you accept the Azure preview "
            "supplemental terms of use.",
            "Use when a single Hyperscale database or a Hyperscale elastic pool needs more "
            "than the 128 vCores available at general availability.",
            "Available for both single Hyperscale databases and Hyperscale elastic pools on "
            "premium-series hardware.",
        ],
        "sources": [VCORE_DOC, HS_XL_PREVIEW],
    },

    # ---------------- Azure SQL Managed Instance ---------------------------

    "mi-gp": {
        "when": [
            "Default service tier for most generic managed instance workloads that need a "
            "fully managed engine with the standard SLA.",
            "Use when storage latency of 5-10 ms is acceptable for the workload.",
            "Use when you need SQL Server instance-scoped surface area and near-100% engine "
            "compatibility rather than a single database.",
            "Use when you can stop and start the instance during idle periods to save "
            "compute and licensing cost - a General Purpose-only capability.",
            "Stay within the limits: 80 vCores, 16 TB of instance storage, and 100 user "
            "databases per instance.",
            "Do not choose it if you need In-Memory OLTP or a read-only replica; those "
            "require Business Critical.",
        ],
        "sources": [MI_VCORE_DOC, MI_LIMITS_DOC],
    },

    "mi-nextgen-gp": {
        "when": [
            "Choose when your business is budget-oriented but the performance metrics and "
            "limits of the classic General Purpose tier are insufficient - the baseline "
            "cost is the same.",
            "Choose when you need more than 100 databases on one instance; Next-gen supports "
            "up to 500.",
            "Choose when you need more than 16 TB of reserved storage; Next-gen supports up "
            "to 32 TB.",
            "Choose when you need better storage latency, IOPS, and throughput - it uses "
            "Elastic SAN instead of page blobs, giving 3-5 ms latency against 5-10 ms.",
            "Choose when you want to scale vCores, memory, storage, and IOPS independently, "
            "including flexible memory on premium-series hardware.",
            "Budget for the extras: IOPS above the free quota of 3 per GB of reserved "
            "storage, and memory above the default allocation, are billed separately.",
            "Note that In-Memory OLTP is still not supported, and there are still no "
            "read-only replicas.",
        ],
        "sources": [MI_VCORE_DOC, MI_NEXTGEN_DOC, MI_LIMITS_DOC],
    },

    "mi-bc": {
        "when": [
            "Use when the workload needs consistently low IO latency, about 1-2 ms, from "
            "locally attached SSD storage.",
            "Use when reports, analytics, or read-only queries can be redirected to the "
            "free read-scale replica included in the tier.",
            "Use when you need higher resiliency and faster recovery - one of three "
            "secondary replicas becomes the new primary immediately on failure.",
            "Use when you need In-Memory OLTP, which neither General Purpose nor Next-gen "
            "General Purpose supports.",
            "Use when advanced data corruption protection through automatic page repair "
            "matters.",
            "Use when a failover group must guarantee an RPO of 5 seconds and an RTO of "
            "30 seconds.",
            "Configure 64 or more vCores if you need compute isolation - it is only "
            "supported at that size and above.",
            "Plan capacity accordingly: one Business Critical vCore consumes four regional "
            "vCore units against your subscription quota, versus one for General Purpose.",
        ],
        "sources": [MI_VCORE_DOC, MI_LIMITS_DOC],
    },

    "mi-hw-gen5": {
        "when": [
            "Baseline managed instance hardware - choose it when 5.1 GB of memory per vCore "
            "and a ceiling of 80 vCores and 408 GB are enough.",
            "Choose it when regional coverage matters: standard-series is available in all "
            "public regions worldwide.",
            "Use an instance pool if you want a 2-vCore instance; 2 vCores cannot be "
            "deployed as a standalone instance.",
            "Move to premium-series if the workload needs more memory per vCore or more "
            "than 80 vCores.",
        ],
        "sources": [MI_VCORE_DOC, MI_LIMITS_DOC],
    },

    "mi-hw-g8im": {
        "when": [
            "Choose when you want the newer Intel 8370C (Ice Lake) 2.8 GHz processors "
            "rather than the mixed Broadwell/Skylake/Cascade Lake pool of standard-series.",
            "Choose when the workload needs 7 GB of memory per vCore instead of 5.1 GB, up "
            "to 560 GB per instance.",
            "Choose when you need more than 80 vCores - premium-series scales to 128 in "
            "Business Critical and Next-gen General Purpose.",
            "Required if you want the flexible memory feature, which lets you raise memory "
            "without adding vCores.",
            "Choose when Business Critical needs up to 16 TB of storage, available in major "
            "regions (5.5 TB elsewhere).",
            "Regional coverage is broad: premium-series is available in all public regions.",
        ],
        "sources": [MI_VCORE_DOC, MI_LIMITS_DOC],
    },

    "mi-hw-g8ih": {
        "when": [
            "Choose when the workload is memory-bound and needs 13.6 GB of memory per vCore, "
            "up to 870.4 GB per instance.",
            "Choose when In-Memory OLTP needs the largest available allocation - memory "
            "optimized premium-series gives roughly double the premium-series limit.",
            "Choose when Business Critical needs up to 16 TB of instance storage.",
            "Check regional availability first - memory optimized premium-series is "
            "restricted to a subset of regions, unlike standard-series and premium-series.",
            "Note the memory-to-vCore ratio holds only up to 64 vCores; above that, memory "
            "stays capped at 870.4 GB.",
        ],
        "sources": [MI_VCORE_DOC, MI_LIMITS_DOC],
    },
}


# Cross-cutting guidance that applies to a whole purchasing model. Prepended to
# the per-SKU list so the model-level decision is never lost.
PURCHASING_MODEL_NOTE = {
    "DTU": (
        "Purchasing model: pick DTU only if you want simple, preconfigured bundles of "
        "compute, storage, and I/O. Microsoft marks the vCore model as recommended, and "
        "Azure Hybrid Benefit, the serverless compute tier, and the Hyperscale service "
        "tier are all unavailable in the DTU model.",
        PURCHASING_DOC,
    ),
    "vCore": (
        "Purchasing model: vCore is the model Microsoft recommends. Choose it when you "
        "value flexibility, control, and transparency, want to scale compute and storage "
        "independently, or want to apply Azure Hybrid Benefit or reserved capacity "
        "pricing.",
        PURCHASING_DOC,
    ),
}


# Hardware families that no longer appear in the resource-limit tables at all, so
# their individual service-level objectives can no longer be enumerated from a
# current Microsoft page.
RETIRED_FAMILIES = [
    {
        "family": "Gen4 hardware (GP and BC)",
        "status": "Retired",
        "retired": "2020-2023",
        "detail": "Cannot be provisioned, scaled up, or scaled down. Migrate to a supported "
                  "hardware generation for wider vCore and storage scalability, accelerated "
                  "networking, and better IO performance.",
        "source": "https://azure.microsoft.com/updates/support-has-ended-for-gen-4-hardware-on-azure-sql-database/",
    },
    {
        "family": "Fsv2-series hardware (General Purpose)",
        "status": "Retired",
        "retired": "2026-10-01",
        "detail": "Retired on 1 October 2026 and removed from the resource-limits "
                  "article, so its 11 sizes (GP_Fsv2_8 to GP_Fsv2_72) can no longer be "
                  "enumerated. Microsoft directs former users to Hyperscale "
                  "premium-series or standard-series (Gen5).",
        "source": FSV2_RETIREMENT,
    },
    {
        "family": "M-series hardware (Business Critical)",
        "status": "Retired",
        "retired": "2023",
        "detail": "Removed from the Azure SQL Database hardware options. Microsoft positions "
                  "Hyperscale premium-series memory optimized as the alternative, offering "
                  "more memory at a lower price.",
        "source": "https://techcommunity.microsoft.com/blog/azuresqlblog/announcing-ga-of-new-premium-series-hardware-options-for-azure-sql-database-hype/3679091",
    },
]
