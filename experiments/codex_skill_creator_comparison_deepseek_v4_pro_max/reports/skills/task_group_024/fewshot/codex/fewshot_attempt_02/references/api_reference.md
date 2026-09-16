# API Reference

## Work Item Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier, e.g. WI-24024-P001 |
| title | string | Human-readable title |
| work_type | string | One of: Feature, Enhancement, Bug, Incident, Security, Compliance, Reliability, Refactor, Chore, Dependency |
| status | string | Current state: Closed, Verified, Done, Deployed, Review, In Progress, Backlog, Open, Duplicate, Cancelled |
| team | string | Owning engineering team |
| owner | string|null | Assigned owner name; null when unassigned |
| product_area | string | Product area |
| created_at | date | YYYY-MM-DD |
| due_at | date | YYYY-MM-DD |
| closed_at | date|null | YYYY-MM-DD; null when not yet closed |
| severity | string | S1, S2, S3, S4 |
| priority | integer | 1 (highest) to 4 (lowest) |
| labels | JSON array string | e.g. ["security","cve","auth"] |
| story_points | integer | Effort estimate |
| release_id | string|null | Parent release |
| milestone_id | string|null | Parent milestone |
| duplicate_of | string|null | ID of the canonical record this duplicates |
| mirror_status | string | STALE - do not use for decisions |
| legacy_category | string | STALE - do not use for classification |

## Status Semantics

### Closed Terminal States (complete, resolved, shipped)
Closed, Verified, Done, Deployed

These indicate a work item has reached a finished state. Items in these states are counted as complete for milestone/release readiness.

### Active/Non-Terminal States (still in flight)
Review, In Progress, Backlog, Open

These items are still active. They can be overdue for SLA calculations if their age exceeds the SLA window.

### Exclusion States (never count as primary)
Duplicate - references another item via duplicate_of field
Cancelled - work cancelled, never completed

## Mix Target Fields

| Field | Type |
|-------|------|
| scope_id | string |
| quarter | string |
| team_group | string |
| product_area | string |
| new_feature_pct | number (0-1 decimal) |
| tech_debt_pct | number (0-1 decimal) |
| reliability_pct | number (0-1 decimal) |
| security_pct | number (0-1 decimal) |

Multiply decimal values by 100 to get percentage points.

## SLA Policy

| Severity | days_to_due |
|----------|-------------|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

## Release Fields

| Field | Type |
|-------|------|
| id | string |
| name | string |
| target_date | date |
| train | string |

## Milestone Fields

| Field | Type |
|-------|------|
| id | string |
| name | string |
| owner_team | string |
| release_id | string |

## Blocker Fields

| Field | Type |
|-------|------|
| id | string |
| cause | string |
| opened_at | date |
| resolved_at | date|null |
| severity | Low, Medium, High, Critical |
| status | Open, Monitoring, Resolved |
| work_item_id | string |
| release_id | string |

## Dependency Fields

| Field | Type |
|-------|------|
| blocked_id | string |
| depends_on_id | string |
| relation | string: depends-on, blocks-release-readiness, security-review-required, validation-required, audit-evidence-required, implementation-dependency |

## SQL Query Endpoint

POST /api/query
Headers: Content-Type: application/json, X-Env-Token: portfolio-readonly
Body: {"sql": "...", "params": [...]}

The work_items table supports SELECT and WITH. Parameters use ? placeholders.

### Scope Work Items
{"sql": "SELECT id, work_type, labels, status, duplicate_of, team, product_area, closed_at, title, owner, severity, created_at, due_at, milestone_id, release_id FROM work_items WHERE team IN (?,?) AND product_area IN (?,?) ORDER BY id", "params": ["Platform Core", "Identity Services", "Atlas Backend", "Identity"]}

### Release Work Items
{"sql": "SELECT id, work_type, labels, status, duplicate_of, team, product_area, milestone_id, title, owner FROM work_items WHERE release_id = ? ORDER BY id", "params": ["REL-ORION-2026-02"]}

### Individual Item
{"sql": "SELECT * FROM work_items WHERE id = ?", "params": ["WI-24024-P001"]}
