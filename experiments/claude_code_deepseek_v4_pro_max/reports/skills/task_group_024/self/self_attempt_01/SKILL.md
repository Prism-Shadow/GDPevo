# Portfolio Engineering Analysis Skill

## Purpose
Analyze portfolio engineering data — work items, mix targets, SLA policies, releases, milestones, blockers, and dependencies — to produce structured assessments: portfolio mix reviews, SLA aging audits, and release readiness reports.

## Trigger
Invoke this skill for portfolio mix analysis, SLA aging audits, release readiness assessments, or any task requiring classification and analysis of work items against portfolio targets and policies.

---

## Environment Access

The portfolio engineering environment exposes a REST API at a base URL provided via `environment_access.md` or `<TASK_ENV_BASE_URL>`. All endpoints live under this single base.

### Authentication
- Most endpoints are unauthenticated GETs.
- The SQL query endpoint (`POST /api/query`) requires an auth header:
  - Header name: specified in `environment_access.md` (typically `X-Env-Token`)
  - Header value: specified in `environment_access.md`

### Available Endpoints

| Method | Path                        | Purpose                                  |
|--------|-----------------------------|------------------------------------------|
| GET    | `/api/work-items`           | List all work items                      |
| GET    | `/api/work-items/{item_id}` | Get single work item detail              |
| GET    | `/api/mix-targets`          | List portfolio mix targets               |
| GET    | `/api/sla-policy`           | Get SLA policy configuration             |
| GET    | `/api/releases`             | List releases                            |
| GET    | `/api/releases/{release_id}`| Get release detail including milestones  |
| GET    | `/api/milestones`           | List milestones with work item linkage   |
| GET    | `/api/dependencies`         | List work item dependency relationships  |
| GET    | `/api/blockers`             | List blocker records for work items      |
| POST   | `/api/query`               | Run restricted SQL queries (auth required) |

### Fetch Strategy
- Start by fetching the broadest relevant collection (e.g., all work items, all mix targets, all releases) to understand what data is available.
- Use `POST /api/query` sparingly and only when the standard REST endpoints cannot answer a question — prefer REST endpoints first.
- When fetching a release, use `/api/releases/{release_id}` to get milestone membership rather than inferring from standalone milestone data.
- Fetch related records (blockers, dependencies) after identifying the work item population of interest.

---

## Work Item Model

### Field Authority
Work items carry multiple fields that can conflict. Use this precedence to resolve conflicts:

1. **Authoritative fields** (trust these):
   - `status` — the canonical work item status
   - `type` — the canonical work item type (Bug, Feature, Task, Epic, etc.)
   - `portfolio_category` — the canonical portfolio classification when present
   - `closed_at` — timestamp when the item was closed
   - `team` — the owning team
   - `assignee` / `owner` — the assigned person (may be null/missing)
   - `release_id` — the release this item belongs to
   - `milestone_id` — the milestone this item belongs to
   - `duplicate_of` — points to the canonical/primary item if this is a duplicate

2. **Stale/mirror fields** (ignore these — they may reflect export snapshots or legacy values):
   - `mirror_status` — a possibly stale copy of status; never use for decisions
   - `legacy_category` — a deprecated classification field; use `portfolio_category` instead
   - Any field prefixed with `mirror_` or `export_`
   - Any field suffixed with `_legacy`

### Status Classification
Work items fall into these lifecycle buckets:

- **Closed/Complete**: `status` indicates the work is done. These are the primary population for portfolio mix analysis and SLA aging.
  - Common closed statuses: `Closed`, `Done`, `Completed`, `Resolved`
- **Cancelled**: `status` indicates cancellation. These are **excluded from all analyses** but reported in exclusion flags.
- **In Progress / Open**: Work not yet finished. Relevant for release readiness (gating items) and SLA aging (open/overdue items).
- **Duplicate**: Identified by a non-null `duplicate_of` field pointing to another work item ID. **Excluded from primary counts** but reported in duplicate clusters.

### Distractor Records
Some records may appear to be in scope (matching team, quarter, or product area) but are not primary closed portfolio work. Common distractor patterns:
- Records with a status that is neither closed nor cancelled (e.g., `Draft`, `Proposed`, `Backlog`) — they were never worked
- Records whose `closed_at` falls outside the target quarter
- Records with a `type` that is not a deliverable work item (e.g., `Epic` containers that decompose into child items already counted)

### Portfolio Category Resolution
When an item's `portfolio_category` is authoritative and set, use it directly. When absent or suspect, resolve by:

