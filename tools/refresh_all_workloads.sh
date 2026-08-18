#!/usr/bin/env bash
# Refresh the repository's cross-workload catalog from the CurrentAzureWorkloadSKUInfo
# skill, which reads Microsoft documentation directly. There is no hand-maintained copy.
#
#   tools/refresh_all_workloads.sh [extra refresh.py flags]
#
# Exit 2 means the catalog differs from the skill's reviewed baseline: not a failure,
# but the diff needs adjudicating before the new numbers ship. See the skill's SKILL.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$ROOT/Skills/AzureAllWorkloads/CurrentAzureWorkloadSKUInfo"
STAGE="$SKILL/output"

python3 "$SKILL/scripts/refresh.py" --out-dir "$STAGE" "$@"
status=$?

if [ $status -ne 0 ] && [ $status -ne 2 ]; then
  echo "refresh failed (exit $status) — repository files left untouched" >&2
  exit $status
fi

cp "$STAGE/azure-workload-sku-table.md" "$ROOT/docs/azure-workload-sku-table.md"
cp "$STAGE/azure-workload-skus.html"    "$ROOT/docs/azure-workload-skus.html"
cp "$STAGE/azure-workload-skus.json"    "$ROOT/data/azure-workloads.json"
cp "$STAGE/azure-workload-skus.csv"     "$ROOT/data/azure-workloads.csv"

echo
echo "Repository files updated:"
echo "  docs/azure-workload-sku-table.md"
echo "  docs/azure-workload-skus.html"
echo "  data/azure-workloads.json"
echo "  data/azure-workloads.csv"
exit $status
