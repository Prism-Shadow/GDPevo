---
name: apexcloud-retention-ops
description: Use this skill for ApexCloud Retention Operations tasks that ask for account retention, churn-risk, support, NPS, revenue, renewal, or pipeline analysis from the remote GDPEVO environment. Trigger whenever the task mentions ApexCloud, accounts, ARR, CSM owners, lifecycle status, product usage, SLA, support tickets, NPS, opportunities, churn candidates, renewals, or asks for a computed business answer from the remote API.
---

# ApexCloud Retention Operations

Use the remote environment as the source of truth. Do not infer values from memory, train examples, or local repository files. These tasks are small enough to solve by fetching JSON, joining on `account_id`, applying explicit filters, and returning the requested fields exactly.

## Environment Access

Read `environment_access.md` first and set the base URL from `GDPEVO_ENV_BASE_URL`.

Known public endpoints observed in the train environment:

- `GET /api/health`: service status and dataset row counts.
- `GET /api/accounts`: all account master records.
- `GET /api/accounts/{account_id}`: one account master record.
- `GET /api/accounts/{account_id}/metrics`: monthly metrics for one account.
- `GET /api/accounts/{account_id}/tickets`: support tickets for one account.
- `GET /api/accounts/{account_id}/nps`: NPS responses for one account.
- `GET /api/opportunities`: all opportunities. Query parameters may be ignored; filter locally.

Endpoint habits:

- Probe with `GET` and expect JSON. Unrecognized routes return a JSON 404 with `No matching public endpoint`.
- Prefer fetching `/api/accounts` once, then looping over account IDs for nested collections.
- Filter locally after fetching. Do not assume server-side filters such as `?account_id=...`, `?state=open`, or date parameters work.
- Use account aliases only for name matching. After resolving an account name, join and report by canonical `account_id`, `display_name`, and/or `legal_name` as requested.

## Core Data Shapes

Account master records include:

- `account_id`, `display_name`, `legal_name`, `account_aliases`
- `segment`, `region`, `product_plan`, `lifecycle_status`
- `csm_owner`, `renewal_date`, `contract_tenure_months`
- `billing_arr_current`, `crm_arr`

Monthly metrics records include:

- `month` in `YYYY-MM`, `quarter` in `YYYY-Q#`
- `active_seats`, `product_usage`, `recognized_revenue`
- `nps_score`, `sla_compliance`, `support_ticket_count`, `survey_status`

Support ticket records include:

- `ticket_id`, `created_date`, `status`, `severity`, `product_area`
- `first_response_sla_met`, `resolution_sla_met`
- `is_spam`, `is_duplicate`

NPS response records include:

- `response_id`, `response_date`, `score`, `survey_channel`, `retracted`

Opportunity records include:

- `opportunity_id`, `account_id`, `account_legal_name`
- `amount`, `created_date`, `close_date`, `stage`, `state`
- `product_line`, `region`

## Reusable Workflow

1. Start with `/api/health` to confirm service availability and understand which collections exist.
2. Fetch `/api/accounts` and build:
   - `accounts_by_id`
   - normalized name/alias lookup using lowercase, punctuation-light aliases.
3. Identify the relevant account set from the prompt:
   - If the prompt names accounts, resolve names through `display_name`, `legal_name`, and `account_aliases`.
   - If it gives segments, regions, plans, owners, lifecycle statuses, renewal windows, or ARR thresholds, filter account records directly.
4. Fetch only the nested collections needed for those accounts:
   - Metrics for usage, NPS monthly trend, SLA, seats, revenue, and support-ticket-count calculations.
   - Tickets for severity, SLA misses, product area, duplicate/spam exclusions, and ticket status.
   - NPS for response-level averages, channels, date windows, and retraction exclusions.
5. Fetch `/api/opportunities` when the task mentions pipeline, expansion, product lines, close dates, stages, open/closed state, or opportunity amounts.
6. Join by `account_id`. Opportunity `account_legal_name` is useful display context but should not be the join key.
7. Apply time windows before aggregating. Dates are ISO-like strings, so lexical sort works for same-format dates, but use real date parsing for inclusive/exclusive boundary wording.
8. Compute with code for anything beyond a couple of rows. Keep raw values as floats until the final formatting step.
9. Return the exact output shape requested. If no shape is specified, use concise JSON with stable snake_case keys.

## Common Business Rules

Follow the prompt first. When it is silent, use these defaults because they match the data semantics:

