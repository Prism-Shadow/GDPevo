# Operations Analytics API — Task Group 022 Skill

## Overview

This skill covers the shared operations analytics API workflows for AtlasDB and HelioSync
product lines. The tasks span usage rollups, defect-ticket rollups, incident exposure
summaries, data-quality corrections, and post-correction backlog recomputation. Every
response is a single JSON object. Precision, ordering, and exclusion rules are mandatory.

---

## Environment

- **Base URL**: `http://34.46.77.124:9022`
- **Access**: HTTP API only; the underlying database is queried *through* API endpoints, never
  via direct filesystem or local SQLite access.
- **Discovery**: Always start with `GET /` (the API root). It returns endpoint
  documentation, table schemas, and query instructions.

---

## Discovery & Query Workflow

### Phase 1 — Schema Discovery

1. `GET /` to learn available endpoints, tables, column names, and relationships.
2. Identify the tables relevant to the task (typically `usage_daily`, `tickets`, `accounts`,
   `subscriptions`, `incidents`, `data_quality_cases`).
3. Note column names precisely — they are case-sensitive. Common columns:
   - `usage_daily`: `usage_id`, `account_id`, `product_id`, `usage_date`, `environment`,
     `compute_hours`, `api_calls`, `telemetry_source`, `is_backfill`, `audit_reason`,
     `audit_updated_at`
   - `tickets`: `ticket_id`, `account_id`, `product_id`, `created_date`, `status`,
     `severity`, `category`, `customer_impact`, `is_duplicate`, `duplicate_of`,
     `sla_breach`, `closed_date`, `is_canceled`, `audit_reason`, `audit_updated_at`
   - `accounts`: `account_id`, `account_name`, `region`, `tier`, `is_internal`, `is_active`
   - `subscriptions`: `account_id`, `product_id`, `start_date`, `end_date`, `status`
   - `incidents`: `incident_id`, `product_id`, `started_at`, `resolved_at`,
     `impacted_region`, `severity`
   - `data_quality_cases`: `case_id`, `case_status`, `case_type`, `target_table`,
     `new_value`, `audit_reason`, `created_at`

### Phase 2 — Query Through API Endpoints

Use the API's query/select endpoints (not raw SQL). Common patterns:

- Filter by date range: always **inclusive on both ends** unless the task explicitly says
  "exclusive" (as with follow-up ticket windows, which use `start_exclusive`).
- Filter by `product_id` (`'ATLASDB'` or `'HELIOSYNC'`) — exact match.
- Join across tables via the API's relationship parameters or by correlating `account_id`
  and `product_id` across query results.

### Phase 3 — Qualify Records

Apply business-rule filters **after** fetching candidate rows from the API. Track every
exclusion count so you can report it.

#### Usage Record Qualification (AtlasDB / HelioSync)

A usage row is **qualified** when ALL of these are true:

| Rule | Column / Join | How to check |
|---|---|---|
| Correct product | `usage_daily.product_id` | Must match the task's product (`'ATLASDB'` or `'HELIOSYNC'`) |
| Within date range | `usage_daily.usage_date` | `>= start_date AND <= end_date` |
| Production environment | `usage_daily.environment` | Must be `'production'` |
| Not backfill | `usage_daily.is_backfill` | Must be `0` or `FALSE` |
| Not telemetry-v1 | `usage_daily.telemetry_source` | Must NOT be `'telemetry-v1'` |
| Enterprise account | `accounts.tier` | Must be `'enterprise'` |
| Account is active | `accounts.is_active` | Must be `1` or `TRUE` |
| Not internal | `accounts.is_internal` | Must be `0` or `FALSE` |
| Active subscription | `subscriptions` | Must have a subscription row with `status = 'active'` whose window overlaps the usage date range |

#### Ticket Record Qualification (Customer-Impacting Defects)

A ticket is **qualified** when ALL of these are true:

