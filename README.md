# SKUAgility

SKU agility for all workloads.

A catalog of the compute SKUs offered by Azure data services — what exists today, what tier
and hardware family it belongs to, and when it shipped. The first two services covered are
**Azure SQL** (Azure SQL Database + Azure SQL Managed Instance) and
**Azure Database for PostgreSQL**.

## What's here

| Path | Contents |
| --- | --- |
| `docs/azure-sql-skus.md` | Human-readable Azure SQL catalog |
| `docs/azure-postgresql-skus.md` | Human-readable PostgreSQL catalog |
| `data/azure-sql.json` | Machine-readable Azure SQL catalog + release milestones |
| `data/azure-postgresql.json` | Machine-readable PostgreSQL catalog + release milestones |
| `data/skus.csv` | Flat join of every SKU across both services |
| `tools/build_catalog.py` | Source of truth; regenerates everything above |

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

## Caveats

- Memory figures for the Azure SQL vCore model are derived from the published per-vCore
  ratio with documented caps applied, not transcribed row by row.
- SKU availability is region-dependent. This catalog records what the service offers, not
  what any given region can currently allocate.
- Preview SKUs (Hyperscale premium-series 160/192 vCore, PostgreSQL v6 series) are marked
  `Preview` and dated by their preview announcement.

Sources for every date are listed in [`SOURCES.md`](SOURCES.md) and inline in the JSON.
Catalog as of **2026-08-17**.
