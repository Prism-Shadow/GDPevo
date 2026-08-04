# ApexCloud Retention Operations Skill

Use this skill when a task requires building structured retention-operations outputs (risk queues, QBR packets, receivables reviews, churn rankings, or retention action boards) from the ApexCloud Retention Operations API.

## Step 1 — Discover the API Base URL

Read the file named `environment_access.md` in the task workspace. Extract the value of `GDPEVO_ENV_BASE_URL` and use it as the base URL for every API call. The file also declares which endpoints are available and any required headers (the train examples use no extra headers).

## Step 2 — Parse the Task Prompt

Extract these parameters from the prompt text. Not every prompt includes all of them; use only what is present:

- **Account IDs**: listed explicitly as a bullet or comma-separated list of `acct_*` identifiers.
- **Assessment date / as-of date**: the snapshot date for A/R aging and current-state values.
- **Analysis period**: a date range (start → end) and the corresponding month list (`YYYY-MM`).
- **Quarter label**: e.g. `2026-Q2`.
- **Region filter**: when specified (e.g. "North America", "all regions").
- **Event / HR context**: named events (e.g. `apex_connect`) or HR period filters.
- **Follow-up due dates**: sometimes given per action type; use them verbatim in the output.
- **Output shape reference**: if the prompt says "follow the structure in input/payloads/answer_template.json", load that file and use its keys and types as the output schema.
- **Sort order**: prompts may specify sort keys (e.g. "by customer_name ascending", "by risk_score descending").

## Step 3 — Identify the Task Archetype

Match the prompt's intent to one of the archetypes below. A task may combine aspects of multiple archetypes.

### Archetype A — Risk Queue

Rank a list of accounts by renewal risk. Required endpoints:
- `/api/accounts/{account_id}` — profile, tenure, segment, renewal date
- `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` — usage trends
- `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — SLA compliance
- `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — sentiment
- `/api/accounts/{account_id}/billing` — current ARR, renewal date
- `/api/accounts/{account_id}/ar-aging` — overdue balances

For each account, compute a risk score from weighted signals: overdue receivables, NPS decline, SLA degradation, usage decline, renewal proximity, low tenure. Sort descending by risk score and take the top N (usually 5). Assign risk_level thresholds and reason_codes per the reference tables.

### Archetype B — QBR Metrics Packet

Build a monthly metrics breakdown for a single account. Required endpoints:
- `/api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` — revenue per month
- `/api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` — ticket counts
- `/api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` — NPS per month

For SLA compliance: count tickets per month; the fraction with `sla_met=true` × 100, rounded to 1 decimal. Compute highlights (averages, peaks, ticket trend) from the monthly arrays. Assign metric_sources to the most specific endpoint used for each measure.

### Archetype C — Receivables & Pipeline Review

Cross-reference A/R aging with CRM accounts and summarize pipeline. Required endpoints:
- `/api/finance/ar-aging` — all overdue customers
- `/api/accounts` — CRM account list for name matching
- `/api/opportunities` — pipeline with stages (won/lost/open)
- `/api/hr/summary` — headcount, unpaid claims
- `/api/events/performance` — event orders and revenue

Link A/R customers to CRM accounts by matching `customer_name` to `legal_name` (or `name`). A match sets `link_status: "linked"` and fills `account_id`; otherwise `link_status: "unlinked"` with `account_id: null`. Compute win_rate_pct as `won_count / (won_count + lost_count) × 100`. Identify the `top_open_product_line` from open opportunities grouped by `product_line`.

### Archetype D — Churn Model Validation

Validate CSV exports and rank candidate accounts. Required endpoints:
- `/exports/churn/train.csv` — training rows and feature count
- `/exports/churn/validation.csv` — validation rows
- `/exports/churn/candidates.csv` — candidate predictions

Parse each CSV. Count training rows, validation rows, and feature columns (exclude the target/churn label column). Compute accuracy_pct from the validation set and map to an accuracy_band. Determine the tenure coefficient direction from the model metadata. For candidate ranking, extract predicted churn probabilities for the specified account IDs, sort descending, and return the top 5.

### Archetype E — Retention Action Board

Build a comprehensive board with rankings, segment summary, and follow-up calendar. Required endpoints:
- All account-level endpoints from Archetype A, for each listed account
- `/api/opportunities` — expansion pipeline filtered to the analysis period
- `/api/billing/snapshots` — cross-check ARR

Compute risk_level and primary_action per account. Assign `next_touch_due_date` from the prompt's follow-up calendar based on the assigned primary_action (null for `no_action`). Compute segment_summary by classifying accounts as strategic vs enterprise by segment field. `net_revenue_exposure` = `arr_at_risk` − `open_expansion_pipeline`.

## Step 4 — Fetch Data

For each account or entity in the task, issue GET requests to the required endpoints. Always include date/month range query parameters when the endpoint supports them. Parse JSON responses and CSV exports. Handle the case where an account returns null or 404 — skip it with a note but do not halt processing.

## Step 5 — Cross-Reference and Compute

Common cross-reference operations:

- **AR to CRM linking**: Match `customer_name` from `/api/finance/ar-aging` to `legal_name`/`name` in `/api/accounts`. Case-insensitive substring or exact match.
- **SLA compliance**: For a given period, `(tickets_with_sla_met / total_tickets) × 100`.
- **Ticket trend**: Compare ticket counts month-over-month. Three consecutive months: if counts strictly decrease → `improving`, strictly increase → `worsening`, otherwise → `flat`.
- **NPS drop**: Latest month NPS is lower than the previous month.
- **Win rate**: `won / (won + lost) × 100` from opportunity stages.
- **Top product line**: Group open opportunities by `product_line`, sum amounts, take the max.

## Step 6 — Assemble Output

Use the answer template from `input/payloads/answer_template.json` (when referenced) as the exact output schema. Fill every field using:
- Data fetched from the API
- Computed values from Step 5
- Controlled vocabulary from `skill/references/controlled_vocabulary.md`

If the prompt does not reference an answer template, build output that matches the shape described in the prompt body.

### Precision Rules (always apply)
- Currency: 2 decimal places
- Percentages: 1 decimal place
- Counts: integers
- Risk scores: integers
- Churn probabilities: 3 decimal places
- NPS: integers

### Controlled Labels
Use only labels from `skill/references/controlled_vocabulary.md`. Never invent labels.

## Step 7 — Validate Before Returning

- Every field in the answer template is populated (or explicitly null where allowed).
- All enum values match the controlled vocabulary exactly.
- Numeric precision matches the rules above.
- Sort order matches the prompt's specification.
- Top-N lists contain exactly N entries.
- Policy codes are selected from the pipe-delimited options, not invented.

## Reference Files

- `skill/references/api_endpoints.md` — full endpoint catalog with query parameters and data relationships
- `skill/references/controlled_vocabulary.md` — all enum values, precision rules, and policy code conventions