| Rule | Column | How to check |
|---|---|---|
| Correct product | `tickets.product_id` | Matches task product |
| Within creation window | `tickets.created_date` | Inclusive range |
| Customer-impacting | `tickets.customer_impact` | Must be `1` or `TRUE` |
| Defect category | `tickets.category` | Must be `'defect'` |
| Not duplicate | `tickets.is_duplicate` | Must be `0` or `FALSE` |
| Not canceled | `tickets.is_canceled` | Must be `0` or `FALSE` |
| Not internal/test account | `accounts.is_internal` | Must be `0` or `FALSE` |

---

## Output Field Conventions

### Rounding Rules (Mandatory)

| Field type | Decimal places | Example |
|---|---|---|
| `compute_hours` | **2** | `10129.55` |
| SLA breach rate (ratio) | **4** | `0.7273` |
| `median_close_hours` | **2** | `115.71` |
| `added_compute_hours` | **2** | `193.99` |

### Date Formats

- Date-only fields: `YYYY-MM-DD` (e.g., `"2026-01-01"`)
- Datetime fields: `YYYY-MM-DD HH:MM:SS` (e.g., `"2026-05-20 10:57:13"`)

### Data Types

- Counts, row numbers: **integer** (no decimals, no quotes)
- Ratios: **number** (not string)
- IDs, names, regions: **string**
- Arrays: always present, even if empty (`[]`)

### Always-Include Rule

- All four regions (`NA`, `EMEA`, `APAC`, `LATAM`) must appear in regional breakdowns
  even if `qualified_account_count` and `compute_hours` are zero — omit only when the
  task explicitly scopes to a single region and the template confirms region-level output.
- All four severities (`P1`, `P2`, `P3`, `P4`) must be keys in `severity_mix` and
  `backlog_by_severity` objects, with zero for absent tiers.
- Exclusion count keys must all be present, even those whose value is `0`.

---

## Deterministic Ordering Rules

### Top-N Lists
Order by the **primary metric descending**, then **`account_id` ascending** for ties.

| List | Primary sort (DESC) | Tiebreaker (ASC) |
|---|---|---|
| `top_accounts` (usage) | `compute_hours` | `account_id` |
| `top_accounts` (tickets) | `ticket_count` | `account_id` |
| `top_account_after_fix` | `compute_hours` | `account_id` |
| `highest_usage_account` | `compute_hours` | `account_id` |
| `accounts_to_notify` | `backlog_ticket_count` DESC, then `highest_severity` priority (P1 first), then `account_id` ASC | multisort |

### Flat Lists
- `regional_breakdown`: alphabetical by `region` (`APAC`, `EMEA`, `LATAM`, `NA`)
- `account_breakdown`: ascending by `account_id`
- `affected_accounts`: ascending by `account_id`
- `qualified_ticket_ids`: ascending string sort
- `impacted_accounts`: descending by `api_calls`, then ascending `account_id` for ties
- `accounts_with_followup_tickets`: ascending by `account_id`

### Severity Priority
For order-by-severity, the priority is: `P1` > `P2` > `P3` > `P4`. When sorting by
"highest severity", `P1` is the highest/worst, `P4` the lowest.

---

## Data-Quality Correction Patterns

When a task involves applying an approved data-quality case:

### SQL UPDATE Safety Rules

1. **Always guard with WHERE clauses** — never run a bare UPDATE.
2. **Include an EXISTS subquery** on `data_quality_cases` checking:
   - `case_id = '<case-id>'`
   - `case_status = 'approved'`
   - `case_type` matches the correction type (e.g., `'ticket_duplicate_correction'`)
   - `target_table` matches (`'tickets'` or `'usage_daily'`)
3. **Check the current state** before mutating — e.g., `AND is_duplicate = 0 AND duplicate_of IS NULL`
4. **Always populate audit fields**:
   - `audit_reason` — set from the data_quality_cases row
   - `audit_updated_at` — set from the data_quality_cases `created_at`
5. **Use a consistent timestamp** for `audit_updated_at`. Source it from
   `data_quality_cases.created_at` for the specific case row, NOT from
   `datetime('now')` or any wall-clock function.