1. **Priority order of signals**: `portfolio_category` > `type` > `labels` > `title` keywords
2. **Category mapping from type**:
   - `Feature` / `Story` / `Enhancement` → `NewFeature`
   - `Bug` / `Defect` → assess by title/labels: reliability-related keywords → `Reliability`; security-related → `Security`; otherwise → `TechDebt`
   - `Task` / `Chore` → `TechDebt`
   - `Epic` → use child item categories or exclude (container, not deliverable)
3. **Category mapping from labels/title keywords**:
   - Security: `security`, `vuln`, `CVE`, `auth`, `permissions`, `OWASP`, `pentest`
   - Reliability: `reliability`, `SLO`, `SLA`, `uptime`, `outage`, `incident`, `latency`, `resilience`
   - TechDebt: `refactor`, `tech-debt`, `cleanup`, `migration`, `upgrade`, `deprecation`
   - NewFeature: `feature`, `enhancement`, `new`, `capability`

The four portfolio categories are always: **NewFeature**, **TechDebt**, **Reliability**, **Security**.

---

## Portfolio Mix Analysis

Used when the task is to compare actual closed-work distribution against target mix percentages.

### Procedure
1. Fetch all work items and mix targets.
2. Identify the mix target row matching the task's `scope_id`.
3. Filter work items to in-scope closed work (matching teams, product areas, quarter — verified by `closed_at` date, not mirror fields).
4. Exclude: cancelled items, duplicates (items with `duplicate_of` set), and distractor records.
5. Classify each included item into exactly one portfolio category.
6. Count items per category (item counts, not story points).
7. Compute actual percentages: `(category_count / total_included) * 100`, rounded to 1 decimal place.
8. Compute gaps: `gap_pct = actual_pct - target_pct`, rounded to 1 decimal place.
9. Identify under-invested categories: those with negative `gap_pct`, ordered from most negative to least negative.
10. Determine the follow-up action:
    - If any category has a negative gap: `REBALANCE_CAPACITY` with `primary_category` = largest deficit, `rationale_code` = `LARGEST_NEGATIVE_GAP`
    - If data quality issues affect counts: `INVESTIGATE_DATA_QUALITY` with `rationale_code` = `DATA_CONFLICT`
    - If no negative gaps: `MAINTAIN_CURRENT_MIX` with `rationale_code` = `NO_NEGATIVE_GAPS`

### Output Conventions
- `gap_table` / `mix_table` rows in fixed order: NewFeature, TechDebt, Reliability, Security.
- Included work item IDs ordered by `closed_at` ascending, then `id` ascending.
- Distractor/excluded IDs ordered by `closed_at` ascending, then `id` ascending.
- `exclusion_flags.ignored_mirror_status_and_legacy_category` is always `true`.

---

## SLA Aging Audit

Used when the task is to assess how work items age against SLA targets.

### Procedure
1. Fetch work items and SLA policy configuration.
2. From SLA policy, extract the target resolution time (in days) for the relevant work categories.
3. Identify the primary SLA population: in-scope work items (matching teams and categories) that are not duplicates and not cancelled.
4. For each primary item, compute age: days from creation (or SLA start date) to the as-of date, or to `closed_at` for closed items.
5. Classify into aging buckets. Standard buckets: `0-3`, `4-7`, `8-14`, `15-30`, `31+` days.
6. Identify overdue items: items whose age exceeds the SLA target and are not yet closed (or closed after the target).
7. Compute breach rate: `overdue_primary_count / included_primary_count`, rounded to 3 decimal places.

### Overdue Hotspot Detection
- Count overdue items per team.
- Count overdue items per owner (treat missing/null owner as `UNASSIGNED`).
- The top hotspot is the `(team, owner)` pair with the highest overdue count.

### Duplicate Clusters
- Groups of work items where `duplicate_of` points to a primary item.
- Each cluster: `{primary_id, duplicate_ids[]}`.
- Sort clusters by `primary_id` ascending; within each cluster, sort `duplicate_ids` lexicographically.
- Duplicate clusters are reported but their items are **not** counted in primary metrics.

### Escalation Queue (for severity-based SLA)
When severity levels (S1-S4) are present:
- Count overdue items by severity.
- Build escalation queue: order overdue primary items by severity (S1 first, then S2, etc.), with ties broken by age descending.

### Output Conventions
- All ID lists sorted lexicographically ascending.
- Team names listed alphabetically.
- `missing_owner_ids`: subset of included primary IDs where owner/assignee is null, missing, or empty string.
- `breach_rate` / `sla_breach_rate`: rounded to 3 decimal places.

---

## Release Readiness Assessment

Used when assessing whether a release is ready to ship.

