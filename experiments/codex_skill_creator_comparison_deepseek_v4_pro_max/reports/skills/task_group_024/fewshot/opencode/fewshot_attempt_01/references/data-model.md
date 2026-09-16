# Portfolio Data Model Reference

Detailed field reference, value domains, and pattern catalog derived from the environment.

## Work item fields

| Field | Type | Domain / Notes |
|-------|------|----------------|
| `id` | string | Pattern: `WI-24024-[A-Z]?[0-9]{3}`. The prefix `WI-24024-` followed by an optional letter segment (e.g. `P`, `S`) and 3 digits. |
| `title` | string | Free-text description. Often contains signal words for classification (e.g. "cve", "migration", "cleanup", "outage"). |
| `status` | string | **Authoritative.** Values: `In Progress`, `Review`, `Closed`, `Done`, `Verified`, `Deployed`, `Duplicate`, `Cancelled`, `Backlog`, `Reopened`, `Open`, `Monitoring`, `Resolved`. |
| `work_type` | string | `Feature`, `Bug`, `Security`, `Reliability`, `Incident`, `Refactor`, `Dependency`, `Enhancement`, `Chore`, `Compliance` |
| `labels` | array of strings | Common tags: `security`, `cve`, `reliability`, `outage`, `incident`, `latency`, `flaky`, `cleanup`, `refactor`, `migration`, `feature`, `rollout`, `auth`, `encryption`, `dependency`, `customer-request`, `follow-up`, `papertrail`, `stale-export`, `compliance`. |
| `legacy_category` | string | `security`, `quality`, `new`, `tech-debt`, `maintenance`, `bug`, `feature`, `admin`, `release`, `incident`. Not authoritative. |
| `product_area` | string | `Atlas Backend`, `Identity`, `Checkout`, `Data Reliability`, `Security Operations`, `Core Runtime`, `Edge Routing`, `Revenue Systems`, `Release Train`, `API Connectivity` |
| `team` | string | 15 distinct teams including `Platform Core`, `Identity Services`, `AppSec`, `Data Platform`, `Infra Reliability`, `Mobile Client`, `Growth Experiences`, `Core Services`, `Edge Delivery`, `Release Engineering`, `Revenue Platform`, `Billing`, `Integrations`, `Observability`, `API Foundations`. |
| `owner` | string or null | Person name (e.g. "Avery Quinn", "Mina Shah") or `null` when unassigned. |
| `severity` | string | `S1`, `S2`, `S3`, `S4` |
| `priority` | integer | 1-5 (1 is highest) |
| `created_at` | string (ISO date) | Creation date |
| `closed_at` | string (ISO date) or null | Null means not yet closed |
| `due_at` | string (ISO date) | SLA target date |
| `duplicate_of` | string or null | Points to the canonical work item ID. Null when this item is primary. |
| `mirror_status` | string | **DO NOT USE.** Stale export artifact. Values often contradict `status`. |
| `milestone_id` | string or null | References a milestone ID |
| `release_id` | string or null | References a release ID |
| `story_points` | integer | Fibonacci-like sizing (1, 2, 3, 5, 8, 13). Not used for category percentages. |

## Mix target fields

| Field | Type |
|-------|------|
| `scope_id` | string — unique key |
| `quarter` | string — e.g. `2025-Q4` |
| `product_area` | string |
| `team_group` | string — descriptive name |
| `new_feature_pct` | number — decimal 0.0 to 1.0 |
| `tech_debt_pct` | number — decimal 0.0 to 1.0 |
| `reliability_pct` | number — decimal 0.0 to 1.0 |
| `security_pct` | number — decimal 0.0 to 1.0 |

Target percentages always sum to 1.0. Multiply by 100 for percentage points.

## SLA policy

| Severity | `days_to_due` |
|----------|---------------|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

## Release fields

| Field | Type |
|-------|------|
| `id` | string — e.g. `REL-ORION-2026-02` |
| `name` | string |
| `target_date` | string (ISO date) |
| `train` | string — e.g. `Orion`, `Nova`, `Zephyr` |

## Milestone fields

| Field | Type |
|-------|------|
| `id` | string — e.g. `MIL-ORION-GA` |
| `name` | string |
| `owner_team` | string |
| `release_id` | string — parent release |

## Dependency fields

| Field | Type |
|-------|------|
| `blocked_id` | string — the work item that is blocked |
| `depends_on_id` | string — the work item it depends on |
| `relation` | string — `depends-on`, `blocks-release-readiness`, `security-review-required`, `validation-required`, `audit-evidence-required`, `implementation-dependency` |

## Blocker fields