6. **Prefer subquery-based values** over hardcoded literals for `audit_reason`,
   `duplicate_of`, and `audit_updated_at` — this keeps the SQL self-documenting.

### Correction SQL Template (Usage Reclassification)

```sql
UPDATE usage_daily
SET product_id = '<correct-product>',
    audit_reason = '<approved case ID description>',
    audit_updated_at = '<timestamp from case>'
WHERE usage_id IN (<list of specific usage_ids>)
  AND product_id = '<wrong-product>';
```

### Correction SQL Template (Ticket Dedup)

```sql
UPDATE tickets
SET is_duplicate = 1,
    duplicate_of = (SELECT new_value FROM data_quality_cases
                    WHERE case_id = '<case-id>' AND case_status = 'approved'),
    audit_reason = (SELECT audit_reason FROM data_quality_cases
                    WHERE case_id = '<case-id>' AND case_status = 'approved'),
    audit_updated_at = (SELECT created_at FROM data_quality_cases
                        WHERE case_id = '<case-id>' AND case_status = 'approved')
WHERE ticket_id IN (<list of specific ticket_ids>)
  AND product_id = '<product>'
  AND is_duplicate = 0
  AND duplicate_of IS NULL
  AND EXISTS (
    SELECT 1 FROM data_quality_cases
    WHERE case_id = '<case-id>'
      AND case_status = 'approved'
      AND case_type = 'ticket_duplicate_correction'
      AND target_table = 'tickets'
  );
```

### Post-Correction Workflow

1. Execute the correction SQL through the API.
2. Report `changed_row_count` or `changed_ticket_count` (rows actually modified).
3. Re-fetch the data with the same qualification rules as before.
4. Recompute all metrics (counts, hours, breach rates, top accounts, backlog) against
   the **post-correction** state.
5. The `audit_reason` field in the response must match the approved case description
   exactly: `"approved correction <case-id>"`.

---

## Specific Metric Formulas

### SLA Breach Rate
```
sla_breach_rate = count_of_qualified_tickets_with_sla_breach / qualified_ticket_count
```
- Round to **4 decimal places**.
- If no qualified tickets, the rate is `0.0000` (not null or omitted).

### Median Close Hours
- Consider only **closed** qualified tickets (status `'closed'` or `'resolved'`).
- Compute `close_hours = (closed_date - created_date)` in hours (decimal).
- Use the **median** of those values (if even count, average the two middle values).
- Round to **2 decimal places**.

### Compute Hours Aggregation
- Sum `compute_hours` across all qualified usage rows.
- Round to **2 decimal places**.

---

## Exclusion Tracking

### Usage Exclusion Categories
Track and report counts for:
- `usage_candidate_rows` — total rows fetched before filtering
- `usage_non_production_rows_excluded`
- `usage_backfill_rows_excluded`
- `usage_internal_or_inactive_account_rows_excluded`
- `usage_without_active_subscription_rows_excluded`
- `usage_telemetry_v1_overlap_rows_excluded` (or `telemetry_v1_rows_excluded`)

### Ticket Exclusion Categories
Track and report counts for:
- `duplicate`
- `canceled`
- `internal_or_test_account`
- `non_customer_impact`
- `non_defect_category`
- (for incident follow-up) `ticket_canceled_or_duplicate_excluded`,
  `ticket_non_customer_impact_excluded`

---

## Incident Analysis Patterns

1. **Source incident metadata from the database** — do not hardcode window or region from
   the prompt; query the `incidents` table by `incident_id` for the authoritative
   `started_at`, `resolved_at`, `impacted_region`, and `severity`.
2. **Usage exposure window** = the incident window (`started_at` through `resolved_at`,
   inclusive). Filter usage rows whose `usage_date` falls in that range AND whose
   `account.region` matches the incident's `impacted_region` (unless `GLOBAL`).
