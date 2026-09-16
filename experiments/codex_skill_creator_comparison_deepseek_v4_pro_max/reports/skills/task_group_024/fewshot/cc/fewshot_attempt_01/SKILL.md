---
name: work-intelligence
description: Analyze engineering work items through a shared task-environment API. Use this skill whenever the user needs to produce work-intelligence reports including portfolio mix reviews, SLA aging audits, release readiness assessments, or blocker/dependency analysis from a work-tracking system. The skill provides endpoint discovery, data-quality rules, classification conventions, and output schemas. Trigger on requests involving portfolio mix, SLA aging, release readiness, work item classification, engineering metrics, or blocker analysis.
---

# Work Intelligence

Analyze engineering work items, releases, blockers, dependencies, SLAs, and portfolio mix from a shared task-environment API.

## When to use this skill

Use this skill whenever the user asks you to produce a work-intelligence report or analysis from a task environment, including:

- Portfolio mix reviews: classify closed work items into portfolio categories and compare against targets
- SLA aging audits: identify overdue work, calculate breach rates, and produce escalation queues
- Release readiness: assess milestone completion, blockers, and dependency chains for a release
- Blocker analysis: count and categorize unresolved blockers
- Any query involving work item classification, SLA policy, or engineering metrics from the environment API

The skill covers three report families that share the same data sources and data-quality conventions.

## Runtime setup

The task environment base URL is provided as `<TASK_ENV_BASE_URL>` in the user's prompt. The access notes in `environment_access.md` list the available endpoints. Always start by reading that file if it is present.

Available endpoints typically include:

| Endpoint | Purpose |
|---|---|
| `GET /api/work-items` | All work items (single response, no pagination) |
| `GET /api/work-items/{item_id}` | Single work item detail |
| `GET /api/mix-targets` | Portfolio mix targets per scope |
| `GET /api/sla-policy` | SLA days-to-due by severity |
| `GET /api/releases` | Release train metadata |
| `GET /api/releases/{release_id}` | Single release detail |
| `GET /api/milestones` | Milestone metadata |
| `GET /api/dependencies` | Dependency edges between work items |
| `GET /api/blockers` | Blocker records |
| `POST /api/query` | Restricted SQL query endpoint |

Fetch all relevant endpoints in parallel at the start of each task to build a complete in-memory picture. The `GET /api/work-items` endpoint returns every work item in one call; no pagination is needed.

## Data-quality rules

These rules apply across all report families. Violating them produces incorrect answers.

### Status authority

The `status` field is canonical. The `mirror_status` field is stale and must never be used as the source of truth for a work item's current state. The answer templates explicitly require acknowledging this with `"ignored_mirror_status_and_legacy_category": true` where applicable.

### Category classification authority

The `legacy_category` field is unreliable. The `work_type` field is the primary classification signal. `labels` provide secondary signals. `title` provides tie-breaking signals when `work_type` and `labels` conflict.

Do not classify a work item by `legacy_category` alone, and do not trust a `legacy_category` value that contradicts the other three signals.

### Duplicate handling

Work items with `status` equal to `"Duplicate"` (and `duplicate_of` pointing to another work item) must be excluded from primary counts. Instead, report them separately in duplicate clusters: group by `duplicate_of`, with the pointed-to work item as `primary_id` and the duplicate items listed under `duplicate_ids`. Sort clusters by `primary_id` and sort `duplicate_ids` lexicographically within each cluster.

### Cancelled handling

Work items with `status` equal to `"Cancelled"` must be excluded from primary counts. Report them separately under `excluded_cancelled_ids` or as distractor exclusions.

### Closed-state work items

For portfolio mix reviews, use only work items that have reached a terminal state. Recognized closed states include: `Closed`, `Done`, `Deployed`, `Verified`. A work item in `Review`, `In Progress`, or `Backlog` is not closed.

### Stale labels

A label that is literally the string `"stale-export"` indicates the label set was exported from a stale source and individual labels may not be reliable. A title containing the phrase "stale security label" or "stale label" is a signal that the labels field is unreliable for that item. When such signals appear, give more weight to `work_type` and `title` than to `labels`.

