#!/usr/bin/env python3
"""Verify the generated catalog before it is handed to anyone.

Two classes of check:

  Structural — every SKU has a release date, a lifecycle status, an inventory
  source and a release source; every guidance list is non-empty and numbered;
  counts reconcile between the parsed inventory, the JSON, the CSV and the
  Markdown table; the HTML page contains one row per SKU.

  Sources — every distinct URL cited anywhere in the outputs is fetched and must
  return 200. Microsoft retires Tech Community blog posts fairly often, so a
  dead citation is a real defect, not a cosmetic one.

    python3 scripts/verify.py [--out-dir DIR] [--skip-links]

Exit code is non-zero if anything fails, so refresh.py can stop the pipeline.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Safari/537.36")


def check_url(url: str, attempts: int = 3) -> tuple[str, int]:
    """Tech Community intermittently 404s a live page; retry before condemning it."""
    last = 0
    for _ in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA},
                                         method="GET")
            with urllib.request.urlopen(req, timeout=45) as resp:
                last = resp.status
                if last == 200:
                    return url, 200
        except urllib.error.HTTPError as exc:
            last = exc.code
        except Exception:
            last = 0
    return url, last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=os.path.join(HERE, "output"))
    ap.add_argument("--cache", default=os.path.join(HERE, ".cache"))
    ap.add_argument("--skip-links", action="store_true")
    args = ap.parse_args()

    failures: list[str] = []
    warnings: list[str] = []

    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"  FAIL  {msg}")

    def ok(msg: str) -> None:
        print(f"  ok    {msg}")

    # ---- load outputs
    jpath = os.path.join(args.out_dir, "azure-sql-skus.json")
    mpath = os.path.join(args.out_dir, "azure-sql-sku-table.md")
    cpath = os.path.join(args.out_dir, "azure-sql-skus.csv")
    hpath = os.path.join(args.out_dir, "azure-sql-skus.html")
    for p in (jpath, mpath, cpath, hpath):
        if not os.path.exists(p):
            print(f"  FAIL  missing output {p}")
            return 1

    data = json.load(open(jpath, encoding="utf-8"))
    skus = data["skus"]
    md = open(mpath, encoding="utf-8").read()
    html = open(hpath, encoding="utf-8").read()
    with open(cpath, encoding="utf-8") as fh:
        csv_rows = list(csv.DictReader(fh))

    print("Structural checks")

    # ---- counts reconcile across every artifact
    inv_path = os.path.join(args.cache, "inventory.json")
    if os.path.exists(inv_path):
        inv = json.load(open(inv_path, encoding="utf-8"))
        if inv["sku_count"] != len(skus):
            fail(f"parsed inventory has {inv['sku_count']} SKUs but the catalog has "
                 f"{len(skus)} — the rules dropped some")
        else:
            ok(f"catalog covers all {len(skus)} parsed SKUs")

    md_rows = len(re.findall(r"^\| \d+ \| `", md, re.M))
    if md_rows != len(skus):
        fail(f"Markdown table has {md_rows} rows, expected {len(skus)}")
    else:
        ok(f"Markdown table has {md_rows} rows")

    if len(csv_rows) != len(skus):
        fail(f"CSV has {len(csv_rows)} rows, expected {len(skus)}")
    else:
        ok(f"CSV has {len(csv_rows)} rows")

    embedded = re.search(r'<script id="data" type="application/json">(.*?)</script>',
                         html, re.S)
    if not embedded:
        fail("HTML page has no embedded data block")
    else:
        page = json.loads(embedded.group(1))
        if len(page["rows"]) != len(skus):
            fail(f"HTML page carries {len(page['rows'])} rows, expected {len(skus)}")
        else:
            ok(f"HTML page carries {len(page['rows'])} rows")

    # ---- per-SKU completeness
    problems = {"release_date": [], "lifecycle": [], "guidance": [],
                "inventory_doc": [], "release_doc": [], "sources": []}
    for s in skus:
        if not s["release_date"] or s["release_date"] == "unknown":
            problems["release_date"].append(s["sku"])
        if not s["lifecycle_status"]:
            problems["lifecycle"].append(s["sku"])
        if len(s["recommend_when"]) < 3:
            problems["guidance"].append(s["sku"])
        if not s["inventory_doc"].startswith("http"):
            problems["inventory_doc"].append(s["sku"])
        if not s["release_doc"].startswith("http"):
            problems["release_doc"].append(s["sku"])
        if not s["recommend_sources"]:
            problems["sources"].append(s["sku"])
    for name, bad in problems.items():
        if bad:
            fail(f"{len(bad)} SKUs missing {name} (e.g. {', '.join(bad[:4])})")
    if not any(problems.values()):
        ok("every SKU has a release date, lifecycle status, guidance and both sources")

    # ---- lifecycle values are from the known set
    allowed = {"Generally available", "Public preview"}
    unknown = {s["lifecycle_status"] for s in skus
               if s["lifecycle_status"] not in allowed
               and not s["lifecycle_status"].startswith("Deprecated")}
    if unknown:
        fail(f"unexpected lifecycle values: {sorted(unknown)}")
    else:
        ok("lifecycle values are all GA / preview / deprecated")

    # ---- a preview SKU must be dated by its preview announcement
    for s in skus:
        if s["lifecycle_status"] == "Public preview" and s["release_date"] != s["preview_date"]:
            fail(f"{s['sku']} is in preview but dated {s['release_date']} "
                 f"rather than its preview date {s['preview_date']}")

    # ---- confidence is declared honestly
    conf = {}
    for s in skus:
        conf[s["date_confidence"]] = conf.get(s["date_confidence"], 0) + 1
    if set(conf) - {"high", "medium", "low"}:
        fail(f"unexpected confidence values: {sorted(set(conf))}")
    else:
        ok(f"date confidence: {conf}")
        if conf.get("low"):
            warnings.append(
                f"{conf['low']} SKUs carry low-confidence dates — these are "
                "reconstructed from context and are flagged as approximate in the output")

    # ---- sources
    if args.skip_links:
        print("\nSource checks skipped (--skip-links)")
    else:
        urls = set()
        for s in skus:
            urls.add(s["inventory_doc"])
            urls.add(s["release_doc"])
            urls.update(s["recommend_sources"])
        for f in data.get("retired_families", []):
            urls.add(f["source"])
        urls |= set(re.findall(r"\]\((https?://[^)]+)\)", md))

        print(f"\nSource checks ({len(urls)} distinct URLs)")
        dead = []
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            for url, code in ex.map(check_url, sorted(urls)):
                if code != 200:
                    dead.append((code, url))
        if dead:
            for code, url in dead:
                fail(f"HTTP {code} — {url}")
        else:
            ok(f"all {len(urls)} cited URLs return 200")

    # ---- summary
    print()
    if warnings:
        for w in warnings:
            print(f"  note  {w}")
    if failures:
        print(f"\nVERIFICATION FAILED — {len(failures)} problem(s). "
              "Do not ship this catalog until they are resolved.")
        return 1
    print("VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
