---
name: atlas-ops-api
description: Solve operational analytics and data-correction tasks against the Atlas Commerce Operations API. Use this skill whenever the user mentions Atlas Commerce Operations, the Atlas API, fulfillment scorecards, refund reconciliation, carrier quality corrections, warehouse productivity reviews, support health reviews, or any operational analytics task that references TASK_ENV_BASE_URL with a bearer token and SQL endpoints.
---

# Atlas Commerce Operations API

Solve operational analytics and data-correction tasks against the Atlas Commerce Operations API. The API exposes a read-only SQL query service, a schema browser, a data dictionary, a controlled transaction endpoint for single-row corrections, and a correction-audit log.

## Endpoints

The API base URL is provided in the prompt as `<TASK_ENV_BASE_URL>`. Common staging value is `http://task-env:9022`.

All requests use this header:

```
Authorization: Bearer atlas-ops-token-022
```

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Full database schema: tables, columns, types, relationships |
| GET | `/api/data-dictionary` | Business meanings for columns and enumerated values |
| POST | `/api/sql` | Read-only analytical SQL queries |
| POST | `/api/sql/transaction` | Controlled single-row data correction |
| GET | `/api/correction-audit` | Correction audit trail |

The first three endpoints are available for every task. The transaction and audit endpoints are only needed for data-correction tasks.

## Workflow

### 1. Parse the inputs

Every task supplies at least two files under `input/payloads/`:

- A **business request JSON** (e.g. `fulfillment_request.json`) that defines scope, cohort rules, business definitions, classification policies, and rounding instructions.
- An **answer template JSON** (e.g. `answer_template.json`) that is the exact output contract: required fields, types, constraints, and enumerations.

Read both files first. The answer template tells you what to produce; the request tells you how to compute it.

Key sections to extract from the request:
- `scope` / `cohort` / `account_scope` / `case_opened_window`: population and time filters
- `business_definitions` / `reporting_definitions` / `money_policy`: how to classify, measure, and aggregate
- `overall_status_rules` / `cohort_risk_policy` / `support_risk_policy` / `facility_status_rules`: tiered classification
- `rounding`: when and how to round (typically only final reported values)
- `worst_account_ranking` / `employee_ranking` / `reason_ranking`: sort-and-tiebreak rules

For correction tasks, also note:
- `approved_correction`: the exact single-row change to apply
- `correction_status_rule`: how to decide APPLIED vs NOT_APPLIED

### 2. Discover the data model

Call `GET /api/schema` to understand available tables, columns, and foreign keys. Then call `GET /api/data-dictionary` to learn what each column means — especially status codes, enumerated values, and timestamp semantics.

Use `curl` with the bearer token. For example:

```bash
curl -s -H "Authorization: Bearer atlas-ops-token-022" "$TASK_ENV_BASE_URL/api/schema" | python3 -m json.tool
curl -s -H "Authorization: Bearer atlas-ops-token-022" "$TASK_ENV_BASE_URL/api/data-dictionary" | python3 -m json.tool
```

Save these responses to temporary files so you can reference them while constructing queries.

### 3. Map business definitions to SQL

Translate the request's business definitions into SQL queries. Use SQL only for data extraction and let Python handle aggregations, rate math, and classification. Do NOT compute complex metrics in SQL.

**General SQL patterns:**

- **Population filtering**: Use the cohort/time-window fields from the request. Date comparisons use ISO 8601 timestamps. Include boundary rows when the request says `inclusive` or `INCLUSIVE`.
- **Status columns**: Always check the data dictionary for the exact status values. A "delivered" shipment may be `'DELIVERED'` in `canonical_status`, not `status`.
- **Multi-table joins**: The schema reveals foreign keys. Common joins: orders to shipments, shipments to carrier_scans, orders to refunds to reversals, cases to accounts.
- **Effective/latest rows**: When a table has `effective` or `is_current` flags, filter to `true` rows.

