"""Compare this catalog's SKUs against a workload's Azure Migrate-supported SKU list.

`migrate_support.json` records, per workload, the SKU names Azure Migrate's
discovery-and-assessment tooling recognizes for that service — as supplied to this
skill (a document, a support article, whatever the workload's entry names as its
`source`), not derived from the same Microsoft pages the rest of the catalog reads.
A workload with no entry gets an honest "not supplied yet" result rather than a
silent empty comparison, so every service section can carry both call-outs below
even before its Migrate data exists.

The comparison is bucketed by Azure lifecycle status, and every bucket is reported
in full — every SKU in the bucket, with its Migrate-support status — not just the
ones that disagree. A clean bucket (no disagreement) still reports its numbers
rather than being silently omitted, because "nothing to flag" is itself a fact
worth stating plainly.

Three things are flagged, because they are the three ways the catalogs can
disagree in a way that matters operationally:

  - a SKU Azure has GA that Migrate does NOT support — Migrate will not assess
    or move workloads on it, so recommending it blocks a Migrate-based migration.
  - a SKU Azure has in public preview that Migrate does NOT support — the same
    problem, one release stage earlier: it's not yet safe to plan a Migrate-based
    move onto it.
  - a SKU Azure has deprecated or retiring that Migrate DOES support — Migrate
    may recommend landing on something Azure is already walking back.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load() -> dict:
    path = os.path.join(HERE, "references", "migrate_support.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def status_bucket(lifecycle_status: str) -> str:
    ls = lifecycle_status or ""
    if "preview" in ls:
        return "preview"
    if ls.startswith(("Deprecated", "Retiring", "Retired", "End of Life",
                      "Previous generation")):
        return "deprecated"
    return "ga"


# A bucket is flagged when Migrate's support disagrees with what you'd want:
# GA and preview SKUs should be supported; deprecated/retiring ones should not.
FLAG_WHEN_UNSUPPORTED = {"ga", "preview"}


def _detail(r, supported: set, details: dict) -> dict:
    migrate_supported = r.sku in supported
    bucket = status_bucket(r.lifecycle_status)
    if bucket in FLAG_WHEN_UNSUPPORTED:
        flagged = not migrate_supported
    else:
        flagged = migrate_supported
    return {
        "sku": r.sku,
        "tier": r.tier,
        "lifecycle_status": r.lifecycle_status,
        "release_date": r.release_date,
        "date_confidence": r.date_confidence,
        "milestone_label": r.milestone_label,
        "release_doc": r.release_doc,
        "migrate_supported": migrate_supported,
        "flagged": flagged,
        # Whatever else the supplied list says about this SKU (Migrate's own SKU
        # name, its Dev/Test vs Production class) — optional, shown when present.
        "migrate_sku_name": details.get(r.sku, {}).get("migrate_sku_name"),
        "migrate_class": details.get(r.sku, {}).get("migrate_class"),
    }


def _spec_mismatches(service_rows: list, details: dict) -> list[dict]:
    """Where Migrate's list states vCores/RAM, check them against Azure's own."""
    out = []
    for r in service_rows:
        d = details.get(r.sku)
        if not d:
            continue
        bad = {}
        if d.get("vcores") is not None and r.capacity is not None and float(d["vcores"]) != float(r.capacity):
            bad["vcores"] = (r.capacity, d["vcores"])
        if d.get("memory_gib") is not None and r.memory_gb is not None and float(d["memory_gib"]) != float(r.memory_gb):
            bad["memory_gb"] = (r.memory_gb, d["memory_gib"])
        if bad:
            out.append({"sku": r.sku, **{k: {"azure": a, "migrate": m} for k, (a, m) in bad.items()}})
    return sorted(out, key=lambda x: x["sku"])


def _bucket(rows: list) -> dict:
    rows = sorted(rows, key=lambda d: d["sku"])
    flagged = [d for d in rows if d["flagged"]]
    return {
        "total": len(rows),
        "supported_count": sum(1 for d in rows if d["migrate_supported"]),
        "flagged_count": len(flagged),
        "rows": rows,
    }


def compare(service_rows: list, entry: dict | None) -> dict:
    """Migrate-support comparison for one service's already-resolved Sku rows.

    Always returns a dict; `available` is False when the workload has no entry
    in migrate_support.json yet, which the caller renders as an honest gap
    rather than omitting either call-out.

    Every bucket (ga / deprecated / preview) carries every SKU in that bucket,
    each tagged `migrate_supported` and `flagged` — a clean bucket still reports
    its total and supported count, it just has `flagged_count == 0`.
    """
    if not entry:
        return {"available": False}

    supported = set(entry.get("supported_skus", []))
    details = entry.get("sku_details", {})
    buckets: dict[str, list] = {"ga": [], "deprecated": [], "preview": []}
    catalog_skus = set()

    for r in service_rows:
        catalog_skus.add(r.sku)
        buckets[status_bucket(r.lifecycle_status)].append(_detail(r, supported, details))

    return {
        "available": True,
        "source": entry.get("source", ""),
        "as_of": entry.get("as_of", ""),
        "supported_count": len(supported),
        "ga": _bucket(buckets["ga"]),
        "deprecated": _bucket(buckets["deprecated"]),
        "preview": _bucket(buckets["preview"]),
        # Migrate-listed names this catalog cannot find at all — either a naming
        # mismatch or a SKU Azure has removed from the docs entirely. Surfaced so
        # a silent match (every bucket clean) can't hide a broken join.
        "unknown_to_azure": sorted(supported - catalog_skus),
        # Where the supplied list also states sizes, disagreements with Azure's
        # own figures — a sign one of the two lists is stale.
        "spec_mismatches": _spec_mismatches(service_rows, details),
        "has_details": bool(details),
    }