## Portfolio category classification

Map every included work item into exactly one of four portfolio categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Use the following decision process.

### Step 1: Start with work_type

The `work_type` field is the strongest starting signal. The deterministic base mapping is:

| work_type | Default category |
|---|---|
| `Reliability` | Reliability |
| `Incident` | Reliability |
| `Bug` | Reliability |
| `Dependency` | Reliability |
| `Security` | Security |
| `Enhancement` | Security |
| `Compliance` | Security |
| `Refactor` | TechDebt |
| `Chore` | TechDebt |
| `Feature` | NewFeature |

### Step 2: Check for overrides from labels and title

The default mapping can be overridden when labels or title contain strong conflicting signals. Apply these override rules in order:

1. **Feature -> Security override**: If `work_type` is `Feature` and any label is `"security"`, classify as `Security`. A title containing "stale security label" confirms the security association rather than negating it.

2. **Feature -> Reliability override**: If `work_type` is `Feature` and labels or title contain `"migration"` (without a security signal), classify as `Reliability`.

3. **Feature -> TechDebt override**: If `work_type` is `Feature` and labels or title contain strong tech-debt indicators such as `"cleanup"` or `"refactor"` without reliability or security signals, classify as `TechDebt`.

### Step 3: Resolve ambiguity with title

When labels and work_type conflict and neither override rule clearly applies, read the title for the dominant theme. A title mentioning "outage", "incident", or "latency" pushes toward Reliability. A title mentioning "cve", "encryption", or "auth" pushes toward Security.

### Edge cases

- A work item whose `work_type` is `Feature` and has both `"security"` and `"migration"` signals: the security signal takes precedence (Security).
- A work item whose `work_type` is `Enhancement` with labels like `["outage", "reliability"]` stays Security (Enhancement maps to Security; labels do not override).
- A work item with `"stale-export"` in labels: discount the entire label set; rely on work_type and title.

## SLA aging methodology

For SLA aging audits, build the report in this sequence.

### Step 1: Define the primary population

Filter work items to:
- `team` matches one of the given scope teams
- Work item falls within the scope categories (typically `Reliability` and `Security`)
- `status` is not `"Duplicate"` and not `"Cancelled"`

These are the `included_primary_ids`. Sort lexicographically.

### Step 2: Calculate aging

For each primary work item, compute `aging_days = as_of_date - created_at` (in days). Bucket into: 0-3, 4-7, 8-14, 15-30, 31+.

### Step 3: Determine overdue

A work item is **overdue** when:
- `due_at < as_of_date` AND the item is not in a completed terminal state, OR
- `due_at < as_of_date` AND the item was closed but `closed_at > due_at` (closed late)

Completed terminal states are: `Closed`, `Done`, `Deployed`, `Verified`.

Items that are overdue but in a terminal state because they were closed late still count as overdue for breach-rate purposes when the task definition says so. Read the specific answer template and task prompt to determine whether late-closed items count as overdue.

### Step 4: Read SLA policy

The SLA policy endpoint returns `days_to_due` per severity:
- S1: 3 days
- S2: 10 days
- S3: 21 days
- S4: 45 days

The policy is used to set due-date expectations but the overdue calculation above already uses `due_at`.

### Step 5: Compute breach rate

`breach_rate = overdue_count / included_primary_count`, rounded to exactly 3 decimal places.

### Step 6: Build duplicate clusters

Group all work items where `status == "Duplicate"` and `duplicate_of` is non-null by `duplicate_of`. Each cluster has a `primary_id` (the `duplicate_of` target) and `duplicate_ids` (sorted lexicographically). Sort clusters by `primary_id`.

### Step 7: Hotspot and escalation

For team overdue counts: count overdue primary items per team, list teams alphabetically.

For the top hotspot: find the (team, owner) pair with the most overdue primary items. When owner is null/missing, use `"UNASSIGNED"`.

