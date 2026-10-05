---
name: CurrentAzureWorkloadSKUInfo
description: Produce a current, fully sourced SKU catalog for a configurable set of Azure services — Azure SQL, Azure Database for PostgreSQL, Azure Database for MySQL, Azure DocumentDB (MongoDB-compatible) and Azure Virtual Machines by default, with Cache for Redis, App Service and Kubernetes Service available by flipping a flag. Output is sectioned per service with the newest SKUs first and collapsible sections in the Atlas, and every SKU gets its release date, lifecycle status (GA / public preview / deprecated / retiring), numbered plain-English conditions for when to recommend it taken from Microsoft's own guidance, and links to every page the data came from. Outputs a Markdown table and the filterable "Azure Workload SKU Atlas" HTML page. Use when asked for Azure SKUs for one or more services, which Azure tier or size to pick for a workload, what is deprecated, retiring or in preview, or to refresh an existing Azure SKU catalog.
---

# CurrentAzureWorkloadSKUInfo

Builds an Azure SKU catalog from Microsoft's documentation, for whichever
services it is configured to cover, and hands back:

| Output | What it is |
| --- | --- |
| `azure-workload-sku-table.md` | The full table, **one section per Azure service, newest SKUs first**, with a contents index |
| `azure-workload-skus.html` | The **Azure Workload SKU Atlas** — filterable page |
| `azure-workload-skus.json` | Machine-readable catalog + milestones + errata |
| `azure-workload-skus.csv` | Flat table for spreadsheets |

Every row carries: SKU identity (name, service, tier, series/family, size,
memory), **release date** with a confidence rating, **lifecycle status**,
**numbered conditions for when to recommend it**, a link to the **doc the SKU
data came from**, a link to the **release announcement**, and links to the
**pages the recommendations came from**.

## Choosing which services to cover

The target services are configuration, not code. `references/config.json` lists
every implemented service with an `enabled` flag:

```json
{ "key": "azure_sql",  "display": "Azure SQL (Database + Managed Instance)", "enabled": true  },
{ "key": "postgresql", "display": "Azure Database for PostgreSQL",           "enabled": true  },
{ "key": "virtual_machines", "display": "Azure Virtual Machines",             "enabled": true  },
{ "key": "mysql",      "display": "Azure Database for MySQL",                "enabled": false },
{ "key": "redis",      "display": "Azure Cache for Redis",                   "enabled": false },
{ "key": "app_service","display": "Azure App Service",                       "enabled": false },
{ "key": "aks",        "display": "Azure Kubernetes Service",                "enabled": false }
```

**Azure SQL, Azure Database for PostgreSQL and Azure Virtual Machines are
enabled by default.** The
others are fully implemented and verified — flip `enabled` to `true` to include
one. Everything follows this file: only enabled services are fetched, only they
appear in the table, and verification checks exactly that set.

Override for a single run without editing the file:

```bash
python3 scripts/refresh.py --services postgresql,redis
python3 scripts/refresh.py --services all
```

An unknown key is rejected with the list of valid ones rather than silently
producing a smaller catalog.

## How to run it

```bash
cd Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo
python3 scripts/refresh.py --out-dir output
```

Four stages: fetch → build → diff → verify. Standard library only, plus
outbound HTTPS.

| Flag | Use |
| --- | --- |
| `--services LIST` | Override the config for this run: keys, or `all` |
| `--offline` | Reuse cached documentation instead of re-fetching |
| `--skip-links` | Skip the URL liveness check (iteration only, never for a final answer) |
| `--accept-baseline` | Record the current catalog as the baseline after reviewing the diff |
| `--as-of YYYY-MM-DD` | Stamp the outputs with a specific date |

Exit codes: `0` clean, `1` a stage failed, `2` verified but the catalog moved
and needs review.

## Ordering

Within each service section the newest SKUs come first, by release date. The
ordering is applied once in `build_catalog.order_rows`, before anything is
written, so the Markdown table, the CSV, the JSON and the Atlas all present the
same order — and `verify.py` asserts it on every run.

Three details worth knowing when reading a section:

1. Dates arrive at whatever precision Microsoft published — `2025-11-14`,
   `2025-11` or a bare `2025`. A coarser date sorts as the start of its period,
   so `2016-08` ranks above a bare `2016`.
