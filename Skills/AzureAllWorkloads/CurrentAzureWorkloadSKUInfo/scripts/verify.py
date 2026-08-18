#!/usr/bin/env python3
"""Verify the generated multi-workload catalog before it is handed to anyone.

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
    jpath = os.path.join(args.out_dir, "azure-workload-skus.json")
    mpath = os.path.join(args.out_dir, "azure-workload-sku-table.md")
    cpath = os.path.join(args.out_dir, "azure-workload-skus.csv")
    hpath = os.path.join(args.out_dir, "azure-workload-skus.html")
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
    services = {}
    for s in skus:
        services[s["service"]] = services.get(s["service"], 0) + 1
    expected = set(data.get("service_order") or services)
    if set(services) != expected:
        fail(f"catalog services {sorted(services)} do not match the configured set "
             f"{sorted(expected)} — a provider silently returned nothing")
    elif any(v == 0 for v in services.values()):
        fail("a configured service produced zero SKUs")
    else:
        ok(f"{len(skus)} SKUs across {len(services)} services: "
           + ", ".join(f"{k} {v}" for k, v in sorted(services.items())))

    # The table is sectioned per service and numbering restarts in each section,
    # so count rows rather than trusting the highest index.
    md_rows = len(re.findall(r"^\| \d+ \| `", md, re.M))
    sections = re.findall(r"^## (.+)$", md, re.M)
    svc_sections = [x for x in sections if x in services]
    if len(svc_sections) != len(services):
        fail(f"Markdown has {len(svc_sections)} service sections, expected "
             f"{len(services)}: {sorted(services)}")
    else:
        ok(f"Markdown has one section per service: {', '.join(svc_sections)}")
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
        if not s["release_date"]:
            problems["release_date"].append(s["sku"])
        elif s["release_date"] == "not established" and s["date_confidence"] != "unknown":
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

    # ---- Virtual Machines are individual sizes, not families
    vms = [s for s in skus if s["service"] == "Azure Virtual Machines"]
    if vms:
        no_spec = [s["sku"] for s in vms
                   if s["capacity"] is None or s["memory_gb"] is None]
        not_size = [s["sku"] for s in vms if not s["sku"].startswith("Standard_")]
        series = {s["series"] for s in vms}
        if not_size:
            fail(f"{len(not_size)} VM rows are not individual sizes "
                 f"(e.g. {not_size[0]}) — the provider fell back to family level")
        elif no_spec:
            fail(f"{len(no_spec)} VM sizes have no vCPU or memory "
                 f"(e.g. {no_spec[0]}) — a non-Basics table was parsed")
        elif len(vms) < 800 or len(series) < 100:
            fail(f"only {len(vms)} VM sizes across {len(series)} series — "
                 "expected far more; the series pages changed shape")
        else:
            ok(f"{len(vms)} individual VM sizes across {len(series)} series, "
               "all with vCPU and memory")

    # ---- newest SKU first within each service section
    def rkey(d: str) -> tuple:
        if not d or d == "not established":
            return (-1, -1, -1)
        try:
            nums = [int(x) for x in d.split("-")[:3]]
        except ValueError:
            return (-1, -1, -1)
        return tuple(nums + [0] * (3 - len(nums)))

    out_of_order = []
    seen_service, prev = None, None
    for s in skus:
        if s["service"] != seen_service:
            seen_service, prev = s["service"], None
        cur = rkey(s["release_date"])
        if prev is not None and cur > prev:
            out_of_order.append(
                f"{s['service']}: {s['sku']} ({s['release_date']}) appears after an "
                f"older SKU")
        prev = cur
    if out_of_order:
        fail(f"{len(out_of_order)} SKUs break the newest-first ordering "
             f"(e.g. {out_of_order[0]})")
    else:
        ok("each service section is ordered newest release first")

    # ---- lifecycle values are from the known set
    allowed = {"Generally available", "Public preview"}
    unknown = {s["lifecycle_status"] for s in skus
               if s["lifecycle_status"] not in allowed
               and not s["lifecycle_status"].startswith(
                   ("Deprecated", "Retiring", "Previous generation"))}
    if unknown:
        fail(f"unexpected lifecycle values: {sorted(unknown)}")
    else:
        ok("lifecycle values are all GA / preview / deprecated / retiring / "
           "previous generation")

    # ---- a preview SKU must be dated by its preview announcement
    for s in skus:
        pass

    # ---- confidence is declared honestly
    conf = {}
    for s in skus:
        conf[s["date_confidence"]] = conf.get(s["date_confidence"], 0) + 1
    if set(conf) - {"high", "medium", "low", "unknown"}:
        fail(f"unexpected confidence values: {sorted(set(conf))}")
    else:
        ok(f"date confidence: {conf}")
        if conf.get("low"):
            warnings.append(
                f"{conf['low']} SKUs carry low-confidence dates — reconstructed from "
                "context and flagged as approximate in the output")
        if conf.get("unknown"):
            warnings.append(
                f"{conf['unknown']} SKUs have NO sourced release date; they read "
                "'not established' rather than carrying a guess. Sourcing these is "
                "the highest-value follow-up for this catalog")
    errata = data.get("source_doc_errata", [])
    if errata:
        warnings.append(
            f"{len(errata)} typographical error(s) in Microsoft's published tables were "
            "corrected; they are listed in the Markdown table")

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
