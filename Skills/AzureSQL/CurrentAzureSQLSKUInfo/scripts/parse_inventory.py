#!/usr/bin/env python3
"""Parse the Azure SQL SKU inventory out of the cached Learn article sources.

Emits a single inventory JSON describing every SKU Microsoft currently
documents, with the values transcribed from the published tables — never
derived from a ratio, because the published numbers are not linear at the top
of the range (HS_PRMS_192 is 843.7 GB, and standard-series caps at 625 GB).

    python3 scripts/parse_inventory.py [--cache DIR] [--out FILE]

Every extraction is anchored on structure the articles guarantee:
  * vCore SLO names come from the "The following table covers these SLOs:"
    sentences, which name each objective in backticks.
  * Memory comes from the "| Memory (GB) |" row aligned to the "| vCores |"
    header of the same table.
  * DTU sizes come from the "| **Compute size** |" / "| Max DTUs |" pairs.
  * Elastic pool sizes come from the "| eDTUs per pool |" header rows.
  * Managed Instance sizes come from the "Number of vCores" grid.

If Microsoft restructures a page, the relevant parser raises instead of
silently returning less — a short inventory is worse than a loud failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SLO_RE = re.compile(r"`((?:GP|BC|HS)_(?:S_)?(?:Gen5|Fsv2|DC|PRMS|MOPRMS)_\d+)`")
SUP_RE = re.compile(r"<sup>.*?</sup>|\^\d+\^|<br\s*/?>")

# vCore section heading -> (service tier, compute tier, hardware, SLO prefix)
VCORE_SECTIONS = [
    ("General Purpose - serverless compute - standard-series (Gen5)",
     "General Purpose", "Serverless", "Standard-series (Gen5)", "GP_S_Gen5"),
    ("Hyperscale - serverless compute - standard-series (Gen5)",
     "Hyperscale", "Serverless", "Standard-series (Gen5)", "HS_S_Gen5"),
    ("Hyperscale - provisioned compute - premium-series memory optimized",
     "Hyperscale", "Provisioned", "Premium-series memory optimized", "HS_MOPRMS"),
    ("Hyperscale - provisioned compute - premium-series",
     "Hyperscale", "Provisioned", "Premium-series", "HS_PRMS"),
    ("Hyperscale - provisioned compute - standard-series (Gen5)",
     "Hyperscale", "Provisioned", "Standard-series (Gen5)", "HS_Gen5"),
    ("Hyperscale - provisioned compute - DC-series",
     "Hyperscale", "Provisioned", "DC-series", "HS_DC"),
    ("General Purpose - provisioned compute - standard-series (Gen5)",
     "General Purpose", "Provisioned", "Standard-series (Gen5)", "GP_Gen5"),
    ("General Purpose - provisioned compute - Fsv2-series",
     "General Purpose", "Provisioned", "Fsv2-series", "GP_Fsv2"),
    ("General Purpose - provisioned compute - DC-series",
     "General Purpose", "Provisioned", "DC-series", "GP_DC"),
    ("Business Critical - provisioned compute - standard-series (Gen5)",
     "Business Critical", "Provisioned", "Standard-series (Gen5)", "BC_Gen5"),
    ("Business Critical - provisioned compute - DC-series",
     "Business Critical", "Provisioned", "DC-series", "BC_DC"),
]


def clean(cell: str) -> str:
    return SUP_RE.sub("", cell).replace("**", "").replace("`", "").strip()


def cells(line: str) -> list[str]:
    return [clean(c) for c in line.strip().strip("|").split("|")]


def heading_text(line: str) -> str:
    """Strip the leading #s and any <a id=...></a> anchor Learn injects."""
    text = re.sub(r"^#+\s*", "", line)
    text = re.sub(r'<a id="[^"]*"></a>', "", text)
    return text.strip()


def read(cache: str, key: str) -> list[str]:
    path = os.path.join(cache, key + ".md")
    if not os.path.exists(path):
        raise SystemExit(f"missing cached page '{key}' — run scripts/fetch_docs.py first")
    with open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


# --------------------------------------------------------------------------
# Azure SQL Database, vCore purchasing model
# --------------------------------------------------------------------------

