---
name: CurrentAzureWorkloadSKUInfo
description: Produce a current, fully sourced SKU catalog spanning Azure's major workload services — Azure SQL Database and Managed Instance, Azure Database for PostgreSQL and MySQL, Azure Cache for Redis, Azure App Service, Azure Kubernetes Service and Azure Virtual Machines. Every SKU gets its release date, lifecycle status (GA / public preview / deprecated / retiring), numbered plain-English conditions for when to recommend it taken from Microsoft's own guidance, and links to every page the data came from. Outputs a Markdown table and the filterable "Azure Workload SKU Atlas" HTML page. Use when asked for Azure SKUs across services, which Azure tier or size to pick for a workload, what is deprecated, retiring or in preview across Azure, or to refresh an existing Azure SKU catalog.
---

# CurrentAzureWorkloadSKUInfo

Builds a cross-service Azure SKU catalog from Microsoft's documentation and
hands back:

| Output | What it is |
| --- | --- |
| `azure-workload-sku-table.md` | The full table — one row per SKU, all columns |
| `azure-workload-skus.html` | The **Azure Workload SKU Atlas** — filterable page |
| `azure-workload-skus.json` | Machine-readable catalog + milestones + errata |
| `azure-workload-skus.csv` | Flat table for spreadsheets |

Every row carries: SKU identity (name, service, tier, series/family, size,
memory), **release date** with a confidence rating, **lifecycle status**,
**numbered conditions for when to recommend it**, a link to the **doc the SKU
data came from**, a link to the **release announcement**, and links to the
**pages the recommendations came from**.

## How to run it

```bash
cd Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo
python3 scripts/refresh.py --out-dir output
```

Four stages: fetch → build → diff → verify. Standard library only, plus
outbound HTTPS.

| Flag | Use |
| --- | --- |
| `--workload NAME` | Build one workload only (`postgresql`, `redis`, …) |
| `--offline` | Reuse cached documentation instead of re-fetching |
| `--skip-links` | Skip the URL liveness check (iteration only, never for a final answer) |
| `--accept-baseline` | Record the current catalog as the baseline after reviewing the diff |
| `--as-of YYYY-MM-DD` | Stamp the outputs with a specific date |

Exit codes: `0` clean, `1` a stage failed, `2` verified but the catalog moved
and needs review.

## Coverage, and where it stops

| Workload | Granularity | Source |
| --- | --- | --- |
| Azure SQL Database / Managed Instance | Every service-level objective | Delegated to the `CurrentAzureSQLSKUInfo` skill |
| Azure Database for PostgreSQL | Every compute size | Compute-options page |
| Azure Database for MySQL | Every compute size | Service-tiers page |
| Azure Cache for Redis | Tier | Overview + what's-new |
| Azure App Service | Plan tier | Hosting-plans page |
| Azure Kubernetes Service | Pricing tier | Pricing-tiers page |
| Azure Virtual Machines | **Size family, not size** | Sizes overview |

Two deliberate boundaries, both worth stating when you report results:

- **Virtual Machines are family-level.** Azure documents roughly 800 individual
  sizes across more than a hundred pages, and the authoritative per-size list is
  the Resource SKUs API, which needs a subscription and credentials. Family
  level is what the documentation states cleanly in one place and is the level
  at which "which VM should I use" is actually answered.
- **Azure SQL is delegated, not re-derived.** `providers/azure_sql.py` runs the
  sibling skill and adopts its output, milestones included. One source of truth
  for Azure SQL; if that skill is missing the provider fails loudly rather than
  quietly shipping a catalog with no Azure SQL in it.

## Adding a workload

Three edits, no framework changes:

1. Add the page(s) to `references/sources.json` with a `strategy` — `raw` for a
   GitHub-hosted article source, `learn` for the rendered page where the source
   repository is not publicly mirrored.
2. Add release milestones to `references/milestones.py`. If you cannot source a
   date, set `confidence="unknown"` — never invent a month.
3. Write `providers/<name>.py` exposing `WORKLOAD`, `SERVICE`, `SOURCES` and
   `collect(docs) -> list[Sku]`, and add it to `PROVIDERS` in
   `providers/__init__.py`.

A provider that cannot find its expected table **must raise**. A silently
shrinking catalog is the failure mode worth guarding hardest against, which is
why every provider ends with a sanity check on how many rows it produced.

## What needs your judgement

**The script does the mechanical work. Four things do not automate.**

### 1. Adjudicate the diff

Stage 3 compares against `baseline/inventory.json` and reports `ADDED` /
`REMOVED` / `CHANGED`. Each change needs a dated Microsoft source before it
ships — a new SKU needs a milestone, a lifecycle move needs the announcement
that declared it.

### 2. Source the missing release dates

Some milestones ship with `confidence="unknown"` and a release date of
*not established*. That is deliberate: no date could be sourced, and a guess
would be worse than a gap. Verification counts them every run. Currently
unsourced: the older App Service tiers, the AKS tiers, the original Redis
Basic/Standard/Premium GA, and VM families (where a single family-level date is
not meaningful). Finding a dated Microsoft announcement for any of these is the
highest-value improvement to this catalog.

### 3. Re-check lifecycle and retirement

Lifecycle is not fully parseable — it lives in prose. Re-read the cached
what's-new pages each run. As of this writing the standout is that **every
Azure Cache for Redis tier is on a retirement path**: Enterprise and Enterprise
Flash retire 2027-03-31, Basic/Standard/Premium retire 2028-09-30, creation was
blocked for new customers on 2026-04-01, and Microsoft directs new work to Azure
Managed Redis. That dominates the recommendation for all five Redis SKUs and
should be led with, not buried.

### 4. Review the errata

Providers may carry an `ERRATA` map correcting typographical errors in
Microsoft's published tables. These are applied explicitly and listed in the
output. The PostgreSQL compute table currently has four (an AMD SKU name
repeating the Intel one twice, a `D`-series name in a Memory Optimized row, and
a `v4` suffix in a `v5` row). On each refresh, check whether Microsoft has fixed
them — a correction that is no longer needed should be removed, not left to
silently rewrite correct data.

## Reporting the result

1. The deliverables, with the Atlas linked or attached.
2. Headline counts: total SKUs, services covered, and the GA / preview /
   deprecated / retiring split.
3. Anything retiring or in preview — that is what changes decisions.
4. The honest gaps: how many dates are *not established*, and the coverage
   boundaries above.

Publish `azure-workload-skus.html` as an artifact if the user wants a shareable
page; it is self-contained and renders under a strict CSP.

**Do not report results without a passing verification run**, which includes
checking that every cited URL still resolves. Microsoft retires announcement
posts regularly.

## Layout

```
CurrentAzureWorkloadSKUInfo/
├── SKILL.md
├── scripts/
│   ├── refresh.py         orchestrator — run this
│   ├── fetch_docs.py      downloads every declared source
│   ├── docsource.py       fetch strategies + the shared Doc/Section/Table model
│   ├── build_catalog.py   runs every provider -> JSON, CSV, Markdown
│   ├── build_artifact.py  renders the Atlas HTML
│   └── verify.py          structural checks + URL liveness
├── providers/
│   ├── __init__.py        the registry
│   ├── common.py          the shared Sku record and helpers
│   └── <workload>.py      one module per service
├── references/
│   ├── sources.json       every page read, its strategy, and why
│   └── milestones.py      release dates, confidence ratings, retirement dates
├── baseline/inventory.json
└── output/
```