3. **Follow-up ticket window** = 7 calendar days after resolution:
   - `start_exclusive` = `resolved_at`
   - `end_inclusive` = `resolved_at + 7 days` (same time of day)
4. **Follow-up tickets** = tickets created in the follow-up window for external customer
   accounts in the impacted region. Apply ticket qualification (no duplicates, no
   canceled, customer-impacting).
5. **Severity mix** = counts of follow-up tickets by severity, always with all four keys.

---

## Backlog Analysis Patterns (Post-Correction)

1. **Backlog** = qualified, non-closed customer-impacting defect tickets within the
   specified period.
2. **`backlog_by_severity`** — always an object with keys `P1`, `P2`, `P3`, `P4`, even
   when some counts are zero.
3. **`accounts_to_notify`** — accounts that have at least one backlog ticket after the
   correction. Sort by:
   - `backlog_ticket_count` descending
   - `highest_severity` ascending in severity priority (P1 before P4)
   - `account_id` ascending
4. **`highest_severity`** for an account = the worst severity among its backlog tickets
   (`P1` worst, `P4` least).

---

## Common Pitfalls

1. **Off-by-one on date ranges** — confirm whether each range boundary is inclusive or
   exclusive. Usage and ticket creation windows are typically inclusive on both ends.
   Follow-up windows after incidents use `start_exclusive` / `end_inclusive`.
2. **Forgetting to exclude telemetry-v1 rows** — these overlap with production telemetry;
   always filter them out from qualified usage.
3. **Including backfill rows** — `is_backfill = 1` rows must be excluded from usage
   qualification.
4. **Including internal or inactive accounts** — always join accounts and check
   `is_internal = 0` and `is_active = 1`.
5. **Missing subscription check** — usage rows for accounts without an active subscription
   covering the date range are not qualified.
6. **Including duplicate/canceled tickets** — always filter `is_duplicate = 0` and
   `is_canceled = 0` for ticket qualification.
7. **Including non-defect or non-customer-impact tickets** — check `category = 'defect'`
   and `customer_impact = 1`.
8. **Wrong rounding** — compute_hours always 2 decimals; SLA breach rate always 4
   decimals. Round after summing, not before.
9. **Missing zero entries** — severity tiers and regions must appear even with zero
   values. Don't omit keys.
10. **Sort order errors** — account_id is the tiebreaker for top-N lists, ascending.
    Regional breakdowns are alphabetical. Account breakdowns are by account_id ascending.
11. **Hardcoding incident metadata** — always read `started_at`, `resolved_at`, and
    `impacted_region` from the `incidents` table, not from the prompt text.
12. **UPDATE without safety guards** — always include an EXISTS check on
    `data_quality_cases` with `case_status = 'approved'` and the correct `case_type` and
    `target_table`.
13. **Using wall-clock time in audit fields** — source `audit_updated_at` from the
    `data_quality_cases.created_at` value, not from `datetime('now')`.
14. **Accumulating float drift in sums** — sum raw values first, then round the total to 2
    decimal places once.
15. **Median of empty set** — if no closed qualified tickets exist, determine the
    convention from the template (usually 0 or null). Check the gold examples for the
    expected behavior.

---

## Step-by-Step Execution Checklist

1. `GET /` — discover schema and endpoints.
2. Identify tables and columns needed for this task.
3. Fetch candidate rows through the API (usage, tickets, incidents, accounts,
   subscriptions, data_quality_cases).
4. Apply qualification filters; track every exclusion count.
5. If a correction case applies:
   a. Read the case details from `data_quality_cases`.
   b. Construct a safe UPDATE with all guards.
   c. Execute through the API; record `changed_row_count`.
   d. Re-fetch and re-qualify the data.
6. Aggregate: sum compute hours, count qualified rows, compute ratios.
7. Build top-N and breakdown lists with correct ordering.
8. Round all numeric outputs to the required precision.
9. Assemble the JSON response matching the template shape exactly.
10. Verify: all required keys present, zero-value entries included, consistent rounding,
    correct ordering.
