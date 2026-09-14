"""Compare this catalog's SKUs against a workload's Azure Migrate-supported SKU list.

`migrate_support.json` records, per workload, the SKU names Azure Migrate's
discovery-and-assessment tooling recognizes for that service — as supplied to this
skill (a document, a support article, whatever the workload's entry names as its
`source`), not derived from the same Microsoft pages the rest of the catalog reads.
A workload with no entry gets an honest "not supplied yet" result rather than a
silent empty comparison, so every service section can carry this block even before
its Migrate data exists.

Two things are flagged, because they are the two ways the catalogs can disagree in
a way that matters operationally:

  - a SKU Azure has GA and Migrate does NOT support — Migrate will not assess or
    move workloads on it, so recommending it blocks a Migrate-based migration.
  - a SKU Azure has deprecated or retiring and Migrate DOES support — Migrate may
    recommend landing on something Azure is already walking back.

A SKU still in preview is neither: it is reported separately, as informational
"not yet assessed" context, never as a flag.
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
    if ls.startswith(("Deprecated", "Retiring", "Retired", "Previous generation")):
        return "deprecated"
    return "ga"


def _detail(r) -> dict:
    return {
        "sku": r.sku,
        "tier": r.tier,
        "lifecycle_status": r.lifecycle_status,
        "release_date": r.release_date,
        "date_confidence": r.date_confidence,
        "milestone_label": r.milestone_label,
        "release_doc": r.release_doc,
    }


def compare(service_rows: list, entry: dict | None) -> dict:
    """Migrate-support comparison for one service's already-resolved Sku rows.

    Always returns a dict; `available` is False when the workload has no entry
    in migrate_support.json yet, which the caller renders as an honest gap
    rather than omitting the block.
    """
    if not entry:
        return {"available": False}

    supported = set(entry.get("supported_skus", []))
    ga_unsupported, deprecated_supported, preview_unassessed = [], [], []
    catalog_skus = set()

    for r in service_rows:
        catalog_skus.add(r.sku)
        bucket = status_bucket(r.lifecycle_status)
        if bucket == "ga" and r.sku not in supported:
            ga_unsupported.append(_detail(r))
        elif bucket == "deprecated" and r.sku in supported:
            deprecated_supported.append(_detail(r))
        elif bucket == "preview" and r.sku not in supported:
            preview_unassessed.append(_detail(r))

    return {
        "available": True,
        "source": entry.get("source", ""),
        "as_of": entry.get("as_of", ""),
        "supported_count": len(supported),
        "ga_unsupported": sorted(ga_unsupported, key=lambda d: d["sku"]),
        "deprecated_supported": sorted(deprecated_supported, key=lambda d: d["sku"]),
        "preview_unassessed": sorted(preview_unassessed, key=lambda d: d["sku"]),
        # Migrate-listed names this catalog cannot find at all — either a naming
        # mismatch or a SKU Azure has removed from the docs entirely. Surfaced so
        # a silent match (both lists happen to be empty of complaints) can't hide
        # a broken join.
        "unknown_to_azure": sorted(supported - catalog_skus),
    }
