#!/usr/bin/env bash
# Helper for querying the M&A Deal Workbench API.
# Usage: source skill/query_workbench.sh
#        workbench_get /api/deals/PRJ_JUNIPER
#        workbench_post_query "SELECT * FROM deals WHERE deal_id = 'PRJ_JUNIPER'"

: "${TASK_ENV_BASE_URL:?Set TASK_ENV_BASE_URL to the workbench base URL}"

TOKEN="${DEAL_WORKBENCH_TOKEN:-deal-workbench-readonly}"

workbench_get() {
  local path="$1"
  curl -sS "${TASK_ENV_BASE_URL}${path}"
}

workbench_post_query() {
  local sql="$1"
  curl -sS -X POST "${TASK_ENV_BASE_URL}/api/query" \
    -H "Content-Type: application/json" \
    -d "{\"token\":\"${TOKEN}\",\"sql\":\"${sql}\"}"
}

workbench_pretty() {
  python3 -m json.tool 2>/dev/null || python3 -c "
import sys,json
try:
    data=json.load(sys.stdin)
    print(json.dumps(data,indent=2))
except Exception as e:
    print(sys.stdin.read())
"
}
