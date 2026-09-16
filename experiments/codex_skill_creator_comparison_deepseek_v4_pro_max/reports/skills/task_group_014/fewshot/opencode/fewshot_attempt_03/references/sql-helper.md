# SQL Query Helper

Reusable pattern for querying the Northstar payer-operations SQL endpoint. Use this when curl escaping becomes unwieldy for multi-condition queries.

## Curl Quoting Reference
The SQL endpoint expects a JSON body with key `sql`. The bearer token is `pa-review-token-014`.

Single-line queries with one string condition:

```bash
curl -s -X POST <BASE_URL>/sql/query \
  -H "Authorization: Bearer pa-review-token-014" \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM cases WHERE case_id = '\''CASE-XX-XXX'\''"}'
```

The `'\''` sequence inside single-quoted curl `-d` strings closes the outer single-quote, inserts a literal single quote, then reopens. For queries with many string conditions, prefer the Python approach below.

Multi-condition queries are easier with Python:

```python
import requests, json, sys

BASE = sys.argv[1] if len(sys.argv) > 1 else "<BASE_URL>"
HEADERS = {"Authorization": "Bearer pa-review-token-014", "Content-Type": "application/json"}

def query(sql):
    r = requests.post(f"{BASE}/sql/query", headers=HEADERS, json={"sql": sql})
    return r.json()

# Example: gather all case context in one call
result = query(
    "SELECT c.*, m.patient_name, m.plan_type, pv.provider_name, pv.specialty, "
    "pl.payer_name, pol.policy_name, pol.version "
    "FROM cases c "
    "JOIN members m ON c.member_id = m.member_id "
    "JOIN providers pv ON c.provider_id = pv.provider_id "
    "JOIN plans pl ON m.plan_id = pl.plan_id "
    "JOIN policies pol ON c.policy_id = pol.policy_id "
    "WHERE c.case_id = 'CASE-XX-XXX'"
)
print(json.dumps(result, indent=2))
```

## Response Shape

Every SQL query returns:

```json
{
  "columns": ["col1", "col2", "..."],
  "rows": [
    {"col1": "value", "col2": "value"}
  ],
  "row_count": 1,
  "limited": false,
  "max_rows": 500
}
```

When `row_count` equals `max_rows` and `limited` is `true`, results are truncated. Use more specific WHERE clauses or pagination if this occurs, though it is rare for single-case queries.

## Common Query Templates

### Gather full case context (prior auth, P2P, appeals)

```sql
SELECT c.*, m.*, pv.*, pl.*, pol.*
FROM cases c
JOIN members m ON c.member_id = m.member_id
JOIN providers pv ON c.provider_id = pv.provider_id
JOIN plans pl ON m.plan_id = pl.plan_id
JOIN policies pol ON c.policy_id = pol.policy_id
WHERE c.case_id = '<case_id>'
```

### Gather criteria results with policy context

```sql
SELECT cc.*, pc.criterion_key, pc.criterion_text, pc.approval_required, pc.result_if_missing
FROM case_criteria cc
JOIN policy_criteria pc ON cc.criterion_id = pc.criterion_id
WHERE cc.case_id = '<case_id>'
```

### Gather documents with clinical facts

```sql
SELECT d.*, df.fact_id, df.fact_key, df.fact_value, df.numeric_value, df.unit, df.supports_criteria
FROM documents d
LEFT JOIN document_facts df ON d.document_id = df.document_id
WHERE d.case_id = '<case_id>'
ORDER BY d.document_id, df.fact_id
```

The LEFT JOIN ensures documents without extracted facts still appear.

### Gather claim lines with matching benchmarks

```sql
SELECT cl.*, pb.benchmark_id, pb.allowed_amount, pb.source_name, pb.source_version,
       pb.effective_start, pb.effective_end
FROM claim_lines cl
JOIN claims c ON cl.claim_id = c.claim_id
JOIN members m ON c.member_id = m.member_id
LEFT JOIN payment_benchmarks pb
  ON pb.payer = c.payer
  AND pb.plan_type = m.plan_type
  AND pb.cpt_code = cl.cpt_code
  AND (pb.modifier = cl.modifier OR (pb.modifier IS NULL AND cl.modifier IS NULL))
WHERE cl.claim_id = '<claim_id>'
ORDER BY cl.line_number, pb.effective_start DESC
```

The LEFT JOIN on benchmarks preserves claim lines even when no benchmark matches. The ORDER BY `effective_start DESC` surfaces the most recent benchmark first for each line.

### Gather drug trials with appeal context

```sql
SELECT dt.*, a.appeal_id, a.denial_date, a.appeal_path, a.expedited_attestation, a.appeal_deadline
FROM drug_trials dt
JOIN appeals a ON dt.case_id = a.case_id
WHERE dt.case_id = '<case_id>'
ORDER BY dt.medication
```

### Gather margin queue rows

```sql
SELECT *
FROM service_margin
WHERE month_id IN ('<id1>', '<id2>', '<id3>')
ORDER BY month_id
```

## Error Handling

The SQL endpoint returns errors in this shape:

```json
{"error": "invalid_sql", "message": "<details>"}
```

Common errors:
- Using key `"query"` instead of `"sql"` in the JSON body.
- SQL syntax errors (unmatched quotes, missing FROM).
- Referencing nonexistent tables or columns.

When a query returns errors, verify column names against `GET /api/tables` and confirm the JSON key is `"sql"`.
