#!/usr/bin/env python3
"""Run the whole skill: fetch, parse, diff, build, verify.

    python3 scripts/refresh.py [--out-dir DIR] [--offline] [--skip-links]
                               [--accept-baseline]

Stages:
  1. fetch      pull the Microsoft Learn article sources
  2. parse      extract the SKU inventory from those sources
  3. diff       compare against baseline/inventory.json and report every change
  4. build      emit the JSON, CSV, Markdown table and HTML Atlas
  5. verify     structural checks plus a liveness check on every cited URL

The diff is the point of re-running. Azure changes underneath this catalog: SKUs
appear, previews go GA, hardware retires. Stage 3 says exactly what moved so the
change can be adjudicated against the announcement that caused it, rather than
silently absorbed.

Exit codes: 0 all good; 1 a stage failed; 2 built and verified, but the inventory
differs from the baseline and needs review.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(HERE, "scripts")
BASELINE = os.path.join(HERE, "baseline", "inventory.json")


def run(script: str, *args: str) -> int:
    print(f"\n=== {script} ===")
    return subprocess.call([sys.executable, os.path.join(SCRIPTS, script), *args])


def key(row: dict) -> str:
    return f"{row['sku']} [{row['service_tier']}]"


def diff_inventory(cache: str) -> tuple[bool, list[str]]:
    """Compare the freshly parsed inventory against the committed baseline."""
    new_path = os.path.join(cache, "inventory.json")
    new = {key(r): r for r in json.load(open(new_path, encoding="utf-8"))["skus"]}

    if not os.path.exists(BASELINE):
        return True, [f"no baseline yet — {len(new)} SKUs parsed; "
                      "re-run with --accept-baseline to record one"]

    old = {key(r): r for r in json.load(open(BASELINE, encoding="utf-8"))["skus"]}
    changes = []
    for k in sorted(set(new) - set(old)):
        r = new[k]
        changes.append(f"ADDED    {k} — {r['hardware']}, {r['capacity']} "
                       f"{r['capacity_unit']}")
    for k in sorted(set(old) - set(new)):
        changes.append(f"REMOVED  {k} — no longer in the Microsoft resource-limit tables")
    for k in sorted(set(old) & set(new)):
        for f in ("capacity", "memory_gb", "hardware", "compute_tier",
                  "purchasing_model", "deployment_model"):
            if old[k].get(f) != new[k].get(f):
                changes.append(f"CHANGED  {k}: {f} {old[k].get(f)} -> {new[k].get(f)}")
    return bool(changes), changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--skip-links", action="store_true")
    ap.add_argument("--accept-baseline", action="store_true",
                    help="record the freshly parsed inventory as the new baseline")
    ap.add_argument("--as-of", default=None)
    args = ap.parse_args()

    fetch_args = ["--cache", args.cache] + (["--offline"] if args.offline else [])
    if run("fetch_docs.py", *fetch_args) != 0:
        print("\nfetch failed — cannot build a catalog from stale or partial sources")
        return 1

    if run("parse_inventory.py", "--cache", args.cache) != 0:
        return 1

    print("\n=== diff against baseline ===")
    changed, changes = diff_inventory(args.cache)
    if not changed:
        print("  no inventory changes since the baseline")
    else:
        for c in changes:
            print("  " + c)
        print(f"\n  {len(changes)} change(s). Each one needs a dated Microsoft source "
              "before it ships:\n"
              "    - a new SKU needs a milestone in references/milestones.py and a rule "
              "in references/rules.py\n"
              "    - a lifecycle move (preview -> GA, or a retirement) needs the "
              "what's-new entry that announced it")

    build_args = ["--cache", args.cache, "--out-dir", args.out_dir]
    if args.as_of:
        build_args += ["--as-of", args.as_of]
    if run("build_catalog.py", *build_args) != 0:
        return 1

    if run("build_artifact.py", "--out-dir", args.out_dir) != 0:
        return 1

    verify_args = ["--out-dir", args.out_dir, "--cache", args.cache]
    if args.skip_links:
        verify_args.append("--skip-links")
    if run("verify.py", *verify_args) != 0:
        return 1

    if args.accept_baseline:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        with open(os.path.join(args.cache, "inventory.json"), encoding="utf-8") as fh:
            data = fh.read()
        with open(BASELINE, "w", encoding="utf-8") as fh:
            fh.write(data)
        print(f"\nbaseline updated: {BASELINE}")
        changed = False

    print("\n" + "=" * 60)
    print(f"Outputs in {args.out_dir}:")
    for name in ("azure-sql-sku-table.md", "azure-sql-skus.html",
                 "azure-sql-skus.json", "azure-sql-skus.csv"):
        p = os.path.join(args.out_dir, name)
        if os.path.exists(p):
            print(f"  {name:26} {os.path.getsize(p) // 1024:>4} KB")

    if changed:
        print("\nInventory differs from the baseline — review the diff above before "
              "publishing, then re-run with --accept-baseline.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
