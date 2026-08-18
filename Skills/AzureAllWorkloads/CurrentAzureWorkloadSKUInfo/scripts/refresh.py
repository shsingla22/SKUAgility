#!/usr/bin/env python3
"""Run the whole skill: fetch, build, diff, verify.

    python3 scripts/refresh.py [--out-dir DIR] [--offline] [--skip-links]
                               [--workload NAME] [--accept-baseline]

Stages:
  1. fetch    pull every documentation source declared in references/sources.json
  2. build    run each workload provider and emit JSON, CSV, Markdown and the Atlas
  3. diff     compare against baseline/inventory.json and report every change
  4. verify   structural checks plus a liveness check on every cited URL

The diff is why re-running is worth anything. Azure moves underneath this
catalog constantly — SKUs appear, previews go GA, whole services get retirement
dates. Stage 3 says exactly what moved so it can be checked against the
announcement that caused it.

Exit codes: 0 clean; 1 a stage failed; 2 built and verified but the inventory
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
    return f"{row['service']} :: {row['sku']} [{row['tier']}]"


def snapshot(out_dir: str) -> dict:
    path = os.path.join(out_dir, "azure-workload-skus.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {key(r): {"capacity": r["capacity"], "memory_gb": r["memory_gb"],
                     "lifecycle_status": r["lifecycle_status"],
                     "series": r["series"]}
            for r in data["skus"]}


def diff_against_baseline(out_dir: str) -> tuple[bool, list[str]]:
    new = snapshot(out_dir)
    if not os.path.exists(BASELINE):
        return True, [f"no baseline yet — {len(new)} SKUs built; re-run with "
                      "--accept-baseline to record one"]
    with open(BASELINE, encoding="utf-8") as fh:
        old = json.load(fh)

    changes = []
    for k in sorted(set(new) - set(old)):
        changes.append(f"ADDED    {k}")
    for k in sorted(set(old) - set(new)):
        changes.append(f"REMOVED  {k}")
    for k in sorted(set(old) & set(new)):
        for f in ("capacity", "memory_gb", "lifecycle_status", "series"):
            if old[k].get(f) != new[k].get(f):
                changes.append(f"CHANGED  {k}: {f} {old[k].get(f)} -> {new[k].get(f)}")
    return bool(changes), changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--skip-links", action="store_true")
    ap.add_argument("--workload")
    ap.add_argument("--accept-baseline", action="store_true")
    ap.add_argument("--as-of")
    args = ap.parse_args()

    fetch_args = ["--cache", args.cache]
    if args.offline:
        fetch_args.append("--offline")
    if args.workload:
        fetch_args += ["--workload", args.workload]
    if run("fetch_docs.py", *fetch_args) != 0:
        print("\nfetch failed — a catalog built from partial sources would look "
              "complete while missing a service", file=sys.stderr)
        return 1

    build_args = ["--cache", args.cache, "--out-dir", args.out_dir]
    if args.workload:
        build_args += ["--workload", args.workload]
    if args.offline:
        build_args.append("--offline")
    if args.as_of:
        build_args += ["--as-of", args.as_of]
    if run("build_catalog.py", *build_args) != 0:
        return 1

    if run("build_artifact.py", "--out-dir", args.out_dir) != 0:
        return 1

    print("\n=== diff against baseline ===")
    changed, changes = diff_against_baseline(args.out_dir)
    if not changed:
        print("  no catalog changes since the baseline")
    else:
        for c in changes[:80]:
            print("  " + c)
        if len(changes) > 80:
            print(f"  ... and {len(changes) - 80} more")
        print(f"\n  {len(changes)} change(s). Each needs a dated Microsoft source "
              "before it ships:\n"
              "    - a new SKU needs a milestone in references/milestones.py\n"
              "    - a lifecycle move (preview -> GA, or a retirement) needs the\n"
              "      announcement or what's-new entry that declared it")

    verify_args = ["--out-dir", args.out_dir, "--cache", args.cache]
    if args.skip_links:
        verify_args.append("--skip-links")
    if run("verify.py", *verify_args) != 0:
        return 1

    if args.accept_baseline:
        os.makedirs(os.path.dirname(BASELINE), exist_ok=True)
        with open(BASELINE, "w", encoding="utf-8") as fh:
            json.dump(snapshot(args.out_dir), fh, indent=1, sort_keys=True)
            fh.write("\n")
        print(f"\nbaseline updated: {BASELINE}")
        changed = False

    print("\n" + "=" * 60)
    print(f"Outputs in {args.out_dir}:")
    for name in ("azure-workload-sku-table.md", "azure-workload-skus.html",
                 "azure-workload-skus.json", "azure-workload-skus.csv"):
        p = os.path.join(args.out_dir, name)
        if os.path.exists(p):
            print(f"  {name:30} {os.path.getsize(p) // 1024:>4} KB")

    if changed:
        print("\nCatalog differs from the baseline — review the diff above, then "
              "re-run with --accept-baseline.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
