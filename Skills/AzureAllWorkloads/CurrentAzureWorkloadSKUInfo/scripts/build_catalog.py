#!/usr/bin/env python3
"""Run every workload provider and emit the cross-workload catalog.

    python3 scripts/build_catalog.py [--cache DIR] [--out-dir DIR]
                                     [--services LIST] [--offline]

Writes into --out-dir:
    azure-workload-skus.json     catalog + milestone registry + errata
    azure-workload-skus.csv      flat table
    azure-workload-sku-table.md  the deliverable Markdown table

A provider that raises is reported and fails the build. A partial catalog that
looks complete is the worst outcome here, so there is no "skip the broken one"
path.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("", "/scripts", "/providers", "/references"):
    sys.path.insert(0, HERE + sub)

from docsource import load                                   # noqa: E402
from milestones import MILESTONES, NOT_ESTABLISHED           # noqa: E402
import migrate_support                                       # noqa: E402
import providers as registry                                 # noqa: E402

COLUMNS = ("| # | SKU | Tier | Series / family | Size | Release date | Confidence "
           "| Lifecycle status | SKU data source | Release date source "
           "| When to recommend this SKU | Recommendation source |\n"
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")


def load_specs() -> dict:
    with open(os.path.join(HERE, "references", "sources.json"), encoding="utf-8") as fh:
        specs = json.load(fh)["sources"]
    for k, v in specs.items():
        v["key"] = k
    return specs


def release_sort_key(date: str) -> tuple[int, int, int]:
    """Sort key for a release date, newest first when reversed.

    Dates arrive at whatever precision Microsoft published: "2025-11-14",
    "2025-11", or bare "2025". A coarser date sorts as the start of its period,
    so 2016-08 is newer than a bare 2016. "not established" sorts oldest so
    undated SKUs collect at the bottom of their section rather than the top.
    """
    if not date or date == NOT_ESTABLISHED:
        return (-1, -1, -1)
    parts = date.split("-")
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return (-1, -1, -1)
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def order_rows(rows: list, service_order: list[str]) -> list:
    """Group by service in configured order, newest SKU first within each group.

    Applied once, before anything is emitted, so the Markdown table, the CSV,
    the JSON and the Atlas all present the same order. Python's sort is stable,
    so SKUs sharing a release date keep the order their provider produced them
    in — which is the documentation's own order, and is deterministic.
    """
    groups: dict[str, list] = {}
    for r in rows:
        groups.setdefault(r.service, []).append(r)

    ordered_services = [s for s in service_order if s in groups]
    ordered_services += [s for s in groups if s not in ordered_services]

    out = []
    for svc in ordered_services:
        group = groups[svc]
        group.sort(key=lambda r: release_sort_key(r.release_date), reverse=True)
        out += group
    return out


def numbered(items: list[str]) -> str:
    return "<br>".join(f"{i}. {t}" for i, t in enumerate(items, 1))


def links(urls: list[str]) -> str:
    seen, out = set(), []
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return "<br>".join(f"[{i}]({u})" for i, u in enumerate(out, 1))


def sku_row(i: int, r) -> str:
    size = "—"
    if r.capacity is not None:
        size = f"{r.capacity:g} {r.capacity_unit}"
        if r.memory_gb is not None:
            size += f" / {r.memory_gb:g} GB"
    return (f"| {i} | `{r.sku}` | {r.tier} | {r.series} | {size} "
            f"| {r.release_date} | {r.date_confidence} | {r.lifecycle_status} "
            f"| [docs]({r.inventory_doc}) | [announcement]({r.release_doc}) "
            f"| {numbered(r.recommend_when)} | {links(r.recommend_sources)} |")


def migrate_comparisons(by_service: dict) -> dict:
    """Migrate-support comparison for every service, keyed by service display name.

    Every configured service gets an entry, including workloads with no
    migrate_support.json data yet — those come back {"available": False} so the
    Markdown and Atlas can say "not supplied yet" instead of omitting the block.
    """
    support = migrate_support.load()
    out = {}
    for svc, group in by_service.items():
        workload = group[0].workload
        out[svc] = migrate_support.compare(
            group, migrate_support.entry_for(support, svc, workload))
    return out


MIGRATE_TABLE_HEADER = ("| # | SKU | Tier | Lifecycle status | Since | Confidence "
                        "| Migrate supported | Flag |\n"
                        "| --- | --- | --- | --- | --- | --- | --- | --- |")


def _migrate_flag_text(bucket_kind: str, flagged: bool) -> str:
    if not flagged:
        return "—"
    if bucket_kind == "deprecated":
        return "⚠️ Migrate still supports this"
    return "⚠️ Not Migrate-supported"


def _migrate_bucket_lines(bucket_kind: str, label: str, bucket: dict,
                          detailed: bool = False, flagged_only: bool = False,
                          cols: tuple = (True, True)) -> list[str]:
    """Lines for one lifecycle bucket's table: always emitted, even at zero rows."""
    lines = [f"**{label}** — {bucket['total']} SKU(s), Migrate supports "
             f"{bucket['supported_count']}, {bucket['flagged_count']} flagged.", ""]
    if bucket.get("flagged_groups"):
        lines += ["Flagged, by tier and hardware: " + "; ".join(
            f"{g['tier']} · {g['series']}: {g['count']}" if g['series'] else f"{g['tier']}: {g['count']}"
            for g in bucket["flagged_groups"]) + ".", ""]
    if bucket["total"] == 0:
        lines += [f"No {label.lower()} SKUs for this service — nothing to compare.", ""]
        return lines
    rows = bucket["rows"]
    if flagged_only:
        rows = [d for d in rows if d["flagged"]]
        lines += [f"Listing the {len(rows)} flagged SKU(s) only; the "
                  f"{bucket['total'] - len(rows)} that agree with Migrate are counted "
                  "above and not listed individually.", ""]
        if not rows:
            return lines
    if detailed:
        extra_heads = [h for h, on in (("Migrate SKU name", cols[0]), ("Migrate class", cols[1])) if on]
        header = ("| # | SKU | Tier | Lifecycle status | Since | Confidence | Migrate supported | "
                  + " | ".join(extra_heads) + (" | " if extra_heads else "") + "Flag |\n"
                  + "| --- " * (8 + len(extra_heads)) + "|")
        lines += [header]
    else:
        lines += [MIGRATE_TABLE_HEADER]
    for i, d in enumerate(rows, 1):
        yn = "Yes" if d["migrate_supported"] else "No"
        flag = _migrate_flag_text(bucket_kind, d["flagged"])
        extra = ""
        if detailed:
            if cols[0]:
                extra += f"| {('`' + d['migrate_sku_name'] + '`') if d.get('migrate_sku_name') else '—'} "
            if cols[1]:
                extra += f"| {d.get('migrate_class') or '—'} "
        lines.append(f"| {i} | `{d['sku']}` | {d['tier']} | {d['lifecycle_status']} "
                     f"| {d['release_date']} | {d['date_confidence']} | {yn} {extra}| {flag} |")
    lines.append("")
    return lines


