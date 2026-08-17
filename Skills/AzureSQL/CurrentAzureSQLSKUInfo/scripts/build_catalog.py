#!/usr/bin/env python3
"""Join the parsed inventory with the release, lifecycle and guidance references.

Reads .cache/inventory.json (from parse_inventory.py) and emits, into --out-dir:

    azure-sql-skus.json       machine-readable catalog + milestone registry
    azure-sql-skus.csv        flat table
    azure-sql-sku-table.md    the deliverable Markdown table

    python3 scripts/build_catalog.py [--cache DIR] [--out-dir DIR]

Any SKU the rules can't classify is reported and the build fails, so a newly
introduced hardware family surfaces instead of shipping with a blank date.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import asdict, dataclass, field

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "references"))

from guidance import GUIDANCE, PURCHASING_MODEL_NOTE          # noqa: E402
from milestones import MILESTONES                             # noqa: E402
from rules import (                                           # noqa: E402
    INVENTORY_DOC, PREVIEW, RETIRED_FAMILIES, UNMAPPED, classify,
)

LIVE_BASE = "https://learn.microsoft.com/azure/azure-sql"


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
    memory_basis: str
    lifecycle_status: str
    release_date: str
    preview_date: str | None
    ga_date: str | None
    date_confidence: str
    milestone: str
    milestone_label: str
    inventory_doc: str
    release_doc: str
    recommend_when: list[str] = field(default_factory=list)
    recommend_sources: list[str] = field(default_factory=list)
    notes: str = ""


def build_rows(inventory: dict) -> tuple[list[Sku], list[str]]:
    rows, unmapped = [], []
    for r in inventory["skus"]:
        c = classify(r)
        if c["milestone"] == UNMAPPED or c["guidance_key"] == UNMAPPED:
            unmapped.append(r["sku"])
            continue

        m = MILESTONES[c["milestone"]]
        release = (m.preview if c["lifecycle_status"] == PREVIEW else m.ga) \
            or m.preview or m.ga or "unknown"

        note, note_src = PURCHASING_MODEL_NOTE[r["purchasing_model"]]
        when, sources = [note], [note_src]
        for key in c["guidance_key"].split("+"):
            entry = GUIDANCE[key]
            when += list(entry["when"])
            sources += [s for s in entry["sources"] if s not in sources]

        rows.append(Sku(
            sku=r["sku"],
            service=r["service"],
            deployment_model=r["deployment_model"],
            purchasing_model=r["purchasing_model"],
            service_tier=r["service_tier"],
            compute_tier=r["compute_tier"],
            hardware=r["hardware"],
            capacity_unit=r["capacity_unit"],
            capacity=r["capacity"],
            memory_gb=r["memory_gb"],
            memory_basis=r.get("memory_basis", "published"),
            lifecycle_status=c["lifecycle_status"],
            release_date=release,
            preview_date=m.preview,
            ga_date=m.ga,
            date_confidence=m.confidence,
            milestone=m.key,
            milestone_label=m.label,
            inventory_doc=f"{LIVE_BASE}/{INVENTORY_DOC[r['source_page']]}",
            release_doc=m.source,
            recommend_when=when,
            recommend_sources=sources,
            notes=m.note,
        ))
    return rows, unmapped


# --------------------------------------------------------------------------
# Emitters
# --------------------------------------------------------------------------

def numbered(items: list[str]) -> str:
    return "<br>".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def links(urls: list[str]) -> str:
    return "<br>".join(f"[{i}]({u})" for i, u in enumerate(urls, 1))


def write_markdown(rows: list[Sku], path: str, as_of: str) -> None:
    lines = [
        "# Azure SQL — complete SKU table",
        "",
        f"Every Azure SQL Database and Azure SQL Managed Instance SKU that Microsoft "
        f"currently documents: **{len(rows)} SKUs**. Generated {as_of} by the "
        "`CurrentAzureSQLSKUInfo` skill, direct from Microsoft Learn article sources.",
        "",
        "Column notes:",
        "",
        "- **Release date** — the GA date of the release that made the SKU orderable, or "
        "the preview date for SKUs still in preview. Microsoft publishes release dates "
        "per SKU *family*, not per individual size, so sizes added later than their "
        "family carry their own date.",
        "- **Confidence** — how firmly the date is sourced. `high` = a dated Microsoft "
        "announcement names this exact change; `medium` = a Microsoft page dates it to a "
        "month; `low` = reconstructed from context, treat as approximate.",
        "- **Lifecycle status** — read from the current Microsoft documentation.",
        "- **When to recommend** — paraphrased from the Microsoft pages linked in the "
        "last column. No third-party or inferred advice.",
        "- **Memory** — transcribed from the published `Memory (GB)` rows for Azure SQL "
        "Database; derived from the documented per-vCore ratio and cap for Managed "
        "Instance, whose docs publish ratios rather than a per-size table.",
        "",
        "| # | SKU | Deployment | Service tier | Hardware | Size | Release date "
        "| Confidence | Lifecycle status | SKU data source | Release date source "
        "| When to recommend this SKU | Recommendation source |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, s in enumerate(rows, 1):
        size = f"{s.capacity:g} {s.capacity_unit}"
        if s.memory_gb is not None:
            size += f" / {s.memory_gb:g} GB"
        tier = s.service_tier + ("" if s.compute_tier == "Provisioned"
                                 else " — " + s.compute_tier)
        lines.append(
            f"| {i} | `{s.sku}` | {s.deployment_model} | {tier} | {s.hardware} | {size} "
            f"| {s.release_date} | {s.date_confidence} | {s.lifecycle_status} "
            f"| [docs]({s.inventory_doc}) | [announcement]({s.release_doc}) "
            f"| {numbered(s.recommend_when)} | {links(s.recommend_sources)} |"
        )

    used = {s.milestone for s in rows}
    lines += ["", "## Release milestones", "",
              "| Milestone | Preview | GA | Confidence | Source |",
              "| --- | --- | --- | --- | --- |"]
    for key, m in MILESTONES.items():
        if key in used:
            lines.append(f"| {m.label} | {m.preview or '—'} | {m.ga or '—'} "
                         f"| {m.confidence} | [link]({m.source}) |")

    notes = [MILESTONES[k] for k in MILESTONES if k in used and MILESTONES[k].note]
    if notes:
        lines += ["", "### Milestone notes", ""]
        lines += [f"- **{m.label}** — {m.note}" for m in notes]

    lines += ["", "## Retired and deprecated hardware families", "",
              "Gen4 and M-series no longer appear in the Microsoft resource-limit tables "
              "at all, so their individual service-level objectives cannot be enumerated "
              "from a current Microsoft page — they are recorded at family level rather "
              "than invented as SKU rows. Fsv2-series is still fully documented and its "
              "sizes appear individually in the table above.", "",
              "| Family | Status | Retired | Detail | Source |",
              "| --- | --- | --- | --- | --- |"]
    for f in RETIRED_FAMILIES:
        lines.append(f"| {f['family']} | {f['status']} | {f['retired']} | {f['detail']} "
                     f"| [link]({f['source']}) |")
    lines.append("")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def write_json(rows: list[Sku], path: str, as_of: str) -> None:
    used = {s.milestone for s in rows}
    payload = {
        "generated": as_of,
        "generator": "Skills/AzureSQL/CurrentAzureSQLSKUInfo",
        "sku_count": len(rows),
        "date_confidence_legend": {
            "high": "a dated Microsoft announcement or release note names this exact change",
            "medium": "a Microsoft page dates the change to a month, or a reputable "
                      "secondary source corroborates a first-party announcement",
            "low": "reconstructed from context; treat the date as approximate",
        },
        "release_milestones": [
            {"key": m.key, "label": m.label, "preview": m.preview, "ga": m.ga,
             "confidence": m.confidence, "source": m.source, "note": m.note}
            for k, m in MILESTONES.items() if k in used
        ],
        "retired_families": RETIRED_FAMILIES,
        "skus": [asdict(s) for s in rows],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def write_csv(rows: list[Sku], path: str) -> None:
    fields = [f for f in asdict(rows[0]) if f not in ("recommend_when", "recommend_sources")]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields + ["recommend_when", "recommend_sources"])
        w.writeheader()
        for s in rows:
            d = asdict(s)
            d["recommend_when"] = " | ".join(
                f"{i}. {t}" for i, t in enumerate(d["recommend_when"], 1))
            d["recommend_sources"] = " | ".join(d["recommend_sources"])
            w.writerow(d)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    ap.add_argument("--as-of", default=None, help="ISO date stamped on the outputs")
    args = ap.parse_args()

    as_of = args.as_of
    if not as_of:
        import datetime
        as_of = datetime.date.today().isoformat()

    with open(os.path.join(args.cache, "inventory.json"), encoding="utf-8") as fh:
        inventory = json.load(fh)

    rows, unmapped = build_rows(inventory)
    if unmapped:
        print("BUILD FAILED — these SKUs matched no rule in references/rules.py:",
              file=sys.stderr)
        for s in unmapped:
            print("  " + s, file=sys.stderr)
        print("\nAdd a milestone and guidance entry for them before shipping the "
              "catalog; a SKU with no dated source must not ship with a blank date.",
              file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    write_json(rows, os.path.join(args.out_dir, "azure-sql-skus.json"), as_of)
    write_csv(rows, os.path.join(args.out_dir, "azure-sql-skus.csv"))
    write_markdown(rows, os.path.join(args.out_dir, "azure-sql-sku-table.md"), as_of)

    counts: dict[str, int] = {}
    for s in rows:
        counts[s.lifecycle_status] = counts.get(s.lifecycle_status, 0) + 1
    print(f"built {len(rows)} SKUs -> {args.out_dir}")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
