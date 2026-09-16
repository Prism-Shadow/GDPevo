# Atlas Commerce Operations API Patterns

## Base configuration

```bash
BASE="${TASK_ENV_BASE_URL:-http://task-env:9022}"
AUTH="Authorization: Bearer atlas-ops-token-022"
```

## Schema and dictionary discovery

```bash
# Schema: tables, columns, types, foreign keys
curl -s -H "$AUTH" "$BASE/api/schema" > /tmp/schema.json

# Data dictionary: business meanings for columns and enum values
curl -s -H "$AUTH" "$BASE/api/data-dictionary" > /tmp/dictionary.json
```

These files are large. Use `python3 -m json.tool` to pretty-print, or query them with `jq` for specific tables:

```bash
# List all tables
jq '.tables | keys' /tmp/schema.json

# Columns for a specific table
jq '.tables.orders.columns | keys' /tmp/schema.json

# Relationships for a table
jq '.tables.orders.relationships' /tmp/schema.json
```

## Read-only SQL queries

Send queries as JSON with a `sql` key:

```bash
curl -s -X POST \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT column FROM table WHERE condition"}' \
  "$BASE/api/sql"
```

Returns JSON with a `rows` array and optional `row_count`. Each row is a JSON object with column-name keys.

### Common SQL snippets

**Filtering effective rows:**
```sql
SELECT ... FROM table WHERE effective = true
```

**Date range filtering (inclusive boundaries):**
```sql
SELECT ... FROM table
WHERE created_at >= '2026-03-01T00:00:00Z'
  AND created_at <= '2026-04-30T23:59:59Z'
```

**Counting distinct values:**
```sql
SELECT COUNT(DISTINCT column) AS cnt FROM table
```

**Grouping with aggregation:**
```sql
SELECT region, COUNT(*) AS cnt
FROM table
GROUP BY region
ORDER BY cnt DESC, region ASC
```

**Multi-table joins through foreign keys:**
```sql
SELECT o.order_id, s.shipment_id, s.status
FROM orders o
JOIN shipments s ON o.order_id = s.order_id
WHERE o.campaign_id = 'CMP-EXAMPLE'
  AND s.effective = true
```

**Subqueries for existence checks:**
```sql
SELECT *
FROM orders o
WHERE EXISTS (
  SELECT 1 FROM shipments s
  WHERE s.order_id = o.order_id
    AND s.effective = true
)
```

**FX rate lookup:**
```sql
SELECT r.service_date, r.currency, r.amount,
       f.usd_per_unit
FROM refunds r
JOIN fx_rates f ON r.service_date = f.rate_date AND r.currency = f.currency
```

## Transaction endpoint (correction tasks only)

For controlled single-row data corrections:

```bash
curl -s -X POST \
  -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "carrier_scan",
    "entity_id": "<shipment_id>",
    "source_row_id": "<scan_row_id>",
    "field_name": "<field_name>",
    "old_value": "<old_canonical_value>",
    "new_value": "<new_canonical_value>",
    "reason_code": "<reason_code>",
    "actor": "<actor>",
    "audit_id": "<audit_id>",
    "correction_key": "<correction_key>",
    "corrected_at": "<corrected_at_iso8601>"
  }' \
  "$BASE/api/sql/transaction"
```

Returns a result with `affected_business_rows` and `audit_rows` counts.

## Correction audit endpoint

```bash
curl -s -H "$AUTH" "$BASE/api/correction-audit" | python3 -m json.tool
```

Returns all correction audit records. Filter for your correction_key or audit_id to verify.

## Running Python for computation

The Python script at `scripts/compute.py` provides a skeleton. Key patterns:

**Fetching SQL results from Python:**
```python
import subprocess, json

def query(sql):
    result = subprocess.run([
        "curl", "-s", "-X", "POST",
        "-H", "Authorization: Bearer atlas-ops-token-022",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"sql": sql}),
        f"{base}/api/sql"
    ], capture_output=True, text=True)
    return json.loads(result.stdout)
```

**Rate computation:**
```python
rate = round(qualifying / total, 4)  # round only final values
```

**Median:**
```python
import statistics
median = round(statistics.median(sorted_values), 2)
```

**Tiered classification:**
```python
def classify(rate, severe_rate):
    for tier in rules:
        if eval(tier["condition"]):
            return tier["status"]
    return catch_all_status
```

**Sorting with tie-breakers:**
```python
sorted_items = sorted(items, key=lambda x: (-x["primary"], x["secondary"]))
```

**Currency conversion:**
```python
# For each refund row, look up the daily FX rate and convert
usd_amount = row["amount"] * fx_lookup[(row["service_date"], row["currency"])]
```