def parse_vcore(lines: list[str]) -> list[dict]:
    """Walk the ## sections, collecting SLO names and their Memory (GB) values."""
    section = None
    memory: dict[str, float] = {}
    slos: dict[str, set[str]] = {}

    for i, line in enumerate(lines):
        if line.startswith("## "):
            title = heading_text(line)
            section = None
            for name, tier, compute, hardware, prefix in VCORE_SECTIONS:
                if title == name:
                    section = (tier, compute, hardware, prefix)
                    slos.setdefault(prefix, set())
                    break
            continue
        if section is None:
            continue

        prefix = section[3]

        # SLO names are stated verbatim in the "covers these SLOs" sentences.
        if "SLOs:" in line or "SLOs :" in line:
            for name in SLO_RE.findall(line):
                if name.rsplit("_", 1)[0] == prefix:
                    slos[prefix].add(name)

        # Memory row, aligned to the vCores header directly above it.
        if line.startswith("| vCores |") or line.startswith("| Min-max vCores |"):
            header = cells(line)[1:]
            for j in range(i + 1, min(i + 8, len(lines))):
                nxt = lines[j]
                if nxt.startswith("| Memory (GB) |"):
                    for v, g in zip(header, cells(nxt)[1:]):
                        if v.isdigit() and re.fullmatch(r"[\d,.]+", g):
                            memory[f"{prefix}_{v}"] = float(g.replace(",", ""))
                    break
                if nxt.startswith("|") and " memory (GB)" in nxt.lower():
                    break          # serverless: a min-max range, not a single value
                if nxt.startswith("## ") or nxt.startswith("### "):
                    break

    rows = []
    for name, tier, compute, hardware, prefix in VCORE_SECTIONS:
        found = slos.get(prefix)
        if not found:
            raise SystemExit(
                f"no SLOs parsed for '{prefix}' — the '{name}' section of the vCore "
                "resource-limits article changed shape")
        for slo in sorted(found, key=lambda s: int(s.rsplit("_", 1)[1])):
            rows.append({
                "sku": slo,
                "service": "Azure SQL Database",
                "deployment_model": "Single database / Elastic pool",
                "purchasing_model": "vCore",
                "service_tier": tier,
                "compute_tier": compute,
                "hardware": hardware,
                "capacity_unit": "vCore",
                "capacity": int(slo.rsplit("_", 1)[1]),
                "memory_gb": memory.get(slo),
                "source_page": "vcore_single",
            })
    return rows


# --------------------------------------------------------------------------
# Azure SQL Database, DTU purchasing model
# --------------------------------------------------------------------------

def parse_dtu_single(lines: list[str]) -> list[dict]:
    rows, seen = [], set()
    for i, line in enumerate(lines):
        if not line.startswith("| **Compute size**"):
            continue
        names = cells(line)[1:]
        for j in range(i + 1, min(i + 6, len(lines))):
            if lines[j].startswith("| Max DTUs |"):
                for name, dtu in zip(names, cells(lines[j])[1:]):
                    if not name or name in seen or not dtu.replace(",", "").isdigit():
                        continue
                    seen.add(name)
                    tier = ("Basic" if name == "Basic"
                            else "Standard" if name.startswith("S") else "Premium")
                    rows.append({
                        "sku": name,
                        "service": "Azure SQL Database",
                        "deployment_model": "Single database",
                        "purchasing_model": "DTU",
                        "service_tier": tier,
                        "compute_tier": "Provisioned",
                        "hardware": "n/a (DTU model)",
                        "capacity_unit": "DTU",
                        "capacity": int(dtu.replace(",", "")),
                        "memory_gb": None,
                        "source_page": "dtu_single",
                    })
                break
    if len(rows) < 10:
        raise SystemExit("DTU single-database parse returned too few sizes — "
                         "the article changed shape")
    return rows


