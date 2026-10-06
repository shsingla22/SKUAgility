# SKUAgility

SKU agility for all workloads.

A catalog of the compute SKUs offered by Azure data services — what exists today, what tier
and hardware family it belongs to, when it shipped, whether it is still a good idea, and
where every one of those claims came from. Built from Microsoft documentation by two
reusable skills. **1,519 SKUs across Azure SQL, Azure Database for PostgreSQL, Azure Database for MySQL,
Azure DocumentDB (MongoDB-compatible) and Azure Virtual Machines** by default; three more
services ship switched off behind a config flag.

## What's here

| Path | Contents |
| --- | --- |
| `Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo/` | **The all-workloads skill** — one catalog spanning every covered Azure service |
| `Skills/AzureSQL/CurrentAzureSQLSKUInfo/` | **The Azure SQL skill** — the deep Azure SQL catalog, also consumed by the skill above |
| `docs/azure-workload-sku-table.md` | Cross-workload table: every SKU, release date, lifecycle, guidance, sources |
| `docs/azure-workload-skus.html` | The Azure Workload SKU Atlas — the same table as a filterable page |
| `docs/azure-sql-sku-table.md` | Complete Azure SQL table: every SKU with release date, lifecycle status, source links and doc-sourced recommendation conditions |
| `docs/azure-sql-skus.html` | The Azure SQL SKU Atlas — the same table as a filterable page |
| `docs/azure-postgresql-skus.md` | Human-readable PostgreSQL catalog |
| `data/azure-sql.json`, `data/azure-sql.csv` | Machine-readable Azure SQL catalog + release milestones |
| `data/azure-postgresql.json`, `data/azure-postgresql.csv` | Machine-readable PostgreSQL catalog |
| `data/azure-workloads.json`, `data/azure-workloads.csv` | Machine-readable cross-workload catalog |
| `tools/refresh_all_workloads.sh` | Runs the all-workloads skill into `docs/` and `data/` |
| `Skills/.../references/config.json` | **Which Azure services the catalog covers** |
| `tools/refresh_azure_sql.sh` | Runs the Azure SQL skill into `docs/` and `data/` |
| `tools/build_catalog.py` | PostgreSQL catalog generator (Azure SQL is the skill's job) |

Regenerate:

```bash
tools/refresh_all_workloads.sh    # every covered service — fetches live docs, verifies
tools/refresh_azure_sql.sh        # Azure SQL only, in more depth
python3 tools/build_catalog.py    # the standalone PostgreSQL catalog
```

No dependencies beyond the Python 3 standard library. `refresh_azure_sql.sh` needs
outbound HTTPS to Microsoft Learn.

## The skills

Nothing in the Azure catalog is hand-maintained. Two skills read Microsoft's documentation
and generate everything, then verify what they produced:

| Skill | Covers | Granularity |
| --- | --- | --- |
| `CurrentAzureWorkloadSKUInfo` | A **configurable** set of services — SQL, PostgreSQL, MySQL, DocumentDB (MongoDB) and Virtual Machines on by default; Cache for Redis, App Service and AKS available | Per individual size |
| `CurrentAzureSQLSKUInfo` | Azure SQL Database + Managed Instance | Every service-level objective |

Which services the cross-workload catalog covers is set in
[`references/config.json`](Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo/references/config.json)
— flip an `enabled` flag, or override one run with `--services postgresql,redis` or
`--services all`. The output is sectioned per service, newest SKUs first, with a contents
index; in the Atlas each service section folds shut so the whole catalog can be skimmed at
service level.

The all-workloads skill delegates Azure SQL to the SQL skill rather than re-deriving it, so
there is one source of truth per service. Both are symlinked into `.claude/skills/` so
Claude Code can invoke them by name, and both report what changed since their last reviewed
baseline instead of silently absorbing it.

Adding a service to the cross-workload catalog is three edits — a source, a set of release
milestones, and a provider module — described in the
[skill's SKILL.md](Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo/SKILL.md).

### Notable current findings

- **Azure SQL Fsv2-series retired on 2026-10-01.** Its 11 sizes are gone from Microsoft's
  resource-limits article and so from this catalog; the family is recorded in the Azure SQL
  table's *Retired and deprecated hardware families* section.
- **Four typos in Microsoft's published PostgreSQL compute table** are corrected explicitly
  and listed in the output rather than repeated or silently dropped.
- **Azure Virtual Machines are enumerated per size** — 1,058 sizes across 137 series, read
  from each series' own "Sizes in series" table, with vCPU and memory for every one.
- **Azure SQL and PostgreSQL are fully dated.** About 60% of VM sizes carry a dated GA
  announcement; the rest read *not established* rather than carrying a guess, and every run
  counts them.
- If you enable Redis: **every Azure Cache for Redis tier is retiring.** Enterprise and
  Enterprise Flash on 2027-03-31, Basic/Standard/Premium on 2028-09-30, with creation
  already blocked for new customers since 2026-04-01. Microsoft directs new work to Azure
  Managed Redis.
- **Azure Migrate SKU support comparison.** Every service section now opens with two
  call-outs — **GA SKU discrepancies** and **Public preview SKU discrepancies** — comparing
  this catalog's SKUs against Azure Migrate's supported SKU list for that service. Both report
  every SKU in their bucket, flagging a GA or preview SKU Migrate doesn't support and a
  deprecated SKU it still does. Currently sourced for **PostgreSQL only** (a user-supplied
  document, `references/migrate_support.json`): all 71 GA PostgreSQL SKUs match Migrate's list
  exactly (zero flags), but all **38 public-preview v6 SKUs are flagged** — Migrate's list
  predates the v6 preview. **MySQL** (user-supplied document, 2026-10-05): **25 of the 49 GA
  SKUs are not Migrate-supported** — every v5 size (`*ads_v5` / `*ds_v5`) plus `E64ds_v4` —
  and Migrate's list names `Standard_E96ds_v5`, which Microsoft's MySQL service-tiers page
  does not offer. **MongoDB / Azure DocumentDB** (user-supplied document, 2026-10-05): Migrate
  supports all nine cluster tiers M10–M200 — with its own SKU names and a Dev/Test (M10–M30) vs
  Production (M40–M200) classification, and its vCore/RAM figures agree with Azure's page for
  every one — but **not the Free Tier**, the one flag. **Azure SQL Managed Instance** (user-supplied
  document, 2026-10-06): Migrate's tier x hardware x vCore grid covers 104 of the 106 sizes; the two
  it misses are the 2-vCore General Purpose sizes (standard-series and premium-series), which Azure
  offers only inside instance pools. Azure SQL Database and Virtual Machines show "not supplied
  yet" until their own Migrate data is added.
- **MongoDB on Azure is Azure DocumentDB now.** Microsoft renamed Azure Cosmos DB for MongoDB
  (vCore) to Azure DocumentDB (with MongoDB compatibility) on 2025-11-18. The catalog carries
  its nine cluster tiers (M10–M200) plus the Free Tier, all GA; M10/M20 are dated to their
  March 2025 launch and M25 to November 2023. One doc inconsistency is recorded: the M10/M20
  announcement calls them dedicated compute, the current compute page lists them as burstable.
- **80 VM sizes across 11 series are End of Life** per Microsoft's End of Life size-series
  list (Dv2/Dsv2, Dv3/Dsv3, Ev3/Esv3, Fsv2, Lsv2, DCsv3/DCdsv3, HC, HBv2): retirement
  announced, still usable until the date, restricted for new subscriptions.

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

**Azure DocumentDB (MongoDB-compatible)** — cluster tiers M10, M20, M25 (burstable vCores) and
M30–M200, plus the Free Tier. The RU-based Azure Cosmos DB for MongoDB has no compute sizes
and is not covered.

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
and inline in the JSON. Catalog as of **2026-10-05**.
