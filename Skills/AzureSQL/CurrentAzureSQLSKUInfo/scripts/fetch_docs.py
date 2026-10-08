#!/usr/bin/env python3
"""Fetch the Microsoft Learn article sources this skill reads.

Downloads the raw Markdown for every page in references/sources.json into a
cache directory. Working from the article source rather than rendered HTML is
what makes the inventory parse deterministic — the source states SLO names
explicitly ("The following table covers these SLOs: `GP_Gen5_2`, ...").

    python3 scripts/fetch_docs.py [--cache DIR] [--offline]

--offline reuses whatever is already cached and fails if anything is missing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(HERE, "references", "sources.json")
UA = "SKUAgility-CurrentAzureSQLSKUInfo (+https://github.com/shsingla22/SKUAgility)"


def load_sources() -> dict:
    with open(SOURCES, encoding="utf-8") as fh:
        return json.load(fh)


def raw_url(src: dict, key: str) -> str:
    return f"{src['raw_base']}/{src['pages'][key]['path']}.md"


def live_url(src: dict, key: str) -> str:
    return f"{src['live_base']}/{src['pages'][key]['path']}"


def fetch(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} for {url}")
        return resp.read().decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    src = load_sources()
    os.makedirs(args.cache, exist_ok=True)

    failures = []
    for key in src["pages"]:
        dest = os.path.join(args.cache, key + ".md")
        if args.offline:
            if not os.path.exists(dest):
                failures.append(f"{key}: not cached and --offline was given")
            else:
                print(f"  cached  {key}")
            continue
        try:
            text = fetch(raw_url(src, key))
        except Exception as exc:                       # network or 404
            failures.append(f"{key}: {exc}")
            print(f"  FAILED  {key}: {exc}", file=sys.stderr)
            continue
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"  fetched {key} ({len(text) // 1024} KB)")

    if failures:
        print(f"\n{len(failures)} page(s) unavailable:", file=sys.stderr)
        for f in failures:
            print("  - " + f, file=sys.stderr)
        return 1

    print(f"\nAll {len(src['pages'])} pages available in {args.cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
