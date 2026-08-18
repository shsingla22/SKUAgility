"""Release milestones for Azure Virtual Machine size series.

Azure announces VM sizes per *series generation*, usually several series at once
in a single dated post ("Announcing General Availability of Azure Dl/D/E v6 VMs
..."). Every size on a series page inherits that series' milestone.

Each entry maps a set of series-name prefixes to a dated announcement. Prefixes
are matched case-insensitively against the series name taken from the
documentation page (for example "Dsv6-series" -> prefix "dsv6").

Series with no entry here get `vm-series-undated`: their release date reads
"not established" rather than carrying a guess. Sourcing more of them is
straightforward - find the "Announcing ... generally available" post for the
generation and add a block below.
"""

VM_RELEASES = [
    {
        "key": "vm-v7-intel",
        "label": "Azure v7 VM series on Intel Xeon 6 (Granite Rapids)",
        "prefixes": ["dlsv7", "dldsv7", "dsv7", "ddsv7", "esv7", "edsv7"],
        "preview": "2025-11",
        "ga": "2026-05-07",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azurecompute/announcing-general-availability-of-azure-dldesv7-series-vms-based-on-intel%C2%AE-xeon/4516907",
        "note": "The 248 and 372 vCPU sizes were still rolling out at GA.",
    },
    {
        "key": "vm-v7-amd",
        "label": "Azure v7 VM series on AMD EPYC 5th Gen (Turin)",
        "prefixes": ["dasv7", "dadsv7", "dalsv7", "daldsv7", "easv7", "eadsv7",
                     "fasv7", "fadsv7", "falsv7", "faldsv7", "famsv7", "famdsv7"],
        "preview": None,
        "ga": "2026-01-27",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azurecompute/announcing-general-availability-of-azure-daeafasv7-series-vms-based-on-amd-%E2%80%98turi/4488627",
    },
    {
        "key": "vm-v6-intel",
        "label": "Azure v6 VM series on 5th Gen Intel Xeon (Emerald Rapids) with Azure Boost",
        "prefixes": ["dlsv6", "dldsv6", "dsv6", "ddsv6", "esv6", "edsv6"],
        "preview": "2024-08",
        "ga": "2025-02-10",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azurecompute/announcing-general-availability-of-azure-dlde-v6-vms-powered-by-intel-emr-proces/4376186",
        "note": "The largest sizes arrived later: E128 and E192 on 2025-08-01, "
                "D192 on 2025-09-08.",
    },
    {
        "key": "vm-v6-amd",
        "label": "Azure v6 VM series on 4th Gen AMD EPYC (Genoa) with Azure Boost",
        "prefixes": ["dalsv6", "daldsv6", "dasv6", "dadsv6", "easv6", "eadsv6",
                     "falsv6", "fasv6", "famsv6", "fadsv6", "faldsv6", "famdsv6"],
        "preview": "2023-11",
        "ga": "2024-12-10",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azurecompute/new-daeafav6-vms-with-increased-performance-and-azure-boost-are-now-generally-av/4309381",
    },
    {
        "key": "vm-v6-cobalt",
        "label": "Azure Cobalt 100 Arm-based v6 VM series",
        "prefixes": ["dpsv6", "dpdsv6", "dplsv6", "dpldsv6", "epsv6", "epdsv6"],
        "preview": "2024-05",
        "ga": "2024-10-16",
        "confidence": "high",
        "source": "https://azure.microsoft.com/en-us/blog/azure-cobalt-100-based-virtual-machines-are-now-generally-available/",
        "note": "Microsoft's first in-house 64-bit Arm CPU.",
    },
    {
        "key": "vm-b-v2",
        "label": "Azure burstable v2 VM series (Bsv2, Basv2, Bpsv2)",
        "prefixes": ["bsv2", "basv2", "bpsv2"],
        "preview": "2023-07",
        "ga": "2023-09-12",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azurecompute/announcing-the-general-availability-of-new-azure-burstable-virtual-machines/3924532",
        "note": "Intel Xeon Platinum 8370C, AMD EPYC 7763v and Ampere Altra Arm "
                "variants announced together.",
    },
    {
        "key": "vm-dc-v6-amd",
        "label": "Azure DCasv6 and ECasv6 confidential VMs on 4th Gen AMD EPYC (SEV-SNP)",
        "prefixes": ["dcasv6", "dcadsv6", "ecasv6", "ecadsv6"],
        "preview": None,
        "ga": "2025-09",
        "confidence": "high",
        "source": "https://techcommunity.microsoft.com/blog/azureconfidentialcomputingblog/ga-dcasv6-and-ecasv6-confidential-vms-based-on-4th-generation-amd-epyc%E2%84%A2-processo/4451460",
    },
    {
        "key": "vm-dc-v5-amd",
        "label": "Azure DCasv5 and ECasv5 confidential VMs on 3rd Gen AMD EPYC (SEV-SNP)",
        "prefixes": ["dcasv5", "dcadsv5", "ecasv5", "ecadsv5"],
        "preview": None,
        "ga": "2023",
        "confidence": "low",
        "source": "https://techcommunity.microsoft.com/blog/azureconfidentialcomputingblog/azure-confidential-vms-dcasv5ecasv5-using-amd-sev-snp-processors-are-now-general/2993530",
        "note": "Sources disagree on the month of general availability, so only the "
                "year is recorded here.",
    },
    {
        "key": "vm-v5-amd",
        "label": "Azure v5 VM series on 3rd Gen AMD EPYC (Milan)",
        "prefixes": ["dasv5", "dadsv5", "dalsv5", "daldsv5", "easv5", "eadsv5"],
        "preview": None,
        "ga": "2021-11-02",
        "confidence": "medium",
        "source": "https://azure.microsoft.com/en-us/blog/upgrade-your-infrastructure-with-the-latest-dv5ev5-azure-vms-in-preview/",
        "note": "Announced generally available alongside the Dv5/Ev5 line on "
                "2021-11-02; the day is from the announcement, not a Learn page.",
    },
    {
        "key": "vm-v5-intel",
        "label": "Azure v5 VM series on 3rd Gen Intel Xeon (Ice Lake)",
        "prefixes": ["dsv5", "ddsv5", "dlsv5", "dldsv5", "esv5", "edsv5",
                     "dv5", "ddv5", "ev5", "edv5"],
        "preview": "2021-04",
        "ga": "2022",
        "confidence": "low",
        "source": "https://azure.microsoft.com/en-us/blog/upgrade-your-infrastructure-with-the-latest-dv5ev5-azure-vms-in-preview/",
        "note": "Preview announced April 2021; general availability followed during "
                "2022 but no dated first-party GA post could be located, so the "
                "year is approximate.",
    },
    {
        "key": "vm-v4",
        "label": "Azure v4 VM series (Intel Cascade Lake and AMD EPYC Rome)",
        "prefixes": ["dsv4", "ddsv4", "dv4", "ddv4", "esv4", "edsv4", "ev4", "edv4",
                     "dasv4", "dadsv4", "easv4", "eadsv4", "dav4", "eav4"],
        "preview": None,
        "ga": "2020",
        "confidence": "low",
        "source": "https://azure.microsoft.com/en-us/blog/new-general-purpose-and-memoryoptimized-azure-virtual-machines-with-intel-now-available/",
        "note": "The Intel Dv4/Ev4 line was announced available in June 2020 and the "
                "AMD Dav4/Eav4 line earlier the same year. Month-level dates per "
                "series could not be sourced, so the year is approximate.",
    },
]

UNDATED = {
    "key": "vm-series-undated",
    "label": "Azure VM size series with no sourced release announcement",
    "prefixes": [],
    "preview": None,
    "ga": None,
    "confidence": "unknown",
    "source": "https://learn.microsoft.com/azure/virtual-machines/sizes/overview",
    "note": "No dated Microsoft announcement was located for this series during "
            "the last refresh. The size list itself comes from the series' own "
            "documentation page and is current; only the release date is missing.",
}


def milestone_for(series: str) -> str:
    """Longest-prefix match so 'ddsv6' beats 'dsv6' and 'dalsv6' beats 'dasv6'."""
    name = series.lower().replace("-series", "").replace("_", "")
    best, best_len = UNDATED["key"], -1
    for entry in VM_RELEASES:
        for prefix in entry["prefixes"]:
            if name == prefix and len(prefix) > best_len:
                best, best_len = entry["key"], len(prefix)
    return best


ALL = VM_RELEASES + [UNDATED]
