## When to Use This Skill

Use this skill whenever you need to interact with the ApexCloud Retention Operations API to produce structured retention deliverables: risk queues, QBR metrics packets, collections dossiers, churn model validations, or retention action boards. The skill encodes the reusable access model, endpoint map, controlled vocabularies, numeric precision conventions, and common output patterns observed across the five canonical task families.

---

## API Connectivity

1. Obtain the environment base URL from `<TASK_ENV_BASE_URL>` as provided in the task prompt, or from the `GDPEVO_ENV_BASE_URL` value listed in `environment_access.md`.
2. No authentication headers are required.
3. Only `GET` requests are allowed.
4. Append endpoint paths directly to the base URL. Query strings may be used when an endpoint supports filters (e.g., `?start=YYYY-MM&end=YYYY-MM`).

### Endpoint Map

```
GET /api/accounts
GET /api/accounts/{account_id}
GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM
GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD
GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD
GET /api/accounts/{account_id}/billing
GET /api/accounts/{account_id}/ar-aging
GET /api/billing/snapshots
GET /api/finance/ar-aging
GET /api/opportunities
GET /api/hr/summary
GET /api/events/performance
GET /exports/churn/train.csv
GET /exports/churn/validation.csv
GET /exports/churn/candidates.csv
GET /exports/account_metric_extract.csv
```

---

## Data Fetching Strategy

### Account Profiling
- Use `GET /api/accounts` to obtain the full account list.
- Use `GET /api/accounts/{account_id}` for per-account profile fields (legal name, segment, tenure, lifecycle stage, renewal date).

### Financial Data
- **ARR / Revenue**: Use `GET /api/accounts/{account_id}/billing` and cross-reference with `GET /api/billing/snapshots`. When `uses_billing_arr_source` is needed, set it to `true` if billing snapshots are the primary ARR source.
- **A/R Aging**: Use `GET /api/accounts/{account_id}/ar-aging` and `GET /api/finance/ar-aging` for overdue balance and aging buckets.
- **Expansion Pipeline**: Use `GET /api/opportunities` and filter by close date within the analysis period.

### Customer Health
- **Metrics**: Use `GET /api/accounts/{account_id}/metrics?start=YYYY-MM&end=YYYY-MM` for usage trend and product consumption data.
- **Support Tickets**: Use `GET /api/accounts/{account_id}/tickets?start=YYYY-MM-DD&end=YYYY-MM-DD` for ticket volume, SLA compliance, and hygiene.
- **NPS**: Use `GET /api/accounts/{account_id}/nps?start=YYYY-MM-DD&end=YYYY-MM-DD` for sentiment scores. NPS scores are returned as integers.

### Operations Context
- Use `GET /api/hr/summary` for headcount and unpaid claims.
- Use `GET /api/events/performance` for event orders and event revenue.

### Churn Datasets
- Use `GET /exports/churn/train.csv` and `GET /exports/churn/validation.csv` as CSV exports for model validation reads.
- Use `GET /exports/churn/candidates.csv` for candidate account churn probabilities.
- Use `GET /exports/account_metric_extract.csv` for bulk metric extracts.

---

## Numeric Precision (Deterministic)

| Measure          | Precision              |
|------------------|------------------------|
| Currency / ARR   | 2 decimal places       |
| Percentages      | 1 decimal place        |
| Counts           | Integers               |
| Risk scores      | Integers               |
| NPS scores       | Integers               |
| Churn probability| 3 decimal places       |

---

## Output Formatting Rules

1. **Always return valid JSON only** — no explanatory text outside the JSON object.
2. Follow the schema from the provided `answer_template.json` exactly. Do not add or remove top-level keys.
3. Use controlled enum values (see `reference/vocabulary.md`) for every field that accepts them. Never invent new enum values.
4. Month strings use `YYYY-MM` format. Dates use `YYYY-MM-DD` format.
5. Lists must appear in the order specified by the task (e.g., ranked by risk, by churn probability, or by standard board order).
6. `null` is valid for fields like `nps_score` or `account_id` when the underlying data is absent. Use `null`, not `0` or empty string, for genuinely missing values unless the template explicitly defaults to `0` or `""`.

---

## Workflow Patterns

### Pattern A — Risk Queue (like train_001, train_005)
1. Fetch all accounts. Filter to the provided account_id list.
2. For each account, fetch its billing, metrics, tickets, NPS, and A/R aging data.
3. Compute a risk score from: overdue balance, NPS trend, SLA degradation, usage decline, low tenure, and renewal proximity.
4. Assign a `risk_level` (critical, high, medium, low) and a `primary_action`.
5. Attach `reason_codes` that explain the risk classification.
6. Sort accounts by risk score descending and return the top N (typically 5 or all).
7. Compute portfolio summary aggregates (accounts reviewed, critical/high count, ARR at risk, collections count, technical recovery count).
8. Populate `model_checks` or `policy_codes` as the template requires.

### Pattern B — QBR Metrics Packet (like train_002)
1. Fetch the target account profile.
2. For each month in the analysis period, fetch metrics, tickets, and NPS.
3. Build per-month rows with revenue, ticket count, SLA compliance %, and NPS score.
4. Compute highlights: average revenue, peak revenue month/value, max SLA month/%, peak NPS month/score, and ticket trend (improving/worsening/flat).
5. Assign metric sources from the source enum vocabulary.
6. Populate the review_plan and select 4 ordered agenda topics.

### Pattern C — Collections Dossier (like train_003)
1. Fetch billing snapshots and A/R aging for the period.
2. Identify accounts with overdue balances and past-due receivables.
3. Cross-reference with CRM opportunities for expansion pipeline context.
4. Build aging tiers and compute ad-hoc collections metrics.
5. Match overdue accounts to CRM opportunity records by legal name.
6. Populate overdue_followups with due dates and primary actions.
7. Include ops_context from HR summary and event performance endpoints.

### Pattern D — Churn Model Validation (like train_004)
1. Fetch and parse `/exports/churn/train.csv` — count rows and features.
2. Fetch and parse `/exports/churn/validation.csv` — count rows, compute accuracy.
3. Report accuracy band (below_70, 70_to_79, 80_to_89, 90_plus).
4. Determine tenure coefficient direction (negative, positive, zero).
5. Fetch `/exports/churn/candidates.csv` and filter to the requested candidate accounts.
6. Rank by predicted churn probability descending.
7. Assign outreach_action and reason_code per candidate.
8. Populate cohort_checks: past_due_shortlist_count, low_tenure_shortlist_count, average_probability_top5.

### Pattern E — Retention Action Board (like train_005)
1. Fetch all accounts and filter to the provided account_id list.
2. For each account, reconcile: profile, billing, support tickets, NPS, A/R aging, and expansion opportunities.
3. Compute risk level, primary action, ARR, expansion pipeline, overdue balance, and reason codes.
4. Assign next_touch_due_date based on primary_action using the follow-up calendar.
5. Sort in standard retention board order (by risk descending).
6. Compute segment_summary: strategic vs enterprise counts, ARR at risk, open expansion pipeline, net revenue exposure.
7. Populate followup_calendar with the provided due dates for each action type.

---

## Referenced Files

- `reference/vocabulary.md` — Complete controlled enum vocabulary for risk levels, actions, reason codes, metric sources, review owners, agenda topics, policy codes, accuracy bands, and more.
