## Data Model Reference

### Base URL
`<TASK_ENV_BASE_URL>` provided by the task runtime environment.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/work-items` | List all work items (239 records) |
| GET | `/api/work-items/{work_item_id}` | Fetch a single work item by ID |
| GET | `/api/mix-targets` | List all portfolio mix target rows |
| GET | `/api/sla-policy` | List SLA severity-to-days mapping |
| GET | `/api/releases` | List all releases |
| GET | `/api/releases/{release_id}` | Fetch a single release |
| GET | `/api/milestones` | List all milestones |
| GET | `/api/dependencies` | List all dependency edges |
| GET | `/api/blockers` | List all blocker records |
| POST | `/api/query` | Restricted SQL query endpoint |

### Work Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier, e.g. `WI-24024-P001` |
| `status` | string | **Authoritative** current state. Do not use `mirror_status`. |
| `mirror_status` | string | **Stale** — ignore this field. |
| `work_type` | string | Primary classification signal. Values: `Feature`, `Enhancement`, `Security`, `Compliance`, `Reliability`, `Incident`, `Bug`, `Refactor`, `Chore`, `Dependency` |
| `labels` | array[string] | Secondary classification signal. Common values: `security`, `cve`, `encryption`, `auth`, `reliability`, `latency`, `outage`, `incident`, `flaky`, `cleanup`, `refactor`, `migration`, `dependency`, `feature`, `rollout`, `follow-up`, `customer-request`, `stale-export`, `papertrail` |
| `title` | string | Tiebreaker classification signal |
| `legacy_category` | string | Legacy field — do not use as primary signal. Values: `new`, `feature`, `bug`, `tech-debt`, `quality`, `maintenance`, `security`, `admin` |
| `team` | string | Owning engineering team |
| `product_area` | string | Product area (may include combined areas separated by `+`) |
| `owner` | string or null | Assigned owner name. `null` means unassigned. |
| `severity` | string | `S1`, `S2`, `S3`, or `S4` |
| `priority` | integer | 1 (highest) to 5 (lowest) |
| `story_points` | integer | Effort estimate |
| `closed_at` | string or null | ISO date of closure. `null` means open. |
| `created_at` | string | ISO date of creation. |
| `due_at` | string or null | ISO due date. |
| `duplicate_of` | string or null | If status is Duplicate, the canonical work item id. |
| `release_id` | string or null | Associated release. |
| `milestone_id` | string or null | Associated milestone. |

### Status Value Semantics

| Status | Meaning | Completed? |
|--------|---------|------------|
| `Backlog` | Not yet started | No |
| `In Progress` | Actively worked on | No |
| `Review` | Under review | No |
| `Reopened` | Reopened after close | No |
| `Blocked` | Cannot proceed | No |
| `Cancelled` | Cancelled — always exclude from primary counts | N/A |
| `Duplicate` | Points to another item via `duplicate_of` — always exclude from primary | N/A |
| `Done` | Completed | Yes |
| `Deployed` | Deployed to production | Yes |
| `Verified` | Verified complete | Yes |
| `Closed` | Closed | Yes |
| `Resolved` | Resolved | Yes |

### Mix Target Fields

| Field | Type | Description |
|-------|------|-------------|
| `scope_id` | string | Unique scope key to match on |
| `quarter` | string | e.g. `2025-Q4` |
| `product_area` | string | Product area or combined areas |
| `team_group` | string | Team grouping description |
| `new_feature_pct` | number | Decimal, e.g. 0.34 = 34% |
| `tech_debt_pct` | number | Decimal |
| `reliability_pct` | number | Decimal |
| `security_pct` | number | Decimal |

### SLA Policy Fields

| Field | Type | Description |
|-------|------|-------------|
| `severity` | string | `S1`, `S2`, `S3`, `S4` |
| `days_to_due` | integer | SLA window in days for that severity |

Observed values: S1=3 days, S2=10 days, S3=21 days, S4=45 days.

### Release Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | e.g. `REL-ORION-2026-02` |
| `name` | string | Human-readable name |
| `target_date` | string | Target ship date |
| `train` | string | Release train name |

### Milestone Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | e.g. `MIL-ORION-GA` |
| `name` | string | Human-readable name |
| `release_id` | string | Parent release |
| `owner_team` | string | Team responsible |

### Blocker Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | e.g. `BLK-24024-001` |
| `release_id` | string | Release this blocks |
| `work_item_id` | string | Work item affected |
| `cause` | string | Exact cause description — use verbatim as key |
| `severity` | string | `Low`, `Medium`, `High`, `Critical` |
| `status` | string | `Open`, `Monitoring`, `Resolved` |
| `opened_at` | string | ISO date |
| `resolved_at` | string or null | ISO date if resolved |

### Dependency Fields

| Field | Type | Description |
|-------|------|-------------|
| `blocked_id` | string | Work item that is blocked |
| `depends_on_id` | string | Work item it depends on |
| `relation` | string | Nature: `depends-on`, `blocks-release-readiness`, `security-review-required`, `validation-required`, `implementation-dependency`, `audit-evidence-required` |

### Distractor Record Detection

Some work items use an alternate schema wrapped in a `work_item` sub-object with field names like `legacy_category` and `product_area` (instead of `product_area`). These are distractor records — exclude them from primary portfolio analysis and report them in the exclusion list when the answer template has a dedicated field for them.