- Exclude support tickets where `is_spam` or `is_duplicate` is true for operational ticket counts, SLA rates, severity mixes, and product-area analysis.
- Exclude retracted NPS responses from response-level NPS averages and counts.
- Exclude `cancelled` tickets from resolution-rate or backlog analyses unless the prompt asks for all statuses.
- For backlog/open-ticket counts, include `status == "open"` and still exclude spam/duplicates unless explicitly told otherwise.
- For pipeline analysis, use `state == "open"` unless the prompt asks for closed, won/lost, historical, or all opportunities.
- For won/lost analysis, use `stage` values like `Closed Won` and `Closed Lost`; do not treat every `state == "closed"` opportunity as won.
- For account eligibility, preserve lifecycle semantics. `active`, `renewal_risk`, `implementation`, and `paused` are distinct; do not collapse them unless the prompt says active customers broadly.
- For ARR questions, distinguish `billing_arr_current` from `crm_arr`. If the prompt does not specify CRM ARR, default to current billing ARR and say so briefly.
- For monthly metric trends, use `month` order from `2026-01` through `2026-12`; for quarters, group by the provided `quarter` field.
- For renewal windows, treat `renewal_date` as an account-level date. Be explicit about inclusive boundaries if the prompt gives "between", "through", or "next N days".

## Output Conventions

When the task provides a schema, match it exactly.

When the task does not provide a schema, prefer:

```json
{
  "answer": "...",
  "accounts": [
    {
      "account_id": "...",
      "display_name": "...",
      "metric_name": 0
    }
  ],
  "assumptions": [
    "Excluded spam and duplicate tickets.",
    "Excluded retracted NPS responses."
  ]
}
```

Formatting rules:

- Use `account_id` for machine-readable identity and `display_name` for human-readable account names.
- Keep IDs exactly as returned, such as `acct_...`, `TCK-...`, `NPS-...`, and `OPP-...`.
- Round currency and ARR only at the end. Use two decimals for money unless the prompt requests whole dollars.
- Round rates and percentages consistently, usually to two decimals. State whether a value is a percent or a fraction.
- Sort ranked lists by the requested metric descending, then by `display_name` or `account_id` ascending for deterministic tie breaks.
- Include counts used in denominators when reporting rates if the prompt allows it; this makes exclusions auditable.
- If returning CSV-like or table output, preserve requested column order and use canonical field names.

## Pitfalls

- Do not read local `env/`, `runs/`, evaluator, judge, report, or other answer-bearing files. This task is solved from the remote API only.
- Do not use train gold answers, validation labels, or judge feedback. If such material appears, stop and report contamination.
- Do not rely on `/api/opportunities` query parameters; fetch all opportunities and filter in your own code.
- Do not assume every dataset named in `/api/health` has a top-level route with the same name. Some data is exposed through nested account endpoints.
- Do not count spam, duplicate, retracted, or cancelled records accidentally. These flags are easy to miss and often change the answer.
- Do not join accounts by display name alone. Aliases and legal names vary; resolve once, then use `account_id`.
- Do not confuse monthly `nps_score` in metrics with response-level NPS rows. Use metrics for month-level trend questions; use `/nps` responses for survey-response questions.
- Do not mix current ARR fields. `billing_arr_current` and `crm_arr` can differ.
- Do not assume "closed" means "won" for opportunities. Check `stage`.
- Do not hard-code observed train account names, counts, or computed values into answers. Fetch live data each time.

## Minimal Code Pattern

Use a short script or notebook-style snippet for repeatable calculations:

```python
import json
import urllib.request

BASE = "<environment_base_url>"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as response:
        return json.load(response)

accounts = get("/api/accounts")["accounts"]
accounts_by_id = {a["account_id"]: a for a in accounts}
opportunities = get("/api/opportunities")["opportunities"]

def metrics(account_id):
    return get(f"/api/accounts/{account_id}/metrics")["metrics"]

def tickets(account_id, clean=True):
    rows = get(f"/api/accounts/{account_id}/tickets")["tickets"]
    if clean:
        rows = [r for r in rows if not r["is_spam"] and not r["is_duplicate"]]
    return rows

def nps(account_id, clean=True):
    rows = get(f"/api/accounts/{account_id}/nps")["nps_responses"]
    if clean:
        rows = [r for r in rows if not r["retracted"]]
    return rows
```

Adapt the code to the requested calculation, then answer with the requested schema and a brief note for any default exclusions applied.
