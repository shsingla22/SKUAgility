---
name: CurrentAzureSQLSKUInfo
description: Produce a current, fully sourced catalog of every Azure SQL SKU — Azure SQL Database and Azure SQL Managed Instance — read live from Microsoft Learn. Each SKU gets its release date, lifecycle status (GA / public preview / deprecated), numbered plain-English conditions for when to recommend it, and links to every Microsoft page the data came from. Outputs a Markdown table and the filterable "Azure SQL SKU Atlas" HTML page. Use when asked for Azure SQL SKUs, SKU release dates, which Azure SQL tier or hardware to pick, what is deprecated or in preview, or to refresh an existing Azure SQL SKU catalog.
---

# CurrentAzureSQLSKUInfo

Builds an Azure SQL SKU catalog from Microsoft's own documentation and hands back
two deliverables:

| Output | What it is |
| --- | --- |
| `azure-sql-sku-table.md` | The full table — one row per SKU, all columns |
| `azure-sql-skus.html` | The **Azure SQL SKU Atlas** — the same data as a filterable page |
| `azure-sql-skus.json` | Machine-readable catalog plus the milestone registry |
| `azure-sql-skus.csv` | Flat table for spreadsheets |

Every row carries: SKU identity (name, deployment model, purchasing model,
service tier, hardware, vCores/DTU, memory), **release date** with a confidence
rating, **lifecycle status**, **numbered conditions for when to recommend it**,
a link to the **doc the SKU data came from**, a link to the **announcement the
date came from**, and links to the **pages the recommendations came from**.

## How to run it

```bash
cd Skills/AzureSQL/CurrentAzureSQLSKUInfo
python3 scripts/refresh.py --out-dir output
```

That runs all five stages: fetch → parse → diff → build → verify. It needs only
the Python 3 standard library and outbound HTTPS.

Useful flags:

| Flag | Use |
| --- | --- |
| `--offline` | Reuse the cached article sources instead of re-fetching |
| `--skip-links` | Skip the URL liveness check (fast iteration only — never for a final answer) |
| `--accept-baseline` | Record the current inventory as the new baseline after reviewing the diff |
| `--as-of YYYY-MM-DD` | Stamp the outputs with a specific date |
| `--out-dir DIR` | Write the deliverables somewhere else |

Exit codes: `0` clean, `1` a stage failed, `2` built and verified but the
inventory changed and needs review.

## What you must do with the result

**The script does the mechanical work. Three things need your judgement.**

### 1. Adjudicate the diff

Stage 3 compares the freshly parsed inventory against `baseline/inventory.json`.
On a re-run months later it will report `ADDED` / `REMOVED` / `CHANGED` lines.
Each one needs a dated Microsoft source before it ships:

- **A new SKU or hardware family** → find the announcement in the what's-new
  articles (already cached as `whats_new_db`, `whats_new_db_archive`,
  `whats_new_mi`, `whats_new_mi_archive`), add a `milestone(...)` entry to
  `references/milestones.py`, and add it to the lookups in `references/rules.py`.
  The build fails loudly on any SKU that matches no rule — that is deliberate,
  because a SKU with a blank date is worse than a failed build.
- **A SKU that disappeared** → check whether it was retired. If Microsoft removed
  it from the resource-limit tables entirely, move it to `RETIRED_FAMILIES` in
  `references/rules.py` rather than deleting it silently.
- **A changed value** (memory, vCores) → confirm against the article; Microsoft
  does correct these.

### 2. Re-check lifecycle status

Lifecycle is not parsed — it comes from prose that moves around. Read the cached
`whats_new_db.md` and `whats_new_mi.md` **Preview** tables and confirm:

- Anything in those Preview tables that maps to a SKU is `Public preview` in
  `references/rules.py`.
- Anything that has since gone GA is moved to `Generally available`, with the GA
  month recorded as a new milestone.
