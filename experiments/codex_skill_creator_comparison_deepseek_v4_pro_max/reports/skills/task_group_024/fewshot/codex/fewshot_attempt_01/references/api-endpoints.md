# API Endpoints Reference

The task environment exposes REST endpoints at `<TASK_ENV_BASE_URL>`. Always read `environment_access.md` first to confirm which endpoints are active for the current task.

## GET /api/work-items

Returns a paginated list of work items. May support query parameters for filtering.

Typical response structure:

```json
{
  "items": [
    {
      "id": "WI-24024-A001",
      "title": "string",
      "status": "string (e.g. Closed, Open, In Progress, Cancelled, Duplicate)",
      "portfolio_category": "string (NewFeature, TechDebt, Reliability, Security)",
      "severity": "string (S1, S2, S3, S4)",
      "team": "string",
      "product_area": "string",
      "quarter": "string (e.g. 2025-Q4)",
      "owner": "string or null",
      "created_at": "ISO-8601 date string",
      "closed_at": "ISO-8601 date string or null",
      "duplicate_of": "string work item id or null",
      "canonical_id": "string work item id or null",
      "release_id": "string or null",
      "milestone_id": "string or null",
      "mirror_status": "string (stale mirror field, ignore)",
      "legacy_category": "string (stale legacy field, ignore)"
    }
  ],
  "total": "integer",
  "next": "string URL or null"
}
```

### Key pointers

- `id` is the canonical work item identifier.
- `status` is authoritative for lifecycle state; ignore `mirror_status`.
- `portfolio_category` is authoritative for portfolio classification; ignore `legacy_category`.
- `duplicate_of` or `canonical_id` points to the primary work item when this record is a duplicate.
- `closed_at` is null for open items. For SLA audits, items closed within the recent window are considered handled.

## GET /api/work-items/{item_id}

Returns a single work item with the same schema as items in the list response.

## GET /api/mix-targets

Returns an array of mix target rows with scope-level target percentages.

Typical response:

```json
[
  {
    "scope_id": "string (e.g. train_001)",
    "quarter": "string (e.g. 2025-Q4)",
    "target_pct": {
      "NewFeature": 40.0,
      "TechDebt": 25.0,
      "Reliability": 20.0,
      "Security": 15.0
    }
  }
]
```

All four categories are always present. Target percentages sum to 100.0.

## GET /api/sla-policy

Returns SLA response-time thresholds by severity.

Typical response:

```json
{
  "thresholds": {
    "S1": 1,
    "S2": 3,
    "S3": 7,
    "S4": 14
  }
}
```

The values are maximum allowed response days. A work item is overdue if `days_open > threshold_days`.

## GET /api/releases

Returns a list of releases.

## GET /api/releases/{release_id}

Returns a single release with its milestone links.

Typical response:

```json
{
  "id": "REL-MERCURY-2026-01",
  "name": "string",
  "status": "string",
  "milestone_ids": ["MIL-MERCURY-BETA", "MIL-MERCURY-RC", "MIL-MERCURY-GA", "MIL-MERCURY-HARDEN"]
}
```

## GET /api/milestones

Returns milestone definitions. Each milestone has an `id` field.

## GET /api/dependencies

Returns work-item dependency relationships.

Typical response:

```json
[
  {
    "from_id": "WI-24024-AAA",
    "to_id": "WI-24024-BBB",
    "type": "blocks"
  }
]
```

`from_id` depends on `to_id`: the work item with `from_id` is blocked until `to_id` completes.

## GET /api/blockers

Returns blocker records.

Typical response:

```json
[
  {
    "work_item_id": "WI-24024-AAA",
    "cause": "string (exact cause text)",
    "impact": "string (e.g. high, medium, low)",
    "resolved": "boolean"
  }
]
```

For release readiness, only count unresolved (`resolved: false`) high-impact (`impact: "high"`) blockers.

## POST /api/query

Accepts a restricted SQL query. Use only when GET endpoints do not provide the necessary data. The query token may be required.

Request body:

```json
{
  "query": "SELECT ... FROM ... WHERE ..."
}
```

Response contains query results as an array of rows.