def migrate_section_lines(svc: str, cmp: dict) -> list[str]:
    """Markdown for the two Migrate-support sections at the top of one section.

    Both sections always appear, and always state their numbers — a clean bucket
    (nothing flagged) is reported as plainly as a dirty one, never omitted.
    """
    lines = ["### GA SKU discrepancies", ""]
    if not cmp["available"]:
        lines += ["Comparison data has not been supplied for this service yet — "
                  "no flags to show.", "",
                  "### Public preview SKU discrepancies", "",
                  "Comparison data has not been supplied for this service yet — "
                  "no flags to show.", ""]
        return lines

    lines += [f"Compared against {cmp['supported_count']} SKUs Azure Migrate "
              f"supports for this service, as of {cmp['as_of']}. Source: "
              f"{cmp['source']}", ""]
    if cmp.get("scope_note"):
        lines += [f"*Scope: {cmp['scope_note']}*", ""]
    detailed = cmp.get("has_details", False)
    fo = cmp.get("table_mode") == "flagged_only"
    cols = (cmp.get("has_sku_names", True), cmp.get("has_classes", True))
    lines += _migrate_bucket_lines("ga", "Generally available", cmp["ga"], detailed, fo, cols)
    lines += _migrate_bucket_lines("deprecated", "Deprecated / retiring", cmp["deprecated"], detailed, fo, cols)

    for mm in cmp.get("spec_mismatches", []):
        parts = [f"{k} Azure {v['azure']:g} vs Migrate {v['migrate']:g}"
                 for k, v in mm.items() if k != "sku"]
        lines += [f"*Data-quality note — Migrate's list sizes `{mm['sku']}` differently "
                  f"from Azure's page: {'; '.join(parts)}.*", ""]
    if detailed and not cmp.get("spec_mismatches"):
        lines += ["*Migrate's stated vCores and RAM agree with Azure's page for every "
                  "SKU it lists.*", ""]

    unknown = cmp["unknown_to_azure"]
    if unknown:
        lines += [f"*Data-quality note — Migrate's list names {len(unknown)} "
                  f"SKU(s) this catalog does not find under {svc}: "
                  f"{', '.join(f'`{u}`' for u in unknown)}.*", ""]

    lines += ["### Public preview SKU discrepancies", ""]
    lines += _migrate_bucket_lines("preview", "Public preview", cmp["preview"], detailed,
                                   cmp.get("table_mode") == "flagged_only",
                                   (cmp.get("has_sku_names", True), cmp.get("has_classes", True)))
    return lines