**Query construction rules:**
- Send SQL as a JSON body: `{"sql": "SELECT ..."}`
- Use `curl -s -X POST -H "Authorization: Bearer atlas-ops-token-022" -H "Content-Type: application/json" -d '{"sql":"..."}' "$TASK_ENV_BASE_URL/api/sql"`
- Escape single quotes in SQL using Python's `json.dumps` or careful shell escaping
- For large result sets, use Python with `subprocess` and `json.loads` to capture results programmatically

### 4. Compute the answer

Use Python to compute the final metrics from SQL result sets. The script at [scripts/compute.py](scripts/compute.py) provides a starter skeleton with helper functions. Adapt the computation logic to each task's specific business definitions.

**Key computation rules that repeat across tasks:**

- **Rates**: Divide the qualifying subset by the total population. Include incomplete/active items in the denominator unless the request says otherwise.
- **Rounding**: Round only final reported values. Keep intermediate calculations unrounded to avoid drift. Use Python's `round()`.
- **Ranking and tie-breaking**: Sort by the primary dimension descending, then by the tie-break dimension ascending. Take the top N.
- **Median**: For even-length lists, average the two central values after sorting. Use `statistics.median()` or explicit logic.
- **Currency conversion**: When FX rates are involved, convert each row's amount to USD using the daily rate for that row's service date, then aggregate. Use the `fx_rates` table.
- **Status classification**: Apply tiered rules in order. The first matching tier wins. The final tier is typically a catch-all ("otherwise").

**For correction tasks only:**
- Identify the single row and field that needs correction by querying the data
- Use `POST /api/sql/transaction` with the exact correction JSON: entity type, row ID, field name, old value, new value, reason code, actor, audit ID, correction key, and corrected_at timestamp
- Verify with a follow-up `POST /api/sql` query and `GET /api/correction-audit`
- Set `correction_status` to `APPLIED` only when exactly one business row and one audit row committed AND the post-change canonical value is confirmed

### 5. Validate and write the answer

Before writing `answer.json`:
- Check every required field exists
- Verify types match the template (integer, number, string, array, object)
- Confirm array lengths (e.g. exactly 2 worst regions, exactly 3 top employees)
- Confirm array ordering matches the sort rules
- Verify enum values match the template's allowed set exactly
- Check rate ranges (0 to 1) and rounding (4 decimal places for rates, 2 for dollars/hours)

Write the answer with `json.dump` to ensure valid JSON:

```python
import json
with open("answer.json", "w") as f:
    json.dump(result, f, indent=2)
```

Do NOT include commentary, explanations, or extra fields. The output must be exactly the JSON object matching the template.

## Common pitfalls

- **Time boundary semantics**: When a request says "at or before the cutoff", use `<=`. When it says "strictly before", use `<`. When it says "by the cutoff", check whether the request means inclusive or exclusive.
- **Active-time clock**: The "active time" clock for support cases measures time spent in active state, not wall-clock time. The data dictionary explains how this is tracked.
- **Effective rows**: Many tables have effective-dated rows. Always filter to `effective = true` or the equivalent flag.
- **Reopened cases**: Cases in `REOPENED` state are a subset of open/active cases. Count them separately but include them in the open count.
- **Canonical vs raw values**: Carrier scan tables often have both a `raw_status` (from the carrier) and a `canonical_status` (normalized). The business definitions operate on canonical values; corrections modify canonical values only.
- **Multiple shipments per order**: An order may have multiple shipments. Aggregate across shipments before classifying the order (e.g. an order is complete only when ALL its shipments are delivered).
- **Severe exception time math**: Compare the cutoff timestamp to each shipment's `promised_delivery_at`. The 24-hour threshold means `cutoff - promised_delivery_at > 24 hours`.

## Reference files

- [references/api-patterns.md](references/api-patterns.md) — curl patterns, common SQL snippets, and transaction format
- [scripts/compute.py](scripts/compute.py) — Python skeleton for query-to-answer computation
