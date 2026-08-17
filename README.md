# SKUAgility

SKU agility for all workloads.

A catalog of the compute SKUs offered by Azure data services — what exists today, what tier
and hardware family it belongs to, and when it shipped. The first two services covered are
**Azure SQL** (Azure SQL Database + Azure SQL Managed Instance) and
**Azure Database for PostgreSQL**.

## What's here

| Path | Contents |
| --- | --- |
| `Skills/AzureSQL/CurrentAzureSQLSKUInfo/` | **The Azure SQL skill** — reads Microsoft Learn and produces the whole Azure SQL catalog |
| `docs/azure-sql-sku-table.md` | Complete Azure SQL table: every SKU with release date, lifecycle status, source links and doc-sourced recommendation conditions |
| `docs/azure-sql-skus.html` | The Azure SQL SKU Atlas — the same table as a filterable page |
| `docs/azure-postgresql-skus.md` | Human-readable PostgreSQL catalog |
| `data/azure-sql.json`, `data/azure-sql.csv` | Machine-readable Azure SQL catalog + release milestones |
| `data/azure-postgresql.json`, `data/azure-postgresql.csv` | Machine-readable PostgreSQL catalog |
| `tools/refresh_azure_sql.sh` | Runs the skill and copies its output into `docs/` and `data/` |
| `tools/build_catalog.py` | PostgreSQL catalog generator (Azure SQL is the skill's job) |

Regenerate:

```bash
tools/refresh_azure_sql.sh        # Azure SQL — fetches live docs, verifies, rebuilds
python3 tools/build_catalog.py    # PostgreSQL
```

No dependencies beyond the Python 3 standard library. `refresh_azure_sql.sh` needs
outbound HTTPS to Microsoft Learn.

## The Azure SQL skill

Azure SQL is not hand-maintained. `Skills/AzureSQL/CurrentAzureSQLSKUInfo` fetches the
Microsoft Learn article sources, parses the SKU inventory out of them, joins it with a
reviewed set of release milestones and doc-sourced recommendation conditions, and emits
the Markdown table, the Atlas page, JSON and CSV — then verifies the result, including a
liveness check on every cited URL.

Re-running it months from now reports exactly what Azure changed (SKUs added or removed,
values corrected) instead of silently absorbing it. See
[`SKILL.md`](Skills/AzureSQL/CurrentAzureSQLSKUInfo/SKILL.md).

It is symlinked into `.claude/skills/` so Claude Code can invoke it by name.

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
  `Memory (GB)` rows of the resource-limit tables, parsed live from the article source
  by the skill. Managed
  Instance memory is derived from the documented per-vCore ratio with published caps
  applied, since the MI docs publish ratios rather than a per-size table.
- SKU availability is region-dependent. This catalog records what the service offers, not
  what any given region can currently allocate.
- Preview SKUs (Hyperscale premium-series 160/192 vCore, PostgreSQL v6 series) are marked
  `Preview` and dated by their preview announcement.

Sources for every date are listed in [`SOURCES.md`](SOURCES.md), in the skill's
[`references/sources.json`](Skills/AzureSQL/CurrentAzureSQLSKUInfo/references/sources.json),
and inline in the JSON. Catalog as of **2026-08-17**.
