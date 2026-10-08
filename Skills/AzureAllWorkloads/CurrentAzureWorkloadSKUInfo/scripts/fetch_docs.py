#!/usr/bin/env python3
"""Download every documentation source this skill reads.

    python3 scripts/fetch_docs.py [--cache DIR] [--offline] [--services LIST]

Sources are declared in references/sources.json and selected by
references/config.json, so which services get fetched is a configuration
choice. Each source names its own fetch strategy, so adding one is a data
change, not a code change.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("", "/scripts", "/providers", "/references"):
    sys.path.insert(0, HERE + _sub)

from docsource import fetch                                    # noqa: E402
import providers as registry                                   # noqa: E402
SOURCES = os.path.join(HERE, "references", "sources.json")


def load_specs(services: str | None = None) -> dict:
    with open(SOURCES, encoding="utf-8") as fh:
        specs = json.load(fh)["sources"]
    for key, spec in specs.items():
        spec["key"] = key
    wanted = {s["key"] for s in registry.selected(services)}
    return {k: v for k, v in specs.items() if v["workload"] in wanted}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--services", help="comma-separated service keys, or 'all'; "
                                       "defaults to whatever is enabled in "
                                       "references/config.json")
    args = ap.parse_args()

    chosen = registry.selected(args.services)
    print(f"Services: {', '.join(s['display'] for s in chosen)}")
    specs = load_specs(args.services)
    if not specs:
        print("  (the selected services declare no fetchable sources of their own)")
    failures = []
    for key, spec in specs.items():
        try:
            payload = fetch(spec, args.cache, offline=args.offline)
            print(f"  {'cached ' if args.offline else 'fetched'} "
                  f"{key:22} {len(payload) // 1024:>4} KB  ({spec['strategy']})")
        except Exception as exc:
            failures.append(f"{key}: {exc}")
            print(f"  FAILED  {key}: {exc}", file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} source(s) unavailable — a partial fetch would "
              f"produce a partial catalog, so this is a hard failure.", file=sys.stderr)
        return 1
    print(f"\nAll {len(specs)} sources available in {args.cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
