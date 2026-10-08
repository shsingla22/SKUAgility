"""Map a parsed SKU onto its release milestone, lifecycle status and guidance.

The inventory parser reads *what exists* from the resource-limit articles. This
module records *what Microsoft said about it* — which announcement made each SKU
orderable, whether it is GA / preview / deprecated today, and which block of
"when to choose" guidance applies.

Everything here is a lookup keyed on SKU attributes, so a newly parsed SKU either
matches a rule or falls through to `UNMAPPED`, which the build reports loudly
rather than guessing.
"""

from milestones import (
    DC_LARGE, DC_SMALL, DTU_CORE, DTU_EXPANDED, DTU_P4_P11, DTU_P15, FSV2,
    HS_PREMIUM, HS_PREMIUM_64, HS_PREMIUM_XL, HS_SERVERLESS, HYPERSCALE,
    MI_128_VCORE, MI_GA, MI_INSTANCE_POOLS, MI_MID_VCORES, MI_NEXTGEN,
    MI_PREMIUM, MI_PREMIUM_MO, SERVERLESS, VCORE, VCORE_128,
)

UNMAPPED = "unmapped"

GA = "Generally available"
PREVIEW = "Public preview"
# Fsv2 retired on 2026-10-01 and its section is gone from the resource-limits
# article. The rule stays so the sizes classify correctly if Microsoft ever
# republishes them (the parser treats the section as optional).
FSV2_DEPRECATED = "Retired - 2026-10-01"

INVENTORY_DOC = {
    "vcore_single": "database/resource-limits-vcore-single-databases",
    "dtu_single": "database/resource-limits-dtu-single-databases",
    "dtu_pools": "database/resource-limits-dtu-elastic-pools",
    "mi_limits": "managed-instance/resource-limits",
}

# --- Azure SQL Database, DTU -------------------------------------------------

DTU_MILESTONE = {
    "Basic": DTU_CORE, "S0": DTU_CORE, "S1": DTU_CORE, "S2": DTU_CORE, "S3": DTU_CORE,
    "S4": DTU_EXPANDED, "S6": DTU_EXPANDED, "S7": DTU_EXPANDED,
    "S9": DTU_EXPANDED, "S12": DTU_EXPANDED,
    "P1": DTU_CORE, "P2": DTU_CORE, "P6": DTU_CORE,
    "P4": DTU_P4_P11, "P11": DTU_P4_P11,
    "P15": DTU_P15,
}

DTU_GUIDANCE = {
    "Basic": "dtu-basic",
    "S0": "dtu-standard-low", "S1": "dtu-standard-low", "S2": "dtu-standard-low",
}

# --- Azure SQL Database, vCore ----------------------------------------------

VCORE_FAMILY_MILESTONE = {
    "GP_Gen5": VCORE, "BC_Gen5": VCORE,
    "HS_Gen5": HYPERSCALE,
    "GP_S_Gen5": SERVERLESS, "HS_S_Gen5": HS_SERVERLESS,
    "GP_Fsv2": FSV2,
    "GP_DC": DC_SMALL, "BC_DC": DC_SMALL, "HS_DC": DC_SMALL,
    "HS_PRMS": HS_PREMIUM, "HS_MOPRMS": HS_PREMIUM,
}

VCORE_FAMILY_GUIDANCE = {
    "GP_Gen5": "gp-gen5", "BC_Gen5": "bc-gen5", "HS_Gen5": "hs-gen5",
    "GP_S_Gen5": "serverless-gp", "HS_S_Gen5": "serverless-hs",
    "GP_Fsv2": "fsv2",
    "GP_DC": "dc", "BC_DC": "dc", "HS_DC": "dc",
    "HS_PRMS": "hs-prms", "HS_MOPRMS": "hs-moprms",
}

# --- Azure SQL Managed Instance ---------------------------------------------

MI_TIER_GUIDANCE = {
    "General Purpose": "mi-gp",
    "Next-gen General Purpose": "mi-nextgen-gp",
    "Business Critical": "mi-bc",
}
MI_HW_GUIDANCE = {
    "Standard-series (Gen5)": "mi-hw-gen5",
    "Premium-series": "mi-hw-g8im",
    "Premium-series memory optimized": "mi-hw-g8ih",
}


def family_of(sku: str) -> str:
    return sku.rsplit("_", 1)[0]


