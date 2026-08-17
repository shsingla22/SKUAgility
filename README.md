# SKUAgility

SKU agility for all workloads.

A catalog of the compute SKUs offered by Azure data services — what exists today, what tier
and hardware family it belongs to, and when it shipped. The first two services covered are
**Azure SQL** (Azure SQL Database + Azure SQL Managed Instance) and
**Azure Database for PostgreSQL**.

## What's here

| Path | Contents |
| --- | --- |
| `docs/azure-sql-sku-table.md` | **Complete Azure SQL table** — every SKU with release date, lifecycle status, source links and doc-sourced recommendation conditions |
| `docs/azure-sql-skus.md` | Azure SQL catalog grouped by tier and hardware |
| `docs/azure-postgresql-skus.md` | Human-readable PostgreSQL catalog |
| `data/azure-sql.json` | Machine-readable Azure SQL catalog + release milestones |
| `data/azure-postgresql.json` | Machine-readable PostgreSQL catalog + release milestones |
| `data/skus.csv` | Flat join of every SKU across both services |
| `tools/build_catalog.py` | Source of truth; regenerates everything above |
| `tools/guidance.py` | Doc-sourced "when to recommend" conditions per SKU family |

Regenerate after editing `tools/build_catalog.py`:

```bash
python3 tools/build_catalog.py
```

No dependencies beyond the Python 3 standard library.

## Coverage

**Azure SQL Database** — DTU purchasing model (Basic, Standard `S0`–`S12`, Premium `P1`–`P15`,
plus Basic/Standard/Premium elastic pools) and vCore purchasing model (General Purpose,
Business Critical, Hyperscale × provisioned and serverless × standard-series (Gen5),
Fsv2-series, DC-series, premium-series, premium-series memory optimized).

**Azure SQL Managed Instance** — General Purpose, Next-gen General Purpose and Business
Critical on standard-series (Gen5), premium-series (`G8IM`) and memory optimized
premium-series (`G8IH`).

**Azure Database for PostgreSQL** — flexible server Burstable, General Purpose and Memory
Optimized tiers across the v3, v4, v5 (Intel and AMD) and v6 (preview) compute series. The
retired single server SKUs are included, flagged `Retired`, for historical reference.

## Release dates

Every SKU is tagged with a *release milestone* — the announcement that made it orderable —
rather than an invented per-SKU date, because Microsoft ships SKUs in families. Each
milestone carries a preview date, a GA date, a source link and a confidence rating:

| Confidence | Meaning |
| --- | --- |
| `high` | A dated Microsoft announcement or release note names this exact change |
| `medium` | A Microsoft page dates the change to a month, or a reputable secondary source corroborates a first-party announcement |
| `low` | Reconstructed from context — treat the date as approximate |

The `low` entries are mostly pre-2019 Azure SQL history, where the original announcement
posts are no longer dated on Microsoft's site. They are flagged rather than dropped so the
gap is visible.

## Lifecycle status

Every Azure SQL SKU carries a lifecycle status read from the current Microsoft docs:

| Status | Count | What it covers |
| --- | --- | --- |
| Generally available | 291 | Orderable, fully supported |
| Deprecated - cannot be created; retires 2026-10-01 | 11 | The Fsv2-series sizes |
| Public preview | 2 | `HS_PRMS_160` and `HS_PRMS_192` |

Gen4 and M-series are fully retired and no longer enumerable from Microsoft docs; they are
recorded at family level in the table's *Retired and deprecated hardware families* section.

## Recommendation conditions

Each Azure SQL SKU carries a numbered list of plain-English conditions for when to
recommend it, paraphrased from Microsoft Learn — the purchasing-model comparison, the
service-tier "when to choose" sections, the serverless scenarios guidance, and the
resource-limit pages. Every list ships with the links it came from. Nothing is inferred
from third-party sources.

## Caveats

- Memory for every Azure SQL Database vCore SKU is transcribed from the published
  `Memory (GB)` rows of the resource-limit tables (`tools/sqldb_memory.json`). Managed
  Instance memory is derived from the documented per-vCore ratio with published caps
  applied, since the MI docs publish ratios rather than a per-size table.
- SKU availability is region-dependent. This catalog records what the service offers, not
  what any given region can currently allocate.
- Preview SKUs (Hyperscale premium-series 160/192 vCore, PostgreSQL v6 series) are marked
  `Preview` and dated by their preview announcement.

Sources for every date are listed in [`SOURCES.md`](SOURCES.md) and inline in the JSON.
Catalog as of **2026-08-17**.
