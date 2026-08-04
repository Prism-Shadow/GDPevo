## Purpose

Operate the ApexCloud Retention Operations API to build structured retention-analysis deliverables: risk queues, QBR metric packets, receivables reviews, churn-model validations, and high-touch retention boards.

## Environment Configuration

Read the API base URL from the environment variable `GDPEVO_ENV_BASE_URL`. All endpoints are relative to that base. Required headers: none.

## API Reference

See `skill/api_reference.md` for the full endpoint catalog, query-parameter conventions, and return-field summaries.

## Generic Operating Rules

### Input / Prompt Parsing

- Extract every enumerable parameter from the task prompt: account IDs, date ranges, months, assessment/as-of dates, follow-up due dates, and region/event filters.
- Locate the answer-template JSON inside `input/payloads/answer_template.json`. That structure is authoritative for output shape.
- If the prompt references a named account list, include only those IDs. If it says "all regions," include every record the API returns.

### API Call Patterns

- Prefer GET to the `/api/accounts/{account_id}` family (metrics, tickets, nps, billing, ar-aging) for single-account views.
- Use collection endpoints (`/api/accounts`, `/api/finance/ar-aging`, `/api/opportunities`, `/api/hr/summary`, `/api/events/performance`) for cross-account or aggregate views.
- For time-scoped endpoints, supply `start` and `end` query parameters:
  - Month-granularity endpoints: `start=YYYY-MM&end=YYYY-MM`
  - Date-granularity endpoints: `start=YYYY-MM-DD&end=YYYY-MM-DD`

### Linking and Matching

- When linking A/R records to CRM accounts, match on the customer identifier shared across both systems. Mark `link_status` as `"linked"` when a CRM account is found; otherwise `"unlinked"`.
- Sort linked follow-up lists as specified by the prompt (e.g., `customer_name` ascending).

### Vocabularies

Every enumerable field MUST use one of the controlled values below. Never invent new labels.

See `skill/vocabulary.md` for the complete controlled vocabulary.

### Precision Rules

- Currency values (ARR, revenue, balances, pipeline): exactly 2 decimal places.
- Percentage values (SLA compliance, win rate, accuracy): exactly 1 decimal place, except churn probability which uses 3 decimal places.
- Counts (tickets, NPS, headcount, rows): integers.
- Risk scores: integers.

### Output Formatting

- Return valid JSON only. No markdown fences, no explanatory text, no leading/trailing whitespace outside the JSON object.
- Follow the answer-template shape exactly, including every key at every nesting level.
- Omit keys that are not present in the template.
- Use `null` for optional numeric fields that have no data (e.g., `nps_score: null` when no NPS survey exists).
- For empty ordered lists, use `[]`.

### Policy Codes

Policy code fields follow the pattern `PREFIX-N` where PREFIX is a 2-5 character uppercase code and N is a digit from 1-9. Typical prefixes include:

- Risk model: `RS-`
- Revenue/ARR source: `REV-`
- Support hygiene: `SUP-`
- Action priority: `ACT-`
- Receivable trigger: `RCP-`
- CRM match: `CM-`
- Pipeline window: `PW-`
- Follow-up scope: `FS-`
- Churn model protocol: `MOD-`
- Probability scale: `PRB-`
- Deployment rule: `DEP-`
- Outreach mapping: `OUT-`
- Board sort: `BORD-`
- Exposure formula: `EXP-`
- Calendar policy: `CAL-`

### Account ID Convention

Account identifiers use the `acct_` prefix followed by a snake_case name (e.g., `acct_northstar_finance`).

### Date Formats

- Full dates: `YYYY-MM-DD`
- Months: `YYYY-MM`
- Quarters: `YYYY-QN` (e.g., `2026-Q2`)

### Sorting

- Risk-ranked lists: descending by risk score or churn probability (highest risk first), with rank starting at 1.
- Name-sorted lists: ascending by `customer_name` or `account_id`.

### General Workflow

1. Parse the prompt for all parameters (account IDs, date range, months, filters).
2. Load the answer template from `input/payloads/answer_template.json`.
3. Determine which endpoints are needed based on the template shape.
4. Call APIs sequentially or in parallel, collecting all required data.
5. Compute derived fields (averages, peaks, trends, win rates).
6. Determine controlled enum values by matching data patterns to vocabulary entries.
7. Assign policy codes following the prefix conventions and context.
8. Assemble the final JSON, validate against the template shape, and output.
