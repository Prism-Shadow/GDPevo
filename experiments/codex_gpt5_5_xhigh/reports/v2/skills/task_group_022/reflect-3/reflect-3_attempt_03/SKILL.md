---
name: sql-database-analytics
description: Solve SQL database analytics tasks over a remote operations analytics API. Use for tasks that ask Codex to inspect schemas, query SQLite-backed business data, compute usage/support/incident rollups, apply approved data-quality corrections through simulation, and return strict JSON outputs with deterministic ordering and rounding.
---

# SQL Database Analytics

## API Workflow

1. Read the prompt and answer template first. Treat template text such as ordering notes or type descriptions as instructions, not output keys, unless it is clearly a requested data field.
2. Use the task's API base URL. Start with `GET /health`, `GET /schema`, and `GET /tables`; sample rows only when schema is not enough.
3. Query with `POST /query` using JSON `{"sql": "...", "params": []}`. Prefer CTEs that name candidate, exclusion, and qualified populations.
4. Map product names through `products`; read `metric_notes` for reusable business definitions.
5. Build a candidate query first, then separate queries for:
   - qualified rows,
   - exclusion counts,
   - grouped output rows,
   - tie-break ordering checks,
   - independent total checks.
6. Use half-open timestamp windows: `created_at >= start AND created_at < next_period_start`. Use inclusive date filters for date-only columns such as `activity_date`.

## Usage Metrics

Qualified customer usage usually means:

- `usage_daily.product_id` matches the requested product.
- `environment = 'production'`.
- `is_backfill = 0`.
- account is external and current for usage exposure: `accounts.is_internal = 0` and `account_status IN ('active','paused')`.
- when the task says active product subscriptions, enterprise customers, or incident exposure for subscribed accounts, require a subscription active on the usage date:
  `s.start_date <= activity_date AND (s.end_date IS NULL OR s.end_date >= activity_date)`.
- when enterprise eligibility is requested for usage, check `subscriptions.plan_code = 'enterprise'` before falling back to `accounts.segment = 'enterprise'`; subscription plan is often the actual entitlement.
- for incident regional exposure, use the incident record's product, started/resolved timestamps, and impacted region; `GLOBAL` means no regional restriction.

Telemetry overlap rule: exclude `telemetry_v1` production rows when the same account, product, activity date, environment, and non-backfill condition also has `telemetry_v2` or `import_patch`. Count overlap exclusions independently when requested.

Aggregate after filtering; round final numeric metrics, not intermediate rows. Compute-hour outputs use two decimals unless the template says otherwise.

## Support Ticket Metrics

Customer-impacting defect tickets usually require:

- product match and requested time window on `created_at`;
- external/non-test account: `accounts.is_internal = 0` and `account_status <> 'test'` for historical support rollups; use active/paused only when the prompt explicitly asks for current active customers;
- `customer_impact = 1`;
- `status <> 'canceled'`;
- exclude duplicates with `is_duplicate = 0` and, after corrections, also ensure `duplicate_of IS NULL` when duplicate status is represented that way;
- defect categories are `bug`, `outage`, `performance`, and `data_loss`.

Incident follow-up support signals are not automatically defect-only. If the template has canceled/duplicate and customer-impact exclusions but no non-defect exclusion, include all customer-impacting support categories after removing canceled/duplicate tickets.

SLA breach rule: closed tickets breach when `closed_at > sla_due_at`; open or in-progress tickets breach when their `sla_due_at` has passed. Median close hours uses only closed qualified tickets, sorted by duration, with the middle two averaged for even counts.

For backlog tasks, define the backlog population explicitly before aggregating: normally `status IN ('open','in_progress')`. If the prompt says a month but does not say "created from", compare created-in-month versus as-of-cutoff interpretations before finalizing.

## Data-Quality Corrections

Never apply updates to the real database. Use `POST /simulate` with a deterministic update script and read-only follow-up queries.

Safe correction workflow:

1. Read the exact `data_quality_cases` row by `case_id`.
2. Require `case_status = 'approved'`, expected `case_type`, `target_table`, and `field_name`.
3. Restrict updates to `target_ids_csv` and the expected old value/current blank value.
4. Populate `audit_reason` from the case and `audit_updated_at` from the case timestamp or another deterministic task-specified timestamp; avoid `CURRENT_TIMESTAMP`.
5. For usage product corrections, update only the target `usage_daily.product_id` from old to new.
6. For ticket duplicate corrections, set `duplicate_of` to the approved master and set `is_duplicate = 1` when downstream metrics use that flag.
7. Use simulation `changed_rows` as the changed count, then recompute all metrics from the simulated database.

## Output Habits

- Return only the JSON object requested.
- Keep all required zero-valued severity keys such as `P1`, `P2`, `P3`, `P4`.
- Sort deterministically:
  - IDs ascending for ID lists and account breakdowns unless told otherwise.
  - top lists by descending metric, then ascending stable ID.
  - regions alphabetically.
  - account notification lists by the template's priority rule; convert severity to `P1=1, P2=2, P3=3, P4=4`.
- For exclusion counts, use independent diagnostics unless the prompt explicitly asks for sequential buckets. Independent counts can overlap and need not sum to candidate minus qualified.
- Cross-check totals against detail rows before finalizing.

## Common Mistakes

- Using account segment alone when subscription eligibility is required.
- Forgetting to exclude `telemetry_v1` overlap rows in qualified usage.
- Counting exclusion buckets sequentially when the task expects independent counters.
- Including template instruction keys such as ordering notes in the final JSON.
- Treating open overdue tickets as non-breaches.
- Applying draft/rejected DQ cases or writing an update that is not case-gated.
- Using nondeterministic audit timestamps.
- Sorting ties by display name instead of stable IDs.
