# Sources

Every SKU list and release date in this repo traces back to one of the pages below.
Retrieved 2026-08-17.

## Azure SQL Database — SKU inventory

- [Single database vCore resource limits](https://learn.microsoft.com/azure/azure-sql/database/resource-limits-vcore-single-databases) — the authoritative enumeration of `GP_*`, `BC_*`, `HS_*` service-level objectives per hardware configuration
- [DTU resource limits, single databases](https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-single-databases) — Basic, `S0`–`S12`, `P1`–`P15`
- [DTU resource limits, elastic pools](https://learn.microsoft.com/azure/azure-sql/database/resource-limits-dtu-elastic-pools) — eDTU pool sizes
- [vCore purchasing model](https://learn.microsoft.com/azure/azure-sql/database/service-tiers-sql-database-vcore) — hardware configurations, CPU generations, memory-per-vCore ratios, Fsv2 and Gen4 retirement

## Azure SQL Managed Instance — SKU inventory

- [Resource limits](https://learn.microsoft.com/azure/azure-sql/managed-instance/resource-limits) — vCore grids per hardware generation and service tier, memory ratios, flexible memory
- [vCore purchasing model](https://learn.microsoft.com/azure/azure-sql/managed-instance/service-tiers-managed-instance-vcore) — ARM SKU names (`GP_Gen5`, `GP_G8IM`, `GP_G8IH`, `BC_Gen5`, `BC_G8IM`, `BC_G8IH`) and hardware family identifiers

## Azure Database for PostgreSQL — SKU inventory

- [Compute options](https://learn.microsoft.com/azure/postgresql/compute-storage/concepts-compute) — the full B/D/E series table with vCores, memory, IOPS and throughput
- [What is Azure Database for PostgreSQL flexible server?](https://learn.microsoft.com/azure/postgresql/overview) — v6 SKU family preview status and per-region compute-generation availability
- [What's happening to PostgreSQL single server](https://learn.microsoft.com/azure/postgresql/single-server/whats-happening-to-postgresql-single-server) — retirement of the single server deployment model

## Release dates

### Azure SQL Database

- [New Azure SQL Database service tiers generally available in September](https://azure.microsoft.com/en-us/blog/new-azure-sql-database-service-tiers-generally-available-in-september-with-reduced-pricing-and-enhanced-sla/) — Basic/Standard/Premium GA, September 2014
- [GA: New Azure SQL Database Premium performance level, P15](https://azure.microsoft.com/updates?id=general-availability-new-azure-sql-database-premium-performance-level-p15) — P15, August 2016
- [A flexible new way to purchase Azure SQL Database](https://azure.microsoft.com/en-us/blog/a-flexible-new-way-to-purchase-azure-sql-database/) — vCore model announcement, September 2017
- [Announcing Azure SQL Database Hyperscale public preview](https://azure.microsoft.com/en-us/blog/announcing-azure-sql-database-hyperscale-public-preview/) — Hyperscale preview, October 2018
- [Serverless compute tier](https://learn.microsoft.com/azure/azure-sql/database/serverless-tier-overview) — serverless GA, November 2019
- [What's new archive](https://learn.microsoft.com/azure/azure-sql/database/doc-changes-updates-release-notes-whats-new-archive) — dated entries for the Gen5 rename (2022), 128 vCore preview (2022), Hyperscale premium-series preview (2022), 64 vCore for Hyperscale premium-series (June 2023), 128 vCore GA (June 2023), DC-series 10–40 vCore preview (July 2023) and GA (November 2023), Hyperscale premium-series GA (July 2023), Hyperscale serverless preview (February 2023) and GA (February 2024), Hyperscale elastic pools GA (September 2024)
- [Announcing preview of 160 and 192 vCore premium-series options](https://techcommunity.microsoft.com/blog/azuresqlblog/announcing-preview-of-160-and-192vcore-premium-series-options-for-azure-sql-data/4501367) — March 2026
- [Retirement notice: Fsv2-series](https://azure.microsoft.com/updates?id=485030) — retirement 2026-10-01
- [Support has ended for Gen 4 hardware](https://azure.microsoft.com/updates/support-has-ended-for-gen-4-hardware-on-azure-sql-database/)

### Azure SQL Managed Instance

- [GA of premium-series hardware for Azure SQL Managed Instance](https://techcommunity.microsoft.com/t5/azure-sql-blog/announcing-the-general-availability-of-premium-series-hardware/ba-p/3576737) — July 19, 2022
- [Announcing the new premium-series hardware for SQL Managed Instance](https://techcommunity.microsoft.com/t5/azure-sql-blog/announcing-the-new-premium-series-hardware-for-sql-managed/ba-p/2913496) — preview November 2021; memory optimized premium-series GA September 28, 2022
- [Generally available: Azure SQL Managed Instance Next-gen General Purpose](https://techcommunity.microsoft.com/blog/azuresqlblog/generally-available-azure-sql-managed-instance-next-gen-general-purpose/4470970) — December 2, 2025
- [Introducing Azure SQL Managed Instance Next-gen GP](https://techcommunity.microsoft.com/blog/azuresqlblog/introducing-azure-sql-managed-instance-next-gen-gp/4092647) — preview, May 2024

### Azure Database for PostgreSQL

- [Release notes for flexible server](https://learn.microsoft.com/azure/postgresql/release-notes/release-notes) — dated monthly release history, including v4 compute support (October 2021) and the November 2021 GA
- [Flexible server is now GA](https://techcommunity.microsoft.com/blog/adforpostgresql/azure-database-for-postgresql-%E2%80%93-flexible-server-is-now-ga/2987030) — November 2021
- [Flexible server now supports v4 compute series](https://techcommunity.microsoft.com/blog/adforpostgresql/flexible-server-now-supports-v4-compute-series-in-postgresql-on-azure/2815092) — October 2021
- [GA: New burstable SKUs (B4ms–B20ms)](https://azure.microsoft.com/updates/generally-available-new-burstable-skus-for-azure-database-for-postgresql-flexible-server/) — April 2023
- [Introducing Intel V5 compute and 32 TB storage support](https://techcommunity.microsoft.com/t5/azure-database-for-postgresql/introducing-intel-v5-compute-and-32-tb-storage-support-on-azure/ba-p/3839849) — Ddsv5/Edsv5, May 2023 release, announced June 5, 2023

## Known gaps

These dates could not be pinned to a dated first-party announcement and are marked
`low` confidence in the data files:

- Azure SQL Database `P4` / `P11` GA month (recorded as 2015)
- Azure SQL Database `S4`–`S12` GA month (recorded as 2016)
- Azure SQL Database vCore purchasing model GA month (recorded as 2018-04)
- Azure SQL Database Fsv2-series and DC-series (2–8 vCore) GA months
- Azure SQL Database Gen4 GA year
- Azure Database for PostgreSQL AMD v5 series (`Dadsv5`/`Eadsv5`) GA month (recorded as 2023)
- Azure Database for PostgreSQL single server preview/GA dates