- Retirement notices (search the cached `vcore_model.md` for "retire") are
  reflected in the deprecated status and in `RETIRED_FAMILIES`.

At the time of writing that means: `HS_PRMS_160` / `HS_PRMS_192` are preview, the
the 11 `GP_Fsv2_*` sizes retired on 2026-10-01 (the parser treats that section as
optional, and the family is listed as retired), and Gen4 and
M-series are fully retired and no longer enumerable.

### 3. Read the verification output

Stage 5 must print `VERIFICATION PASSED`. It checks that counts reconcile across
all four outputs, that no SKU is missing a date, status, guidance or source, and
that **every cited URL returns 200**. Microsoft retires Tech Community posts
regularly — dead citations have happened before and are a real defect. If a URL
fails, find the current permalink or replace it with the equivalent Microsoft
Learn what's-new archive entry, then update `references/milestones.py`.

**Do not report results without a passing verification run.**

## Reporting the result

Lead with what the reader needs, not with the process:

1. The two deliverables, with the Atlas linked or attached.
2. The headline counts — total SKUs, and the GA / preview / deprecated split.
3. Anything that changed since the last run, and anything still in preview or
   heading for retirement.
4. The honest limits, below.

If the user wants the Atlas as a shareable page rather than a local file,
publish `azure-sql-skus.html` as an artifact. It is self-contained — inline CSS
and JS, no external requests — so it renders under a strict CSP.

## Honest limits — state these, don't paper over them

- **Release dates are per SKU family, not per size.** Microsoft announces
  families. A size added later than its family carries its own milestone (for
  example the 128 vCore sizes, the DC-series 10–40 vCore sizes, the 160/192
  vCore Hyperscale premium-series options).
- **Some dates are approximate.** `references/milestones.py` grades every date
  `high` / `medium` / `low`. The `low` ones are mostly pre-2019 history whose
  announcement posts are no longer dated on Microsoft's site. They ship flagged,
  never silently rounded into something that looks precise.
- **Managed Instance memory is derived, not transcribed.** The MI docs publish a
  per-vCore ratio and a cap rather than a per-size table, so MI memory is
  computed from those. Azure SQL Database memory is transcribed from the
  published `Memory (GB)` rows — which matters, because those are not linear:
  `HS_PRMS_192` is 843.7 GB, not the ~996 GB a ratio implies.
- **Availability is region-dependent.** The catalog records what the service
  offers, not what any given region can allocate today.
- **Microsoft's own pages sometimes disagree.** Known cases: the vCore purchasing
  model page still caps DC-series at 8 vCores while the resource-limits page
  enumerates 40; the MI Next-gen General Purpose GA date is November 2025 in the
  Learn archive but the GA blog posted 2 December 2025. Record the discrepancy
  and say which source you followed — don't silently pick one.

## Layout

```
CurrentAzureSQLSKUInfo/
├── SKILL.md
├── scripts/
│   ├── refresh.py          orchestrator — run this
│   ├── fetch_docs.py       downloads the Learn article sources
│   ├── parse_inventory.py  extracts the SKU inventory from those sources
│   ├── build_catalog.py    joins inventory + references -> JSON, CSV, Markdown
│   ├── build_artifact.py   renders the Atlas HTML
│   └── verify.py           structural checks + URL liveness
├── references/
│   ├── sources.json        registry of every Microsoft page read, and why
│   ├── milestones.py       release dates, confidence ratings, announcement links
│   ├── rules.py            SKU -> milestone / lifecycle / guidance mapping
│   └── guidance.py         the doc-sourced "when to recommend" conditions
├── baseline/
│   └── inventory.json      last reviewed inventory, for diffing
└── output/                 generated deliverables
```

The parser is anchored on structure the articles guarantee — the "The following
table covers these SLOs: `GP_Gen5_2`, ..." sentences and the `| Memory (GB) |`
rows — so it reads Microsoft's stated SKU names rather than inferring them. If
Microsoft restructures a page, the parser raises rather than returning a short
list.