| Field | Type |
|-------|------|
| `id` | string — e.g. `BLK-24024-001` |
| `work_item_id` | string — the work item this blocks |
| `release_id` | string or null |
| `cause` | string — free text reason |
| `severity` | string — `Low`, `Medium`, `High`, `Critical` |
| `status` | string — `Open`, `Resolved`, `Monitoring` |
| `opened_at` | string (ISO date) |
| `resolved_at` | string (ISO date) or null |

## Common patterns and edge cases

### Mirror status mismatch

The `mirror_status` field is a stale export column that frequently disagrees with `status`. Common patterns seen:

- Items with `status: "Duplicate"` may show `mirror_status: "Complete"` or `mirror_status: "Closed"`. Always treat them as duplicates based on `status`.
- Items with `status: "Deployed"` or `status: "Done"` may have `mirror_status` showing `"Open"`, `"Blocked"`, or `"In Progress"`. The `status` field is correct.
- Never use `mirror_status` for any decision: closed/not-closed, complete/incomplete, duplicate/primary. Read `status`, `closed_at`, and `duplicate_of` instead.

### Stale export label

Items carrying the `stale-export` label have out-of-sync metadata. Their `mirror_status` is particularly unreliable, and even other fields (like `legacy_category`) may reflect an earlier export state rather than current truth. When you see `stale-export`, double-check `status` and `closed_at` before classifying.

### Work type vs labels classification conflicts

The environment contains items deliberately constructed to test classification judgment:

- **Feature work_type with security legacy_category**: An item may have `work_type: "Feature"`, `legacy_category: "security"`, and `labels` including `security`, yet the title indicates the security label is stale. The actual work is a feature. Classify by the substance of the work (title + work_type), not the stale security metadata.
- **Dependency work_type with security legacy_category**: An item with `work_type: "Dependency"`, `legacy_category: "security"`, but `labels` of `migration`/`cleanup` and a title mentioning migration. Classify as TechDebt — the labels and title reveal technical cleanup work, not security work.
- **Enhancement work_type with reliability labels**: An item with `work_type: "Enhancement"`, `legacy_category: "new"`, but `labels` including `outage` and `reliability` and a title mentioning outage recovery. The labels and title dominate — classify as Reliability, not NewFeature.
- **Security work_type with quality legacy_category**: An item with `work_type: "Security"`, `legacy_category: "quality"`, and `labels` including `feature`. Work_type Security wins — classify as Security.

**Default rule**: work_type carries the most weight, followed by labels, then legacy_category, then title. But when the title explicitly calls out staleness of a label or reveals the actual substance, let that override lower-priority signals.

### Duplicate detection patterns

Two mechanisms signal a duplicate:

1. `status: "Duplicate"` — unambiguous. This item IS a duplicate regardless of what `mirror_status` or `duplicate_of` says.
2. Non-null `duplicate_of` — this item points to another item as its canonical. It is a duplicate even if its own `status` is something like `"Closed"` (the duplicate record was closed, but the work is tracked under the canonical item).

Both patterns should be caught. Track duplicates in two groups: those excluded because of duplicate status, and those point-at-another.

### Cancelled items

Items with `status: "Cancelled"` have a `closed_at` date (they were formally closed when cancelled) but represent work that was never delivered. Exclude them from primary counts, completion rates, and portfolio mix calculations. Track them as a separate exclusion group.

### Overdue calculation nuance

An item is overdue when `as_of_date > due_at` AND it is not closed by the as-of date. Key edge case: an item whose `due_at` is after the as-of date (e.g. due 2026-01-20, as-of 2026-01-15) but was actually closed before the as-of date (e.g. closed 2026-01-14) is NOT overdue. The `closed_at` field is definitive — if it exists and is <= as_of, the item is not overdue.

### Escalation queue ordering

When an answer template asks for an escalation queue, order overdue items by:
1. Severity (S1 first, then S2, S3, S4)
2. Within the same severity, by `due_at` ascending (earliest due date first)
3. Within the same severity and due date, by `id` ascending

### Dependency chains for release readiness

A critical dependency chain traces from a gating (non-complete) release work item through `depends_on` relationships until it hits a non-complete dependency or a leaf. Important edge case: if every dependency in the chain is already complete (status is Closed/Done/Verified/Deployed), there is no critical chain to report — the output for that chain should be empty. Only report chains where at least one dependency is not yet complete.

### Scope filtering for mix vs. release tasks

- **Portfolio mix**: filter work items strictly by the scope's teams and product areas, plus quarter and closed status.
- **SLA audit**: filter by teams and categories (Security/Reliability), not necessarily by closed status (open items matter for SLA).
- **Release readiness**: filter by `release_id` — include all work items assigned to the release regardless of their team. Milestones also filter by `release_id`.
