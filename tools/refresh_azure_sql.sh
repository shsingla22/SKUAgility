#!/usr/bin/env bash
# Refresh the repository's Azure SQL deliverables from the CurrentAzureSQLSKUInfo
# skill, which reads Microsoft Learn directly. This is the only way the Azure SQL
# files in data/ and docs/ should be produced — there is no hand-maintained copy.
#
#   tools/refresh_azure_sql.sh [extra refresh.py flags]
#
# The skill exits 2 when the parsed inventory differs from its reviewed baseline.
# That is not a failure: it means Azure changed and the diff needs adjudicating
# before the new numbers ship. See the skill's SKILL.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/Skills/AzureSQL/CurrentAzureSQLSKUInfo"
STAGE="$SKILL/output"

python3 "$SKILL/scripts/refresh.py" --out-dir "$STAGE" "$@"
status=$?

if [ $status -ne 0 ] && [ $status -ne 2 ]; then
  echo "refresh failed (exit $status) — repository files left untouched" >&2
  exit $status
fi

cp "$STAGE/azure-sql-sku-table.md" "$ROOT/docs/azure-sql-sku-table.md"
cp "$STAGE/azure-sql-skus.html"    "$ROOT/docs/azure-sql-skus.html"
cp "$STAGE/azure-sql-skus.json"    "$ROOT/data/azure-sql.json"
cp "$STAGE/azure-sql-skus.csv"     "$ROOT/data/azure-sql.csv"

echo
echo "Repository files updated:"
echo "  docs/azure-sql-sku-table.md"
echo "  docs/azure-sql-skus.html"
echo "  data/azure-sql.json"
echo "  data/azure-sql.csv"

if [ $status -eq 2 ]; then
  echo
  echo "NOTE: the inventory differs from the skill's baseline. Review the diff above," >&2
  echo "then re-run with --accept-baseline once each change is sourced." >&2
fi
exit $status
