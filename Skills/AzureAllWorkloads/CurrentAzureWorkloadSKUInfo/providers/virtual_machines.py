"""Azure Virtual Machines, at individual size level.

Azure documents VM sizes across roughly 130 series pages, one per series, each
carrying a "Sizes in series" table that names every size:

    | Size Name         | vCPUs (Qty.) | Memory (GiB) |
    | Standard_D2s_v6   | 2            | 8            |

This provider walks that structure rather than stopping at the family:

    sizes/overview.md            -> the family pages, grouped by workload type
    <type>/<x>-family.md         -> the series pages belonging to that family
    <type>/<series>-series.md    -> the sizes themselves
    lifecycle/end-of-life-sizes-list.md -> which series are End of Life

Release dates come from references/vm_milestones.py, which maps series to the
dated Microsoft announcement that made that generation generally available.
Series with no sourced announcement report "not established" rather than
inheriting a neighbouring generation's date.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import urllib.request

from common import GA, PREVIEW, Sku, sentences
from vm_milestones import milestone_for

WORKLOAD = "virtual_machines"
SERVICE = "Azure Virtual Machines"
SOURCES = ["vm_sizes"]
WANTS_CACHE = True          # this provider fetches its own page tree

RAW = ("https://raw.githubusercontent.com/MicrosoftDocs/azure-compute-docs/main"
       "/articles/virtual-machines/sizes/")
LIVE = "https://learn.microsoft.com/azure/virtual-machines/sizes/"
UA = {"User-Agent": "SKUAgility-CurrentAzureWorkloadSKUInfo"}

TYPES = {"General purpose", "Compute optimized", "Memory optimized",
         "Storage optimized", "GPU accelerated", "FPGA accelerated",
         "High performance compute"}

# Only the "Basics" table carries vCPUs and memory. The Local Storage, Remote
# Storage, Network and Accelerator tables on the same page repeat the size names
# with different columns - and sometimes in a different name form entirely
# (HBv5 lists Standard_HB368-336rs_v5 in Basics but Standard_HB368_336rsv5 in
# the storage tables). Matching every "Size Name" table would invent sizes and
# read a disk count as a vCPU count, so the header must name both a CPU column
# and a memory column. Most pages say "vCPUs (Qty.)"; the DCv3 pages say
# "Cores (Qty.)". A few pages still use the older layout, "| Size | vCPU |
# Memory: GiB | ..." (Ebdsv5/Ebsv5 was rewritten this way in 2026-09), where
# the same sizes repeat in an NVMe table and a SCSI table — collect() keeps the
# first occurrence of each size name, so that repetition is harmless.
SIZE_HEADER = re.compile(
    r"^\|\s*Size(?:\s+Name)?\s*\|[^|]*(?:vCPU|Cores)[^|]*\|[^|]*Memory", re.I)
NUM = re.compile(r"(\d[\d,]*\.?\d*)")

# Typos in Microsoft's published Basics tables, corrected explicitly and listed
# in the output rather than repeated. Keyed by the name as published.
ERRATA = {
    "Standard_L80s_v26": ("Standard_L80s_v2",
                          "a footnote digit is fused to the size name; every other "
                          "table on the page says Standard_L80s_v2"),
    "Standard_E104id_v52": ("Standard_E104id_v5",
                            "a footnote digit is fused to the size name in the Edv5 "
                            "Basics table; Microsoft's own size list says "
                            "Standard_E104id_v5"),
}
APPLIED_ERRATA: list[dict] = []


# --------------------------------------------------------------------------
# fetching the page tree
# --------------------------------------------------------------------------

def _get(path: str, cache: str, offline: bool) -> str:
    local = os.path.join(cache, "vm", path.replace("/", "__") + ".md")
    if os.path.exists(local):
        with open(local, encoding="utf-8") as fh:
            return fh.read()
    if offline:
        return ""
    try:
        req = urllib.request.Request(RAW + path + ".md", headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", "replace")
    except Exception:
        return ""
    os.makedirs(os.path.dirname(local), exist_ok=True)
    with open(local, "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


def _get_many(paths: list[str], cache: str, offline: bool) -> dict[str, str]:
    with concurrent.futures.ThreadPoolExecutor(12) as ex:
        return dict(zip(paths, ex.map(lambda p: _get(p, cache, offline), paths)))


def discover(doc, cache: str, offline: bool) -> tuple[dict, dict, dict]:
    """Return (series path -> type, family text by type, previous-gen statuses)."""
    overview = doc.raw or ""

    # Families, and the workload type each sits under, from the overview tables.
    fam_type: dict[str, str] = {}
    current = ""
    for section in doc.sections:
        heading = section.heading.strip()
        if heading in TYPES:
            current = heading
        for table in section.tables:
            if table.column("Family") < 0:
                continue
            for row in table.body:
                for m in re.findall(r"\]\(\./([a-z-]+/[a-z0-9-]+-family)\.md", overview):
                    fam_type.setdefault(m, current)
    # The table cells lose their links once normalised, so map families to types
    # directly from the raw markdown, section by section.
    fam_type = {}
    type_now = ""
    for line in overview.split("\n"):
        stripped = re.sub(r"^#+\s*", "", line).strip()
        if line.startswith("#") and stripped in TYPES:
            type_now = stripped
        for m in re.findall(r"\]\(\./([a-z-]+/[a-z0-9-]+-family)\.md", line):
            fam_type.setdefault(m, type_now)
    if not fam_type:
        raise RuntimeError("Virtual Machines: no family pages found on the sizes "
                           "overview - the page changed shape")

    fam_pages = _get_many(sorted(fam_type), cache, offline)

    # Series pages: linked from the overview and from each family page.
    series_type: dict[str, str] = {}
    for m in re.findall(r"\]\(\./([a-z-]+/[a-z0-9_-]+-series)\.md", overview):
        series_type.setdefault(m, "")
    for fam, text in fam_pages.items():
        folder = fam.split("/")[0]
        for m in re.findall(r"\]\(\./([a-z0-9_-]+-series)\.md", text):
            series_type[f"{folder}/{m}"] = fam_type.get(fam, "")
    # Microsoft's navigation is not complete: the overview names some series in
    # a family row's text without linking them (Ddsv6, Edsv6), and some series
    # pages are linked from nowhere in the sizes tree (the v4 E-series, M-series).
    # Two supplements, both conservative: names in the overview's text are probed
    # and silently skipped if no page exists, while references/vm_extra_series.json
    # lists pages confirmed to exist, which must still be readable or the build
    # fails (the cue to remove a retired entry).
    for line in overview.split("\n"):
        if "-family.md" not in line:
            continue
        folders = re.findall(r"\]\(\./([a-z-]+)/[a-z0-9-]+-family\.md", line)
        if not folders:
            continue
        for name in re.findall(r"\b([A-Z][A-Za-z]{0,7}v\d)\b", line):
            cand = f"{folders[0]}/{name.lower()}-series"
            if cand not in series_type and _get(cand, cache, offline).strip():
                series_type[cand] = ""
    extra_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "references", "vm_extra_series.json")
    if os.path.exists(extra_path):
        with open(extra_path, encoding="utf-8") as fh:
            for e in json.load(fh)["series"]:
                series_type.setdefault(e["path"], "")
    for path in list(series_type):
        if not series_type[path]:
            folder = path.split("/")[0]
            match = [t for f, t in fam_type.items() if f.startswith(folder + "/")]
            series_type[path] = match[0] if match else "Other"

    # Family-level workload prose, for the guidance column.
    workloads: dict[str, list[str]] = {}
    inc_paths = []
    for fam in fam_type:
        folder, name = fam.split("/")
        inc_paths.append(f"{folder}/includes/{name}-workloads")
    for path, text in _get_many(inc_paths, cache, offline).items():
        body = re.sub(r"^---.*?---", "", text, flags=re.S)
        body = re.sub(r"[#*\[\]]|\(\.\..*?\)", " ", body)
        fam = path.split("/")[0] + "/" + path.split("/")[-1].replace("-workloads", "")
        workloads[fam] = sentences(body, limit=5)

    prev = end_of_life(_get("lifecycle/end-of-life-sizes-list", cache, offline))
    return series_type, {"fam_type": fam_type, "workloads": workloads}, prev


END_OF_LIFE = "End of Life - retirement announced"


def end_of_life(text: str) -> dict[str, str]:
    """Series key -> lifecycle status, from Microsoft's End of Life size-series list.

    The list replaced the older previous-generation page in 2026-09 (the old URL
    redirects here). It names whole series — "Dv2 and Dsv2-series", "Fsv2-series"
    — each with a modernization-guide link, and no per-series sub-status, so every
    listed series carries the one END_OF_LIFE status. Entries that name only some
    sizes of a series ("Msv2 and Mdsv2 isolated sizes") are skipped rather than
    applied to the whole series.

    An empty or unparseable page raises: the previous silent failure mode was
    every End of Life series quietly turning back into "Generally available".
    """
    if not text.strip():
        raise RuntimeError("Virtual Machines: the End of Life size-series list could "
                           "not be read (lifecycle/end-of-life-sizes-list) — refusing "
                           "to mark every series as generally available")
    out: dict[str, str] = {}
    for line in text.split("\n"):
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set("".join(cells)) <= set("-: "):
            continue
        name = cells[0]
        if not name or name.lower().startswith("series") or "isolated sizes" in name.lower():
            continue
        for part in re.split(r"\s+and\s+", name):
            key = re.sub(r"\s*\(.*?\)|-series$|^standard\s+|^memory-optimized\s+", "",
                         part.strip(), flags=re.I)
            key = key.lower().replace(" ", "")
            if key:
                out[key] = END_OF_LIFE
    if len(out) < 10:
        raise RuntimeError(f"Virtual Machines: only {len(out)} series parsed from the "
                           "End of Life list — the page changed shape")
    return out


def end_of_life_status(series_key: str, eol: dict[str, str]) -> str | None:
    """A series page may cover two series ("ev3-esv3"); match either half."""
    if series_key in eol:
        return eol[series_key]
    for part in series_key.split("-"):
        if part in eol:
            return eol[part]
    return None


# --------------------------------------------------------------------------
# parsing sizes
# --------------------------------------------------------------------------

def parse_sizes(text: str) -> list[tuple[str, float | None, float | None]]:
    rows, in_table = [], False
    for line in text.split("\n"):
        if SIZE_HEADER.match(line):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        # Basics rows sometimes carry a footnote marker or emphasis on the name,
        # e.g. "*Standard_D192lds_v7" or "**Standard_M8-2ms**". Strip those or the
        # size is silently dropped from the catalog.
        name = cells[0].strip().lstrip("*").strip().strip("*").strip()
        name = re.sub(r"^\\|<sup>.*?</sup>|\s+$", "", name).strip()
        if not name.startswith("Standard_"):
            continue
        def num(i):
            if len(cells) <= i:
                return None
            m = NUM.search(cells[i])
            return float(m.group(1).replace(",", "")) if m else None
        rows.append((name, num(1), num(2)))
    return rows


def series_label(path: str) -> str:
    name = path.split("/")[-1].replace("-series", "")
    return name[0].upper() + name[1:] + "-series"


def collect(docs: dict, cache: str = "", offline: bool = False) -> list[Sku]:
    doc = docs["vm_sizes"]
    cache = cache or "."
    series_type, meta, prev = discover(doc, cache, offline)

    pages = _get_many(sorted(series_type), cache, offline)

    # Each series has a summary include describing what it is for. Using it makes
    # the guidance specific to the series rather than only to its family, and
    # covers series whose name does not match any family in their folder
    # (Dnsv6 and Dnlsv6 are named "D" but documented under memory-optimized).
    summary_paths = []
    for path in series_type:
        folder, name = path.split("/")
        summary_paths.append(f"{folder}/includes/{name}-summary")
    summaries: dict[str, list[str]] = {}
    for path, text in _get_many(summary_paths, cache, offline).items():
        body = re.sub(r"^---.*?---", "", text, flags=re.S)
        body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
        body = re.sub(r"[#*>`]|\(\.\..*?\)", " ", body)
        folder = path.split("/")[0]
        series_key = f"{folder}/{path.split('/')[-1].replace('-summary', '')}"
        summaries[series_key] = sentences(body, limit=4)
    missing = [p for p, t in pages.items() if not t.strip()]
    if missing:
        raise RuntimeError(
            f"Virtual Machines: {len(missing)} series pages could not be read "
            f"(e.g. {missing[0]}). Refusing to ship a partial VM inventory.")

    fam_type, workloads = meta["fam_type"], meta["workloads"]

    rows: list[Sku] = []
    seen: set[str] = set()
    APPLIED_ERRATA.clear()
    for path, text in pages.items():
        vm_type = series_type[path] or "Other"
        series = series_label(path)
        folder = path.split("/")[0]
        fam_letter = re.match(r"([a-z]+?)(?:l|a|p)?[sdm]*v?\d*$",
                              path.split("/")[-1].replace("-series", ""))
        family_key = None
        for fam in fam_type:
            if fam.startswith(folder + "/"):
                letter = fam.split("/")[1].replace("-family", "")
                if series.lower().startswith(letter):
                    if family_key is None or len(letter) > len(
                            family_key.split("/")[1].replace("-family", "")):
                        family_key = fam
        guidance = list(summaries.get(path, []))
        if family_key:
            guidance += [g for g in workloads.get(family_key, []) if g not in guidance]

        key = series.lower().replace("-series", "")
        status = end_of_life_status(key, prev)
        lifecycle = status or GA

        ms = milestone_for(series)
        sizes = parse_sizes(text)
        if not sizes:
            raise RuntimeError(f"Virtual Machines: no sizes parsed from {path}")

        for name, vcpus, memory in sizes:
            if name in ERRATA:
                fixed, why = ERRATA[name]
                APPLIED_ERRATA.append({"workload": WORKLOAD, "published": name,
                                       "corrected": fixed, "reason": why,
                                       "source": LIVE + path})
                name = fixed
            if name in seen:
                continue
            seen.add(name)
            when = list(guidance)
            when.insert(0, f"This size belongs to the {series}, a "
                           f"{vm_type.lower()} series.")
            if status:
                when.append("Microsoft lists this series as End of Life: it has an "
                            "announced retirement date and deployment restrictions "
                            "for new subscriptions. Use a Current series for new "
                            "deployments and plan the move with its modernization "
                            "guide.")
            when.append("Confirm the size is offered in your target region and that "
                        "your subscription has vCPU quota for its family.")
            rows.append(Sku(
                workload=WORKLOAD, service=SERVICE, sku=name,
                tier=vm_type, series=series,
                capacity=vcpus, capacity_unit="vCPU", memory_gb=memory,
                lifecycle_status=lifecycle, milestone=ms,
                inventory_doc=LIVE + path,
                recommend_when=when,
                recommend_sources=[LIVE + path, doc.url],
            ).resolve())

    thin = [r.sku for r in rows if len(r.recommend_when) < 3]
    if thin:
        raise RuntimeError(
            f"Virtual Machines: {len(thin)} sizes have no documentation-sourced "
            f"guidance (e.g. {thin[0]}). Every size must carry the reasoning from "
            "its own series or family page.")

    if len(rows) < 500:
        raise RuntimeError(f"Virtual Machines: only {len(rows)} sizes parsed, "
                           "expected many more - the series pages changed shape")
    return rows