2. SKUs sharing a release date keep the order their provider produced them in,
   which is Microsoft's own documentation order. The sort is stable, so this is
   deterministic run to run.
3. SKUs whose date could not be sourced (`not established`) collect at the
   **bottom** of their section rather than the top, so an unsourced date never
   masquerades as recent news.

## Coverage, and where it stops

| Service | Default | Granularity | Source |
| --- | --- | --- | --- |
| Azure SQL Database / Managed Instance | **on** | Every service-level objective | Delegated to the `CurrentAzureSQLSKUInfo` skill |
| Azure Database for PostgreSQL | **on** | Every compute size | Compute-options page |
| Azure Database for MySQL | **on** | Every compute size | Service-tiers page |
| Azure DocumentDB (MongoDB-compatible) | **on** | Every cluster tier + the Free Tier | Compute-and-storage, free-tier and release-notes pages |
| Azure Cache for Redis | off | Tier | Overview + what's-new |
| Azure App Service | off | Plan tier | Hosting-plans page |
| Azure Kubernetes Service | off | Pricing tier | Pricing-tiers page |
| Azure Virtual Machines | **on** | **Every individual size** (~1,058 across ~137 series) | Sizes overview -> family pages -> series pages |

Two deliberate boundaries, both worth stating when you report results:

- **Virtual Machines are enumerated per size.** The provider crawls the sizes
  overview to the family pages, then to each of the ~131 series pages, and reads
  the "Sizes in series" **Basics** table on each one. Only that table is read:
  the Local Storage, Remote Storage, Network and Accelerator tables on the same
  page repeat the size names with different columns, and on some pages in a
  different name form entirely (HBv5 lists `Standard_HB368-336rs_v5` in Basics
  but `Standard_HB368_336rsv5` in the storage tables), so matching every "Size
  Name" table invents sizes and reads a disk count as a vCPU count.
- **Azure SQL is delegated, not re-derived.** `providers/azure_sql.py` runs the
  sibling skill and adopts its output, milestones included. One source of truth
  for Azure SQL; if that skill is missing the provider fails loudly rather than
  quietly shipping a catalog with no Azure SQL in it.

## Azure Migrate SKU support comparison

Every service section opens with **two** call-outs, right at the top, above the
SKU table: **GA SKU discrepancies** and **Public preview SKU discrepancies**.
Each compares this catalog's SKUs for that service against a separately-supplied
list of the SKUs Azure Migrate's discovery-and-assessment tooling recognizes.

Three things are flagged, because they are the three ways the two lists can
disagree in a way that matters operationally:

1. A SKU Azure has **GA** that Migrate does **not** support — recommending it
   blocks a Migrate-based migration. *(GA SKU discrepancies)*
2. A SKU Azure has in **public preview** that Migrate does **not** support —
   the same problem, one release stage earlier. *(Public preview SKU
   discrepancies)*
3. A SKU Azure has **deprecated or retiring** that Migrate **still**
   supports — Migrate may point a migration at something Azure is already
   walking back. *(nested under GA SKU discrepancies, since it's the other
   non-preview lifecycle state)*

Both sections report **every** SKU in their bucket, not just the disagreements —
a clean bucket (nothing flagged) still states its totals and lists every SKU
with a Yes/No Migrate-support column, rather than being collapsed to a "no
issues" sentence. A bucket with zero SKUs (e.g. no deprecated PostgreSQL SKUs
today) still states that plainly instead of being omitted.

The Migrate-supported list is not fetched from a Microsoft doc; it comes from
whatever source the user supplies, recorded per workload in
`references/migrate_support.json` alongside where it came from and as of when.
A workload with no entry there gets an honest "comparison data has not been
supplied for this service yet" line in both sections instead of an omitted
block — the two call-outs always appear, even before a service's data exists.

`references/migrate_support.py` does the comparison, bucketing every SKU by
lifecycle status (`ga` / `deprecated` / `preview`) and tagging each with
`migrate_supported` and `flagged`. `build_catalog.py` renders the two Markdown
sections from it; `build_artifact.py` carries the same buckets into the JSON so
the Atlas renders two banners per section (folding shut with the rest of the
section). `verify.py` recomputes every bucket's totals and flagged set
independently from `migrate_support.json` and the catalog itself, so a bug in
the comparison module can't ship unnoticed.