def parse_dtu_pools(lines: list[str]) -> list[dict]:
    rows, tier, seen = [], None, set()
    for line in lines:
        if line.startswith("### "):
            m = re.match(r"(Basic|Standard|Premium) elastic pool limits",
                         heading_text(line))
            tier = m.group(1) if m else None
            continue
        if tier and line.startswith("| eDTUs per pool |"):
            for v in cells(line)[1:]:
                if not v.replace(",", "").isdigit():
                    continue
                edtu = int(v.replace(",", ""))
                key = (tier, edtu)
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "sku": f"{tier}Pool_{edtu}",
                    "service": "Azure SQL Database",
                    "deployment_model": "Elastic pool",
                    "purchasing_model": "DTU",
                    "service_tier": tier,
                    "compute_tier": "Provisioned",
                    "hardware": "n/a (DTU model)",
                    "capacity_unit": "eDTU",
                    "capacity": edtu,
                    "memory_gb": None,
                    "source_page": "dtu_pools",
                })
    if len(rows) < 20:
        raise SystemExit("DTU elastic pool parse returned too few sizes — "
                         "the article changed shape")
    return rows


# --------------------------------------------------------------------------
# Azure SQL Managed Instance
# --------------------------------------------------------------------------

MI_HW = {
    "Standard-series (Gen5)": ("Gen5", 5.1, 408.0),
    "Premium-series": ("G8IM", 7.0, 560.0),
    "Memory optimized premium-series": ("G8IH", 13.6, 870.4),
}
MI_HW_LABEL = {
    "Standard-series (Gen5)": "Standard-series (Gen5)",
    "Premium-series": "Premium-series",
    "Memory optimized premium-series": "Premium-series memory optimized",
}


def parse_mi(lines: list[str]) -> list[dict]:
    """Read the 'Number of vCores' grid: rows are hardware, columns are tiers."""
    start = None
    for i, line in enumerate(lines):
        if line.startswith("### ") and heading_text(line).startswith("Number of vCores"):
            start = i
            break
    if start is None:
        raise SystemExit("Managed Instance article has no 'Number of vCores' section")

    tiers, rows = None, []
    for line in lines[start:start + 20]:
        if not line.startswith("|"):
            if tiers and rows:
                break
            continue
        c = cells(line)
        if set("".join(c[1:])) <= set("- "):
            continue                                  # separator row
        if c[0].lower().startswith("hardware generation"):
            tiers = c[1:]
            continue
        if tiers and c[0] in MI_HW:
            rows.append((c[0], c[1:]))

    if not rows:
        raise SystemExit("could not read the Managed Instance vCore grid")

    out = []
    for hw, per_tier in rows:
        family, ratio, cap = MI_HW[hw]
        for tier, spec in zip(tiers, per_tier):
            prefix = "BC" if tier.startswith("Business") else "GP"
            for token in spec.split(","):
                token = token.strip()
                if not token.isdigit():
                    continue
                v = int(token)
                out.append({
                    "sku": f"{prefix}_{family} ({v} vCores)",
                    "arm_sku": f"{prefix}_{family}",
                    "service": "Azure SQL Managed Instance",
                    "deployment_model": "Managed instance",
                    "purchasing_model": "vCore",
                    "service_tier": tier,
                    "compute_tier": "Provisioned",
                    "hardware": MI_HW_LABEL[hw],
                    "capacity_unit": "vCore",
                    "capacity": v,
                    "memory_gb": round(min(v * ratio, cap), 1),
                    "memory_basis": "ratio",
                    "source_page": "mi_limits",
                })
    return out


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--out", default=os.path.join(HERE, ".cache", "inventory.json"))
    args = ap.parse_args()

    rows = []
    rows += parse_dtu_single(read(args.cache, "dtu_single"))
    rows += parse_dtu_pools(read(args.cache, "dtu_pools"))
    rows += parse_vcore(read(args.cache, "vcore_single"))
    rows += parse_mi(read(args.cache, "mi_limits"))

    payload = {"sku_count": len(rows), "skus": rows}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.write("\n")

    by_service: dict[str, int] = {}
    for r in rows:
        by_service[r["service"]] = by_service.get(r["service"], 0) + 1
    print(f"parsed {len(rows)} SKUs -> {args.out}")
    for k, v in by_service.items():
        print(f"  {k}: {v}")
    missing = [r["sku"] for r in rows
               if r["memory_gb"] is None and r["compute_tier"] == "Provisioned"
               and r["purchasing_model"] == "vCore"]
    if missing:
        print(f"  note: {len(missing)} provisioned vCore SKUs have no published "
              f"Memory (GB) value: {', '.join(missing[:6])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