### Procedure
1. Fetch the release by ID (`/api/releases/{release_id}`) to get its structure and linked milestones.
2. Fetch all milestones and filter to those belonging to this release.
3. For each milestone, identify primary work items (exclude duplicates and cancelled items).
4. Count completed vs total primary work items per milestone.
5. Compute milestone `completion_pct`: `(complete_primary / primary_total) * 100`, rounded to 1 decimal place.
6. Identify gating work items: primary items linked to this release that are not complete (status ≠ closed/done). Sort ascending, no duplicates.
7. Fetch blockers for the release's work items. Filter to high-impact unresolved blockers. Count by exact cause text.
8. Fetch dependencies. Trace chains from blocked release work items to their non-complete dependencies. A critical chain is an ordered path `[blocked_work_item, ..., non_complete_dependency]`.
9. Compute readiness score: `completed_primary / total_primary`, rounded to 3 decimal places.
10. Determine ship decision:
    - `SHIP`: all milestones at 100%, no gating items, no unresolved high-impact blockers.
    - `SHIP_WITH_WATCH`: readiness score high but minor gating items or blockers exist that don't block core functionality.
    - `NO_SHIP`: significant incomplete work, high-impact blockers, or critical dependency chains unresolved.

### Ship Decision Logic
Use the readiness score as the primary signal, then adjust:
- `readiness_score >= 1.0` and zero gating items → `SHIP`
- `readiness_score >= 0.85` but some gating items or blockers → `SHIP_WITH_WATCH`
- `readiness_score < 0.85` or critical blockers/dependencies → `NO_SHIP`

### Output Conventions
- `milestone_completion` sorted by `milestone_id` ascending.
- `gating_work_item_ids` sorted ascending, no duplicates.
- `blocker_cause_counts` keys are exact cause strings from blocker records.
- `critical_dependency_chains` sorted lexicographically by the full path (join with `→` or compare as joined string).
- `completion_pct` rounded to 1 decimal place.
- `readiness_score` rounded to 3 decimal places.

---

## General Operating Rules

### Data Quality
1. **Never trust mirror/export fields.** Always use authoritative fields (`status`, `type`, `portfolio_category`, `closed_at`, `team`).
2. **Detect and exclude duplicates.** Any work item with a non-null `duplicate_of` field is a duplicate. Report in duplicate clusters but exclude from primary counts.
3. **Detect and exclude cancelled items.** Items with cancelled status are excluded from all analyses but reported in exclusion flags.
4. **Validate temporal scope.** Verify `closed_at` falls within the stated quarter or window; do not rely on quarter label fields alone.
5. **Handle missing owners.** Track items with null/missing/empty owner separately; treat as `UNASSIGNED` in hotspot analysis.

### Ordering
- **Work item IDs**: lexicographically ascending (string sort).
- **Team names**: alphabetically ascending.
- **Portfolio categories** in tables: NewFeature, TechDebt, Reliability, Security (fixed order).
- **Milestones**: by `milestone_id` ascending.
- **Aging buckets**: `0-3`, `4-7`, `8-14`, `15-30`, `31+` (fixed order).
- **Duplicate clusters**: by `primary_id` ascending; `duplicate_ids` within cluster sorted lexicographically.
- **Dependency chains**: by the full joined path, lexicographically.

### Precision
- **Percentages** (actual_pct, target_pct, gap_pct, completion_pct): rounded to **1 decimal place**.
- **Rates** (breach_rate, readiness_score): rounded to **3 decimal places**.
- **Counts**: exact integers, no rounding.

### Response Format
- Return a **single JSON object** matching the provided answer template schema.
- No prose, markdown fences, or commentary outside the JSON.
- All required fields must be present; no additional properties beyond the schema.
- Use `null` (not the string "null") for nullable fields when no value applies.

### Conflict Resolution
When multiple signals disagree about a work item's category:
1. Trust `portfolio_category` if authoritatively set.
2. Otherwise, use `type` to determine the broad bucket (Bug → assess further, Feature → NewFeature, Task → TechDebt).
3. Use `labels` and `title` keywords to refine (especially for Bug → Reliability vs Bug → Security disambiguation).
4. Document the resolution logic but do not include resolution notes in the output JSON.

### API Query Patterns
- `POST /api/query` accepts SQL. Use it only when REST endpoints are insufficient.
- Typical use: counting, grouping, or filtering across joined entities not available via single REST calls.
- Always include the auth header specified in `environment_access.md`.
- Prefer filtering on the client side from REST results over SQL queries unless the volume makes that impractical.

### Idempotency
- Repeated runs with the same inputs should produce identical outputs.
- Rely on deterministic sorting and rounding.
- No random or timestamp-dependent values in the output.
