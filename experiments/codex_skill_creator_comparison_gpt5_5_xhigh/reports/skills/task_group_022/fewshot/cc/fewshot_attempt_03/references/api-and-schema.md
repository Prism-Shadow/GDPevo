# API and Schema

Use the task prompt's base URL or `TASK_ENV_BASE_URL` when present. Authentication uses a bearer token from `TASK_ENV_API_TOKEN`.

```bash
curl -sS -H "Authorization: Bearer ${TASK_ENV_API_TOKEN}" "$TASK_ENV_BASE_URL/api/schema"
curl -sS -H "Authorization: Bearer ${TASK_ENV_API_TOKEN}" "$TASK_ENV_BASE_URL/api/data-dictionary"
```

Read-only SQL:

```bash
curl -sS \
  -H "Authorization: Bearer ${TASK_ENV_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select 1 as ok"}' \
  "$TASK_ENV_BASE_URL/api/sql"
```

The SQL endpoint returns `columns`, `rows`, `row_count`, and `truncated`. Keep queries small while exploring, then run aggregate/final queries.

## Main Tables

- `accounts`: account master data with `segment`, `tier`, `region`, `currency`, `is_internal`, and `is_test`.
- `campaigns`: campaign active windows.
- `orders`, `order_lines`, `order_events`: order headers, lines, and lifecycle events.
- `shipments`, `carrier_scans`: shipment headers and raw/canonical carrier observations.
- `refund_attempts`, `payment_events`, `fx_rates`: refund attempts, payment events, and daily USD FX.
- `warehouse_tasks`, `warehouse_task_events`, `employees`, `warehouses`: warehouse work, task events, staffing, and facilities.
- `support_cases`, `case_events`: support case headers and lifecycle events.
- `inventory_movements`, `inventory_snapshots`, `products`: stock movements, snapshots, and SKU metadata.
- `correction_audit`: public audit rows for controlled canonical corrections.

## Reusable SQL Patterns

Deduplicate imported event/source tables:

```sql
with ranked as (
  select
    t.*,
    row_number() over (
      partition by source_system, external_event_id
      order by ingested_at desc
    ) as rn
  from table_name t
)
select *
from ranked
where rn = 1
```

Find the latest event at or before a cutoff:

```sql
with ranked as (
  select
    e.*,
    row_number() over (
      partition by entity_id
      order by event_at desc, stable_event_id desc
    ) as rn
  from event_table e
  where event_at <= :cutoff_at
)
select *
from ranked
where rn = 1
```

Convert minor currency units to USD:

```sql
(amount_minor / 100.0) * fx.usd_per_unit
```

Join `fx_rates` on the row's business date and currency, not query time.

## Controlled Corrections

Use transactions only when the prompt and request payload explicitly approve mutation. The approved pattern is one canonical field update plus one `correction_audit` insert in a single transaction.

Before mutating:

- Identify the single target row with a read-only query.
- Confirm old value, proposed new value, source row ID, business entity ID, and field name.
- Confirm the request's approved `audit_id`, `correction_key`, actor, reason code, and corrected timestamp.

After mutating:

- Verify affected business-row count and audit-row count.
- Requery the target canonical value.
- Read the audit row through the available audit view or table.
- Report `APPLIED` only if the request's success rule is fully met; otherwise report `NOT_APPLIED` with the observed counts and values.

Do not update raw fields such as `raw_status`, source identity fields such as `source_system` or `external_event_id`, or unrelated rows.