For escalation queue (when requested): sort overdue primary items by severity (S1 first, then S2, S3, S4), then by `due_at` ascending within each severity tier.

### Step 8: Missing owners

List primary included work items whose `owner` is `null`, sorted lexicographically by ID.

## Release readiness methodology

For release readiness assessments, build the report in this sequence.

### Step 1: Gather release data

Fetch the specific release by ID, all milestones, all work items, all blockers, and all dependencies. Filter to items relevant to the release.

### Step 2: Milestone completion

For each milestone in the release (sorted by `milestone_id` ascending):
- Count completed primary work items (status in `{Closed, Done, Deployed, Verified}`, excluding Duplicate and Cancelled)
- Count total primary work items for the milestone
- `completion_pct = (complete_primary / primary_total) * 100`, rounded to 1 decimal place

### Step 3: Ship decision

Determine the ship decision:
- `SHIP`: All milestones at 100% completion, no unresolved high-severity blockers.
- `SHIP_WITH_WATCH`: All milestones meet a reasonable threshold, some minor blockers present.
- `NO_SHIP`: Critical milestones incomplete, or unresolved high-impact blockers present.

Base the decision on the actual data rather than a fixed formula. The presence of any unresolved blocker with severity `High` or a gating work item that is not complete strongly suggests `NO_SHIP`.

### Step 4: Gating work items

Identify release work items that are not in a completed terminal state. These are the items that gate release readiness. Include only unique, non-duplicate, non-cancelled items. Sort ascending.

### Step 5: Blocker analysis

Count unresolved blockers by exact `cause` text. Filter to blockers that are unresolved (status is not `Resolved`) and have high impact (severity is `High` or `Critical`, or for the specific release context, blockers tied to release work items). Use the exact cause string as the map key.

### Step 6: Dependency chains

Trace dependency chains where a release work item depends on a non-complete item. Build the ordered path `[blocked_work_item, ..., non_complete_dependency]`. Sort chains lexicographically by the full path representation. Only include chains where the final dependency is non-complete and the chain relates to release readiness.

### Step 7: Readiness score

`readiness_score = completed_primary_work / total_primary_work`, rounded to 3 decimal places. Count only primary (non-duplicate, non-cancelled) work items on the release.

## Output format

Every task requires a single JSON answer conforming to an answer template. The template is provided as a JSON file in the task's `input/payloads/` directory. Read that template first and match its structure exactly.

Common ordering and precision rules across all reports:

- Sort work-item ID lists lexicographically (standard string sort).
- Sort team lists alphabetically.
- Round percentages to 1 decimal place unless specified otherwise.
- Round rates (breach_rate, readiness_score) to 3 decimal places.
- Use exact strings for enum values, cause keys, and category names.
- Do not include prose, commentary, or markdown outside the JSON object in the final answer.

## Reference files

- [classification.md](classification.md) -- Detailed work_type to portfolio category mapping with examples
- [sla-methodology.md](sla-methodology.md) -- SLA aging calculation procedures and edge cases
- [release-readiness.md](release-readiness.md) -- Release assessment decision framework and dependency tracing

Read the relevant reference file when the task involves that specific report family. The SKILL.md body covers the essentials; the references provide deeper grounding and edge-case guidance.

## Environment API patterns

### Query endpoint

The `POST /api/query` endpoint accepts a JSON body with a `query` field containing a SQL SELECT statement. Tables available include `work_items`. Use this for complex filters that cannot be expressed through the GET endpoints. The query token is provided in `environment_access.md` if required.

### Cross-referencing entities

- Work items reference releases via `release_id` and milestones via `milestone_id`.
- Blockers reference work items via `work_item_id` and releases via `release_id`.
- Dependencies link work items via `blocked_id` (the item being blocked) and `depends_on_id` (the item it depends on), with a `relation` field describing the dependency type.
- Mix targets are keyed by `scope_id`, which matches the task's scope identifier.

### Expected data volumes

The environment contains a few hundred work items, tens of releases/milestones, and tens of blockers/dependencies. All data fits in memory. Fetch all relevant endpoints once and work from the local snapshot.
