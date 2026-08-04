---
name: licensing-review
description: >
  Structured licensing review for contractor, liquor, and alcohol regulatory
  domains. Use when the task involves batch eligibility review of contractor
  applications, single-application liquor license staff packages, or
  pre-release alcohol renewal screening queues against a shared licensing
  data environment accessed via REST API and SQL endpoints.
---

# Licensing Review

This skill covers three regulatory review workflows backed by a shared data
environment. Always start by fetching the policies baseline, then gather
domain records before making any determination.

## Environment Initialization

Base URL defaults to `http://task-env:9019`. Use `<TASK_ENV_BASE_URL>` from
the task prompt when present.

SQL queries sent to `POST /api/sql` require:

```
X-Task-Token: licensing-review-019
Content-Type: application/json
```

Body format: `{"query": "<SELECT>", "params": ["v1", ...], "limit": <int>}`

GET endpoints are unauthenticated. Discover tables first:

```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name
```

Inspect columns with `PRAGMA table_info(<table>)` before writing domain queries.

## Workflows

### Contractor Batch Review

Fetch these endpoints, then cross-reference each target application:

- `GET /api/policies`
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`
- `POST /api/sql`

**Determination logic:**

- Active license suspension → `DENY`
- Bond cancelled or coverage shortfall → `HOLD` (fixable) or `DENY` (unfixable)
- Insurance expired relative to review date or coverage shortfall → `HOLD` or `DENY`
- Missing or pending specialty endorsement → `HOLD`
- Experience documentation shortfall → `HOLD`
- Open serious violation → `DENY`; open minor violation → `HOLD`
- Inspection document gap or safety recheck → `HOLD`
- Stale/unverified correspondence → flag in summary

After assigning deficiencies per application, set `risk_tier` (`low`/`medium`/`high`)
based on deficiency count and severity, then assign `determination` (`APPROVE`/`HOLD`/`DENY`).

If the current policy baseline creates a deficiency that would not exist under
the prior baseline, set `policy_impacted: true`.

Build the summary with approve/hold/deny counts, high-risk IDs, policy-impacted IDs,
and stale correspondence IDs. All must be consistent with individual decisions.

Detailed determination codes and deficiency mapping are in
[references/determinations.md](references/determinations.md).

### Liquor License Staff Package (Single Application)

Fetch these endpoints for the target application and location:

- `GET /api/policies`
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`
- `POST /api/sql`

**Posture:** `issue_restricted`, `request_follow_up`, or `deny` — based on whether
risks are covered by controls, gaps are verifiable, and disqualifying factors exist.

**Same-premises basis:** True when the location has prior licensing history that
informs the current evaluation.

**Risk codes** (covered by current controls): `AFTER_HOURS`, `ASSAULT`,
`MINOR_SALE`, `NOISE`, `PUBLIC_SAFETY`, `TAX_HOLD`, `FOOD_SERVICE_GAP`,
`SAME_PREMISES`, `SALE_TO_MINOR`. For hotel-lounge contexts also:
`CAMERA_COVERAGE`, `ID_CHECK`, `PATIO_BOUNDARY`.

**Verification gaps:** What evidence is missing (camera footage, food-service
evidence, floor plans, tax clearance, site photos, neighbor notices, signage).

**Obligations vs. controls:** Separate standard class obligations (`ID_CHECK`,
`HOURS`, `SECURITY`, `FOOD_SERVICE`, `CCTV`, `PATIO`, `NOISE`, `DELIVERY`)
from location-specific active controls (same code pool, but only those actively
tied to this location).

**First-90-day plan:** Sequenced check objects with `check_code` and `timing`
(`first_30_days`, `days_31_60`, `days_61_90`). Define escalation triggers for
field staff.

### Alcohol Renewal Queue

Fetch:

- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`
- `POST /api/sql`

Fetch renewal rules for release boundary and queue size. For each target
licensee, match violations by licensee ID. Rank by descending risk: higher
violation count and more recent violations rank higher; serious violations
weigh more than minor. Compute match confidence from data completeness and
recency. Assign risk tier and next-step label. Return exactly the target
queue size ordered by rank.

## Output Rules

1. Match the answer template exactly — every key present, no extra keys.
2. Use only enum values listed in the template's `allowed_values`.
3. Follow ordering rules (ascending, lexical) where specified.
4. Use `[]` for empty code arrays, never `null`.
5. No prose, markdown, or citations outside the JSON structure.
6. Batch summaries must reconcile with individual application decisions.

## SQL Patterns

- Use parameterized queries: `{"query": "...", "params": ["v1"]}`, never string interpolation.
- Filter by IDs: `WHERE application_id IN (?, ?, ...)` with params array.
- Join across tables for cross-referencing: `LEFT JOIN violations ON ...`.
- Aggregate for ranking: `COUNT(*)`, `MAX(date)`, `ORDER BY count DESC, latest DESC`.
- Compare dates with ISO 8601 strings against the review date from the prompt.
- Retry once on SQL errors after verifying the schema with `PRAGMA table_info`.

Full endpoint reference: [references/endpoints.md](references/endpoints.md).
Full determination codes: [references/determinations.md](references/determinations.md).
