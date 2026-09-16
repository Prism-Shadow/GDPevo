# Atlas Commerce Operations Patterns

Use these patterns after reading the live schema and data dictionary. The request payload remains authoritative when it differs from a pattern below.

## API And Data Conventions

- Base URL usually comes from `TASK_ENV_BASE_URL` or `environment_access.md`; bearer auth uses the env var named there, usually `TASK_ENV_API_TOKEN`.
- Endpoints: `GET /api/schema`, `GET /api/data-dictionary`, `POST /api/sql`, `POST /api/sql/transaction`, and `GET /api/correction-audit`.
- `POST /api/sql` accepts `{"sql": "select ..."}` and returns `columns`, `rows`, `row_count`, and `truncated`.
- Stored timestamps are ISO-8601 UTC text. Compare request boundaries as text only when they use the same normalized `Z` format.
- Monetary amount columns ending in `_minor` are minor units. Convert to major units before FX multiplication, and join `fx_rates` on the row's service date and currency.
- Source import rows may contain retries. For logical entities, deduplicate by the request's logical key and source identity, keeping the latest effective ingested/event copy. For raw-row correction tasks, preserve the stable source row ID.

## Cohorts

- Start with the narrow business entity named by the request: orders, shipments, refund attempts, warehouse tasks, support cases, inventory movements, or accounts.
- Apply time windows exactly. Inclusive end boundaries use `<= end`; strict lateness checks usually use `< cutoff` or `> threshold` exactly as written.
- For production account scope, join `accounts` and require `is_internal = 0` and `is_test = 0`.
- For campaign cohorts, join `campaigns` and use the campaign active window, not only the supplied campaign ID.

## Cutoff State

- For event tables, compute the latest event at or before the cutoff with `row_number() over (partition by id order by event_at desc, stable_event_id desc) = 1`.
- For carrier scans, compute shipment state from latest effective `canonical_status` at or before the cutoff, ordered by `canonical_event_at` and `scan_row_id`.
- For warehouse tasks and support cases, prefer event history for cutoff state when the metric says active, completed by cutoff, reopened at cutoff, or not completed by cutoff.
- Treat missing effective child rows deliberately. For example, an order that requires physical shipment completion is incomplete when it has no shipment.

## Fulfillment Metrics

- Eligible production orders usually join `orders`, `campaigns`, `warehouses`, `accounts`, and `shipments`.
- An order complete by cutoff requires at least one physical shipment and every shipment's effective final carrier status to be delivered by cutoff.
- On-time completion requires every associated shipment's delivered timestamp to be at or before its promised delivery timestamp.
- Severe exception logic often has two branches: incomplete beyond a promise-plus-grace cutoff, or completed with any shipment delivered beyond the grace threshold. Keep branches as boolean columns to make auditing easier.
- Regional rates use the same numerator and denominator as the overall rate, partitioned by warehouse region; order worst regions by unrounded rate, then region.

## Refund Reconciliation

- Separate logical refunds from physical attempt rows. Use the request's status policy to include settled/effective refunds and exclude failed or voided attempts.
- Treat linked reversals through `linked_refund_id` and subtract their USD value from the linked logical refund.
- Compute order-level net refund USD after reversals; join order gross value to the FX rate for the comparison date required by the request.
- Reason rankings use effective net USD by normalized reason code, with the payload's tie-breaker.
- Leakage candidates can come from more than one rule. Use `distinct order_id` after unioning the candidate rules, then sort as requested.

## Carrier Quality Corrections

- Use the named import batch, warehouse, cutoff, and production-shipment scope to find raw/canonical contradictions.
- Keep source identity and raw fields immutable. The minimal approved change in these tasks is the canonical operational value named by the request.
- Compute pre-correction backlog before mutating. After the transaction, recompute the same backlog and delivered counts from the same CTE structure.
- Success requires the business-row count, audit-row count, and post-change canonical value to match the request's rule.

## Warehouse Productivity

- Eligible tasks usually filter `warehouse_tasks` by warehouse, work class, and created window.
- Completed production units and productive minutes come from completion event rows attached to eligible tasks that completed by the state cutoff.
- Employee units per hour is employee-level completed units divided by productive minutes, multiplied by 60. Rank by unrounded units per hour, then employee ID.
- Rework rate counts distinct eligible tasks with rework state/event evidence divided by eligible tasks.
- Delayed high-priority tasks are HIGH or URGENT tasks due strictly before the cutoff that are not completed by the cutoff.
- Lowest-performing teams use completion rate by employee team, with the request's tie-breaker.

## Support Health

- Join support cases to production accounts and filter account segment/region plus the case opened window.
- Active at cutoff includes cases whose cutoff state is open or reopened. Reopened-at-cutoff is the reopened subset.
- First-response breach uses active elapsed time until first agent response; if no agent response exists, measure active elapsed time through the cutoff.
- Resolution breach uses active time to resolution; for active cases, measure active elapsed time through the cutoff.
- Model support active time from event intervals. Waiting-on-customer states pause the active clock; customer reply, reopen, assignment, agent response, escalation, and open states resume it until resolution or cutoff.
- Severe active cases are active at cutoff, priority urgent/high, and beyond the priority resolution threshold. Rank worst accounts by severe active case count, active-clock breach count, then account ID.
- Median active resolution hours is across cases resolved by the cutoff; for an even count average the two middle active-time values before final rounding.

## Output Assembly

- Build JSON from the template's required keys in order. Use arrays of objects only where the template requires them.
- Apply exact enum policies after metric computation, using unrounded rates for threshold comparisons unless the request says otherwise.
- Use `json.dumps(..., indent=2)` or equivalent, but ensure the file contains only the JSON object.