def classify(row: dict) -> dict:
    """Return {milestone, lifecycle_status, guidance_key} for one parsed SKU."""
    sku, tier, hw, cap = row["sku"], row["service_tier"], row["hardware"], row["capacity"]

    # ---- Managed Instance
    if row["service"].endswith("Managed Instance"):
        if tier == "Next-gen General Purpose":
            ms = MI_NEXTGEN
        elif cap == 2:
            ms = MI_INSTANCE_POOLS          # 2 vCores requires an instance pool
        elif hw != "Standard-series (Gen5)" and cap in (96, 128):
            ms = MI_128_VCORE
        elif hw != "Standard-series (Gen5)" and cap in (6, 10, 12, 20, 48, 56):
            ms = MI_MID_VCORES
        elif hw == "Premium-series":
            ms = MI_PREMIUM
        elif hw == "Premium-series memory optimized":
            ms = MI_PREMIUM_MO
        else:
            ms = MI_GA
        guidance = f"{MI_TIER_GUIDANCE[tier]}+{MI_HW_GUIDANCE[hw]}"
        return {"milestone": ms, "lifecycle_status": GA, "guidance_key": guidance}

    # ---- DTU
    # Both branches fall through to UNMAPPED for anything not explicitly known.
    # A new DTU tier or pool size must not inherit the September 2014 date just
    # because it happens to be in the DTU model.
    if row["purchasing_model"] == "DTU":
        if row["deployment_model"] == "Elastic pool":
            known_pool = tier in ("Basic", "Standard", "Premium")
            return {"milestone": DTU_CORE if known_pool else UNMAPPED,
                    "lifecycle_status": GA,
                    "guidance_key": "dtu-pool" if known_pool else UNMAPPED}
        if sku not in DTU_MILESTONE:
            return {"milestone": UNMAPPED, "lifecycle_status": GA,
                    "guidance_key": UNMAPPED}
        guidance = DTU_GUIDANCE.get(
            sku, "dtu-standard-high" if sku.startswith("S") else "dtu-premium")
        if sku == "Basic":
            guidance = "dtu-basic"
        return {"milestone": DTU_MILESTONE[sku], "lifecycle_status": GA,
                "guidance_key": guidance}

    # ---- Azure SQL Database vCore
    fam = family_of(sku)
    ms = VCORE_FAMILY_MILESTONE.get(fam, UNMAPPED)
    guidance = VCORE_FAMILY_GUIDANCE.get(fam, UNMAPPED)
    lifecycle = GA

    if fam in ("GP_Gen5", "BC_Gen5") and cap == 128:
        ms = VCORE_128
    elif fam in ("GP_DC", "BC_DC", "HS_DC") and cap >= 10:
        ms = DC_LARGE
    elif fam in ("HS_PRMS", "HS_MOPRMS") and cap == 64:
        ms = HS_PREMIUM_64
    if fam == "HS_PRMS" and cap in (160, 192):
        ms, guidance, lifecycle = HS_PREMIUM_XL, "hs-prms-xl", PREVIEW
    if fam == "GP_Fsv2":
        lifecycle = FSV2_DEPRECATED

    return {"milestone": ms, "lifecycle_status": lifecycle, "guidance_key": guidance}


# Hardware families Microsoft has removed from the resource-limit tables entirely.
# Their individual objectives can no longer be enumerated from a current page, so
# they are reported at family level instead of being invented as rows.
RETIRED_FAMILIES = [
    {
        "family": "Gen4 hardware (General Purpose and Business Critical)",
        "status": "Retired",
        "retired": "2020-2023",
        "detail": "Cannot be provisioned, scaled up, or scaled down. Migrate to a "
                  "supported hardware generation for wider vCore and storage "
                  "scalability, accelerated networking, and better IO performance.",
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
        "source": "https://azure.microsoft.com/updates?id=485030",
    },
    {
        "family": "M-series hardware (Business Critical)",
        "status": "Retired",
        "retired": "2023",
        "detail": "Removed from the Azure SQL Database hardware options. Microsoft "
                  "positions Hyperscale premium-series memory optimized as the "
                  "alternative, offering more memory at a lower price.",
        "source": "https://techcommunity.microsoft.com/blog/azuresqlblog/announcing-ga-of-new-premium-series-hardware-options-for-azure-sql-database-hype/3679091",
    },
]
