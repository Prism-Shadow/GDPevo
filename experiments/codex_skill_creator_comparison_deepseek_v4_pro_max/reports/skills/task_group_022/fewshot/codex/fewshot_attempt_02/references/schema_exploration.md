# Schema Exploration Patterns

## Fetching schema metadata

Always fetch both endpoints at the start:

```
GET /api/schema
Authorization: Bearer atlas-ops-token-022
```

```
GET /api/data-dictionary
Authorization: Bearer atlas-ops-token-022
```

The schema endpoint returns table names and column names with types.
The data-dictionary returns human-readable descriptions of each column's
business meaning.

## Understanding the data model

Tables are typically linked by shared keys:

- `order_id` links orders to shipments, refunds, and production tasks
- `shipment_id` links shipments to carrier scans
- `account_id` links accounts to support cases
- `warehouse_id` or `region` links location-scoped records to their facilities
- `campaign_id` links orders to campaigns

## Identifying effective and canonical columns

Some tables carry both raw source values and canonical/resolved values:

- A carrier scan may have `raw_status` (what the carrier reported) and
  `canonical_status` (the authoritative reconciled status)
- A refund may have a raw value and an "effective settled" indicator

Always use the canonical or effective column for business logic.
The raw column exists only for reference and must not drive
calculations, filtering, or classification.

## NULL semantics

NULL values carry business meaning. Common examples:

- An order with no shipments (no matching row in the shipments table):
  the order is incomplete
- A shipment with `NULL` promised_delivery_at: the shipment has no
  promise; it cannot satisfy time-based conditions
- A case with `NULL` first_response_at: the case has never been
  responded to; use elapsed time at cutoff for breach evaluation

Do not replace NULL with defaults unless the payload explicitly
instructs otherwise. NULL often changes classification branching.

## Exploring relationships

When two tables may be joined, verify the join produces expected
cardinality by running a count query first. One-to-many relationships
are common (one order → many shipments, one shipment → many scans).
Use subqueries or window functions to resolve to the relevant row
when the business rule needs a single record per entity.

### Resolving "latest" or "final" per group

When a business rule depends on the effective final state per entity
(e.g., effective final carrier status per shipment), use a window
function to rank rows within each group and filter to rank 1:

```sql
SELECT ...
FROM (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY shipment_id ORDER BY scan_at DESC) AS rn
  FROM carrier_scans
  WHERE canonical_status IS NOT NULL
) sub
WHERE rn = 1
```