def write_markdown(rows: list, path: str, as_of: str, errata: list[dict],
                   order: list[str]) -> None:
    """One section per Azure service, each with its own table."""
    # rows arrive already grouped by service and sorted newest-first within each
    # group (see order_rows), so this only needs to preserve what it is given.
    by_service: dict[str, list] = {}
    for r in rows:
        by_service.setdefault(r.service, []).append(r)
    ordered = list(by_service)
    migrate = migrate_comparisons(by_service)

    lines = [
        "# Azure workload SKU catalog",
        "",
        f"**{len(rows)} SKUs across {len(by_service)} Azure services.** Generated "
        f"{as_of} by the `CurrentAzureWorkloadSKUInfo` skill, direct from Microsoft "
        "documentation.",
        "",
        "Which services appear here is set in the skill's "
        "`references/config.json`, or overridden for one run with `--services`.",
        "",
        "## Contents",
        "",
        "| Service | SKUs | Section |",
        "| --- | --- | --- |",
    ]
    for svc in ordered:
        anchor = svc.lower().replace(" ", "-").replace("(", "").replace(")", "")
        lines.append(f"| {svc} | {len(by_service[svc])} | [jump](#{anchor}) |")

    lines += [
        "",
        "## How to read the columns",
        "",
        "- **Release date** — the GA date of the release that made the SKU orderable, "
        "or the preview date for SKUs still in preview. Azure announces SKUs by family "
        "or tier, so a size inherits its family's date unless it was added later.",
        "- **Confidence** — `high` a dated Microsoft announcement names this exact "
        "change; `medium` a Microsoft page dates it to a month; `low` reconstructed "
        "from context; **`unknown` means no date could be sourced** and the cell reads "
        f"*{NOT_ESTABLISHED}* rather than carrying a guess.",
        "- **Lifecycle status** — read from the current Microsoft documentation, "
        "including retirement dates where Microsoft has announced them.",
        "- **Ordering** — within each service the newest SKUs come first, by "
        "release date. SKUs sharing a date keep Microsoft's own documentation "
        "order, and any SKU whose date could not be sourced sits at the bottom "
        "of its section.",
        "- **When to recommend** — taken from Microsoft's own guidance "
        "(\"Target workloads\", \"When to use\", service-tier \"when to choose\" "
        "sections and tier descriptions) on the pages linked in the last column.",
        "",
    ]

    for svc in ordered:
        group = by_service[svc]
        anchor_counts: dict[str, int] = {}
        for r in group:
            anchor_counts[r.lifecycle_status] = anchor_counts.get(
                r.lifecycle_status, 0) + 1
        summary = ", ".join(f"{v} {k.lower()}"
                            for k, v in sorted(anchor_counts.items(), key=lambda kv: -kv[1]))
        docs = sorted({r.inventory_doc for r in group})

        lines += [f"## {svc}", "",
                  f"{len(group)} SKUs — {summary}.", ""]
        lines += migrate_section_lines(svc, migrate[svc])
        lines += ["Documentation read for this service:", ""]
        lines += [f"- <{d}>" for d in docs]
        lines += ["", COLUMNS]
        for i, r in enumerate(group, 1):
            lines.append(sku_row(i, r))
        lines.append("")

    used = {r.milestone for r in rows}
    lines += ["## Release milestones", "",
              "| Milestone | Preview | GA | Confidence | Source |",
              "| --- | --- | --- | --- | --- |"]
    for key, m in MILESTONES.items():
        if key in used:
            lines.append(f"| {m.label} | {m.preview or '—'} | {m.ga or '—'} "
                         f"| {m.confidence} | [link]({m.source}) |")

    unknown = sorted({MILESTONES[r.milestone].label for r in rows
                      if r.date_confidence == "unknown"})
    if unknown:
        lines += ["", "## Release dates that could not be sourced", "",
                  "These ship as *not established* rather than as a guess. Each needs "
                  "a dated Microsoft announcement before it can carry a date.", ""]
        lines += [f"- {label}" for label in unknown]

    if errata:
        lines += ["", "## Corrections applied to the source documentation", "",
                  "Typographical errors found in Microsoft's published tables. Each is "
                  "corrected explicitly rather than repeated or silently dropped.", "",
                  "| Workload | Published | Corrected to | Why | Source |",
                  "| --- | --- | --- | --- | --- |"]
        for e in errata:
            lines.append(f"| {e['workload']} | `{e['published']}` | "
                         f"`{e['corrected']}` | {e['reason']} | [link]({e['source']}) |")

    lines.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    ap.add_argument("--services", help="comma-separated service keys, or 'all'; "
                                       "defaults to references/config.json")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--as-of")
    args = ap.parse_args()

    as_of = args.as_of
    if not as_of:
        import datetime
        as_of = datetime.date.today().isoformat()

    specs = load_specs()
    modules = registry.providers_for(args.services)
    print("Services: " + ", ".join(m.DISPLAY for m in modules))

    rows, failures, order = [], [], []
    for provider in modules:
        try:
            docs = {k: load(specs[k], args.cache) for k in provider.SOURCES}
            if getattr(provider, "WANTS_CACHE", False) or provider.WORKLOAD == "azure_sql":
                got = provider.collect(docs, cache=args.cache, offline=args.offline)
            else:
                got = provider.collect(docs)
            rows += got
            for r in got:
                if r.service not in order:
                    order.append(r.service)
            print(f"  {provider.WORKLOAD:18} {len(got):>4} SKUs")
        except Exception as exc:
            failures.append((provider.WORKLOAD, exc))
            print(f"  {provider.WORKLOAD:18} FAILED: {exc}", file=sys.stderr)
            traceback.print_exc(limit=2, file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} provider(s) failed. A partial catalog would look "
              "complete while missing a whole service, so this is a hard failure.",
              file=sys.stderr)
        return 1

    rows = order_rows(rows, order)

    errata = registry.applied_errata(modules)
    os.makedirs(args.out_dir, exist_ok=True)

    by_service: dict[str, list] = {}
    for r in rows:
        by_service.setdefault(r.service, []).append(r)
    migrate = migrate_comparisons(by_service)

    used = {r.milestone for r in rows}
    payload = {
        "generated": as_of,
        "generator": "Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo",
        "sku_count": len(rows),
        "workloads": order,
        "service_order": order,
        "date_confidence_legend": {
            "high": "a dated Microsoft announcement or release note names this change",
            "medium": "a Microsoft page dates the change to a month, or a reputable "
                      "secondary source corroborates a first-party announcement",
            "low": "reconstructed from context; treat the date as approximate",
            "unknown": "no date could be sourced; release_date reads 'not established'",
        },
        "release_milestones": [
            {"key": m.key, "label": m.label, "preview": m.preview, "ga": m.ga,
             "confidence": m.confidence, "source": m.source, "note": m.note,
             "retirement": m.retirement}
            for k, m in MILESTONES.items() if k in used
        ],
        "source_doc_errata": errata,
        "migrate_support": migrate,
        "skus": [r.dict() for r in rows],
    }
    with open(os.path.join(args.out_dir, "azure-workload-skus.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    flat = [r.dict() for r in rows]
    cols = [c for c in flat[0] if c not in ("recommend_when", "recommend_sources")]
    with open(os.path.join(args.out_dir, "azure-workload-skus.csv"), "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["recommend_when", "recommend_sources"])
        w.writeheader()
        for d in flat:
            d = dict(d)
            d["recommend_when"] = " | ".join(
                f"{i}. {t}" for i, t in enumerate(d["recommend_when"], 1))
            d["recommend_sources"] = " | ".join(d["recommend_sources"])
            w.writerow(d)

    write_markdown(rows, os.path.join(args.out_dir, "azure-workload-sku-table.md"),
                   as_of, errata, order)

    life: dict[str, int] = {}
    for r in rows:
        life[r.lifecycle_status] = life.get(r.lifecycle_status, 0) + 1
    print(f"\nbuilt {len(rows)} SKUs across {len(payload['workloads'])} services "
          f"-> {args.out_dir}")
    for k, v in sorted(life.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    n_unknown = sum(1 for r in rows if r.date_confidence == "unknown")
    if n_unknown:
        print(f"  release date not established: {n_unknown}")
    if errata:
        print(f"  source-doc corrections applied: {len(errata)}")
    for svc, cmp in migrate.items():
        if not cmp["available"]:
            continue
        flags = (cmp["ga"]["flagged_count"] + cmp["deprecated"]["flagged_count"]
                 + cmp["preview"]["flagged_count"])
        print(f"  migrate support ({svc}): {flags} flagged "
              f"({cmp['ga']['flagged_count']} GA-unsupported, "
              f"{cmp['deprecated']['flagged_count']} deprecated-but-supported, "
              f"{cmp['preview']['flagged_count']} preview-unsupported)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