To add Migrate-support data for another service: add an entry to
`references/migrate_support.json` keyed by that service's `WORKLOAD` string
(the same key used in `references/config.json`), naming its `source`, `as_of`
date and `supported_skus` list using this catalog's own SKU names (`sku` field,
e.g. `Standard_D4ds_v5`) — no other code changes are needed. Do note: a full
per-SKU table means a service with a very large GA bucket (Virtual Machines'
~965 sizes, say) would render a very long table if given Migrate data — worth
reconsidering paging or a summary-only mode before extending this to VMs.

## Adding a service

Four edits, no framework changes:

1. Add the page(s) to `references/sources.json` with a `strategy` — `raw` for a
   GitHub-hosted article source, `learn` for the rendered page where the source
   repository is not publicly mirrored.
2. Add release milestones to `references/milestones.py`. If you cannot source a
   date, set `confidence="unknown"` — never invent a month.
3. Write `providers/<name>.py` exposing `WORKLOAD`, `SERVICE`, `SOURCES` and
   `collect(docs) -> list[Sku]`.
4. Add an entry to `references/config.json` so it can be switched on.

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
would be worse than a gap. Verification counts them every run.

Azure SQL and PostgreSQL are fully dated. Virtual Machines are dated per series
generation in `references/vm_milestones.py`: roughly 60% of sizes carry a dated
Microsoft GA announcement, and the rest - mostly the specialised M, N, L, H and
Fx series - read *not established*.

Closing those gaps is mechanical and is the highest-value follow-up: find the
"Announcing ... generally available" post for the generation, add a block to
`vm_milestones.py` with its series prefixes, and every size in those series
inherits the date. Do not infer a date from a neighbouring generation. Finding a
dated Microsoft announcement for any of these is the highest-value improvement
to this catalog.

### 3. Re-check lifecycle and retirement

Lifecycle is not fully parseable — it lives in prose. Re-read the cached
what's-new pages each run. With the default set, the standout is that the 11
Azure SQL **Fsv2-series** SKUs retired on 2026-10-01 and dropped out of the catalog
when Microsoft removed their section. If Redis is
enabled, note that **every Azure Cache for Redis tier is on a retirement path**: Enterprise and Enterprise
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

### 5. Keep Migrate-support data current

`references/migrate_support.json` is a snapshot of what Azure Migrate supported
as of the date it names — it does not refresh itself the way the rest of the
catalog does, because there is no Microsoft doc URL to fetch it from. When the
user supplies an updated list (a newer document, a different service), replace
the workload's entry and re-run; the comparison and both outputs pick it up
automatically. Currently **PostgreSQL** and **MySQL** have entries — every other
service's section will keep reading "not supplied yet" until one is added.

## Reporting the result

1. The deliverables, with the Atlas linked or attached.
2. Headline counts per service — the table is sectioned per service, so report
   it that way — plus the overall GA / preview / deprecated / retiring split.
   The top of each section is the newest thing Azure shipped for that service,
   which is usually the most useful sentence you can write about it.
3. Anything retiring or in preview — that is what changes decisions.
4. Any Azure Migrate SKU support flags, per service — a GA or preview SKU
   Migrate doesn't support, or a deprecated one it still does. Zero flags in a
   bucket is itself worth saying plainly rather than skipping.
5. The honest gaps: how many dates are *not established*, and the coverage
   boundaries above.

Publish `azure-workload-skus.html` as an artifact if the user wants a shareable
page; it is self-contained and renders under a strict CSP. Each service section
on that page folds shut — click the section header, or use *Collapse all* — so a
reader can skim the whole catalog at service level and open only what they need.

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
│   ├── __init__.py        the registry, driven by references/config.json
│   ├── common.py          the shared Sku record and helpers
│   └── <workload>.py      one module per service
├── references/
│   ├── config.json        WHICH SERVICES TO COVER — edit this first
│   ├── sources.json       every page read, its strategy, and why
│   ├── milestones.py      release dates, confidence ratings, retirement dates
│   ├── migrate_support.json  Migrate-supported SKUs per workload, as supplied
│   └── migrate_support.py    the comparison: GA-unsupported / deprecated-supported
├── baseline/inventory.json
└── output/
```
