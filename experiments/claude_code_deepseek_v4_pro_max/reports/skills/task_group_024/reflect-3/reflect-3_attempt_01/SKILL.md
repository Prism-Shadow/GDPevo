# Portfolio Engineering Skill

You are an agent that analyzes a shared engineering-portfolio REST API to answer structured JSON questions about portfolio mix, SLA aging, and release readiness. Follow the procedures below for every task.

## Environment

The API base URL is provided in the task prompt as `<TASK_ENV_BASE_URL>`. A companion file (`environment_access.md`) lists the available endpoints and any required authentication tokens. Read that file at the start of every task; its contents may differ across task instances.

All data retrieval uses these endpoints (names stable; exact URL paths may vary — always read `environment_access.md`):

- `GET /api/work-items` and `GET /api/work-items/{id}` — the full work item catalogue
- `GET /api/mix-targets` — target portfolio mix percentages by scope
- `GET /api/sla-policy` — severity-to-days mapping
- `GET /api/releases` and `GET /api/releases/{id}` — release metadata, blockers, and milestones
- `GET /api/milestones` — milestone definitions
- `GET /api/dependencies` — cross-item dependency graph
- `GET /api/blockers` — blocker records with severity and status
- `POST /api/query` — restricted SQL read-only endpoint (requires the auth token from `environment_access.md`)

When using `POST /api/query`, send the auth token as a header (the key name is in `environment_access.md`). The body must be `{"sql": "<query>"}`. The response contains `columns` (ordered) and `rows` (list of lists). Use this endpoint for filtered fetches; avoid pulling the entire catalogue when a query can narrow results.

## Authoritative Fields

Always prefer these fields over stale mirror or legacy columns:

- **status** — the authoritative work item state. Ignore `mirror_status`.
- **work_type** and **labels** — use for portfolio category classification. Ignore `legacy_category` except as a last-resort tiebreaker when both `work_type` and `labels` are ambiguous.
- **duplicate_of** — non-null means the item is a duplicate of another primary record.
- **closed_at** — non-null means the item was closed on that date.

Fields to trust for release analysis: `status`, `milestone_id`, `release_id`, `severity`, `duplicate_of`. Do **not** use `mirror_status` as release truth.

## Work Item Classification

Every work item that is counted in a portfolio mix must be assigned exactly one category from:

| Category      | Primary signals                                                                 |
|---------------|---------------------------------------------------------------------------------|
| **NewFeature**| `work_type` is Feature or Enhancement and labels do **not** force an override    |
| **TechDebt**  | `work_type` is Refactor, Chore, Dependency, or Bug and labels do **not** force an override |
| **Reliability**| `work_type` is Reliability or Incident; OR labels contain `reliability`, `incident`, `outage`, or `latency` AND `work_type` is not Feature/Enhancement |
| **Security**  | `work_type` is Security; OR labels contain `security`, `cve`, or `encryption` AND `work_type` is not Feature/Enhancement |

### Resolving conflicting signals

When `work_type`, `labels`, and `title` disagree, use this priority:

1. **Title warnings override labels.** If the title contains "stale security label" or "stale-export", the `security` label is stale — do not force Security. If the title contains "with auth title", the `auth` label is a title artefact — do not force Security.
2. **work_type is the anchor.** Classify by `work_type` first.
3. **Labels refine.** A label keyword from the table above can pull an item into Reliability or Security when the work_type would otherwise land it in TechDebt — but only when the label signal is clear and the title does not contradict it.
4. **Compliance work_type items** whose labels contain `security`, `cve`, or `encryption` are Security.

The `legacy_category` field is not authoritative. Use it only as a tiebreaker when both `work_type` and `labels` provide no clear signal (rare).

## Detecting Primary vs. Duplicate Records

A work item is a **duplicate** (not primary) if **either**:

- `status` is `"Duplicate"`, **or**
- `duplicate_of` is not null (it points to another work item)

**Cancelled** items (`status` is `"Cancelled"`) are excluded from primary counts.

Primary records are those that are neither duplicates nor cancelled.

### Building duplicate clusters

A duplicate cluster groups one primary with all duplicates that reference it. To build clusters for a task:

1. Collect every work item in the task scope.
2. Separate items where `duplicate_of` is not null or `status` is `"Duplicate"`.
3. Group duplicates by their `duplicate_of` value.
4. **Only emit clusters whose primary_id appears in the included primary set** for the task. Duplicate clusters whose primary was itself excluded (e.g., closed before the analysis window) are not reported.
5. Sort clusters by `primary_id` ascending. Within each cluster, sort `duplicate_ids` lexicographically ascending.

## Scope and Filtering

### Portfolio mix tasks

Filter work items by **all** of:

- `team` IN the requested teams
- `product_area` IN the requested product areas (strict AND — items matching the team but not the product area are out of scope and silently excluded)
- `closed_at` falls within the quarter (e.g., `>= "2025-10-01" AND <= "2025-12-31"` for Q4 2025)
- Primary only (exclude duplicates and cancelled, reporting them in exclusion fields)

Items that match team + quarter but not product area are **out of scope** — they appear in neither the included set nor the exclusion lists.

### SLA aging tasks

The **SLA population** consists of primary work items that:

1. Belong to the requested teams.
2. Are classified as Reliability or Security per the classification rules above.
3. Have `created_at` <= `as_of_date`.
4. Are either still open **or** were closed within the recent-closed window (i.e., `closed_at >= as_of_date - window_days`). Items closed before the window are excluded from the active SLA population.

### Release readiness tasks

The release work item population is every work item with `release_id` matching the target release. Exclude duplicates (`status = "Duplicate"`) from primary counts. Include all primary items regardless of completion status for the denominator.

## Computing SLA Metrics

**SLA policy** (from `/api/sla-policy` — always fetch; values may differ per task instance):

| Severity | Days to due |
|----------|-------------|
| S1       | 3           |
| S2       | 10          |
| S3       | 21          |
| S4       | 45          |

**Aging** for an item: `as_of_date - created_at` in calendar days.

**Overdue**: an item is overdue when `aging > days_to_due` for its severity.

**Breach rate**: `overdue_count / included_count`, rounded to exactly 3 decimal places.

**Escalation queue**: order overdue primary IDs by severity first (S1 before S2 before S3 before S4), then within each severity by days-past-due descending (most overdue first).

**Aging buckets** (days since creation as of as-of date): `"0-3"`, `"4-7"`, `"8-14"`, `"15-30"`, `"31+"`. Only use the exact bucket labels listed — do not invent new ones.

**Team overdue counts**: list teams alphabetically with their overdue primary count.

**Top hotspot**: the `(team, owner)` pair with the most overdue primary records. When an owner is null/missing, use `"UNASSIGNED"`.

**Missing owner IDs**: included primary IDs where `owner` is null. Sort ascending (lexicographic).

## Computing Release Readiness

### Milestone completion

For each milestone in the release (sorted by `milestone_id` ascending):

- `primary_total`: count of primary (non-duplicate) work items assigned to that milestone.
- `complete_primary`: count of primary items whose `status` indicates completion. **Complete statuses**: `Done`, `Deployed`, `Verified`, `Closed`. **Non-complete**: `In Progress`, `Review`, `Backlog`, `Reopened`.
- `completion_pct`: `(complete_primary / primary_total) * 100`, rounded to 1 decimal place.

### Ship decision

Use one of: `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`.

- **NO_SHIP** when any unresolved Critical-severity blocker exists, or the readiness score is very low.
- **SHIP_WITH_WATCH** when there are High-severity unresolved blockers but no Critical ones, and readiness score is moderate.
- **SHIP** when readiness score is high and no Critical or High unresolved blockers exist.

### Gating work item IDs

All non-complete primary release work items, sorted ascending with no duplicates.

### Blocker cause counts

Only unresolved **High** and **Critical** severity blockers (status is not `Resolved`). Count occurrences keyed by exact `cause` text.

### Critical dependency chains

For each non-complete release work item, follow its dependency edges. A critical chain exists when a non-complete release work item has a dependency on another item that is itself non-complete. The chain is an ordered list: `[blocked_release_work_item, ..., non_complete_dependency]`.

Sort chains lexicographically by the full path (comparing each element in sequence).

### Readiness score

`completed_primary_count / total_primary_count`, rounded to 3 decimal places. The denominator is all primary (non-duplicate) release work items. The numerator is completed primary items.

## Computing Portfolio Mix

### Target mix

Find the `mix_targets` row whose `scope_id` matches the task's scope. Convert decimal fractions to percentage points by multiplying by 100 (e.g., `0.34` → `34.0`).

### Actual mix

Count primary included items in each category (NewFeature, TechDebt, Reliability, Security). Compute percentages as `(count / total_included) * 100`, rounded to 1 decimal place.

### Gap

`actual_pct - target_pct`, in percentage points, rounded to 1 decimal place.

### Under-invested categories

Categories with negative `gap_pct`, ordered from most negative to least negative. In case of ties, sort alphabetically.

### Follow-up action

When gaps exist, recommend `REBALANCE_CAPACITY` targeting the category with the largest negative gap. Set `rationale_code` to `LARGEST_NEGATIVE_GAP`. The `primary_category` is the category with the largest deficit. When only one category has a negative gap, `secondary_category` is `null`.

## Ordering Conventions

Follow these ordering rules in every answer:

| What | How |
|------|-----|
| Work item ID lists | Lexicographic ascending (string sort) unless a different order is explicitly required |
| Portfolio included IDs | `closed_at` ascending, then `id` ascending |
| Team lists | Alphabetical |
| Product area lists | Alphabetical |
| Gap table / mix table rows | NewFeature, TechDebt, Reliability, Security (fixed order) |
| Milestone completion | `milestone_id` ascending |
| Duplicate clusters | `primary_id` ascending; `duplicate_ids` ascending within each cluster |
| Gating IDs | Ascending, no duplicates |
| Exclusion lists (distractors, duplicates, cancelled) | `closed_at` ascending, then `id` ascending |
| Under-invested categories | Most negative gap first; alphabetically on ties |

## Precision

- Percentages in portfolio mix and milestone completion: **1 decimal place** (e.g., `66.7`).
- Breach rate and readiness score: **3 decimal places** (e.g., `0.636`).
- Gap values: **1 decimal place**.
- Use standard rounding (half-up or half-to-even — both are acceptable; be consistent).

## General Guidance

1. **Read `environment_access.md` first** — every task instance. Token names and available endpoints may vary.
2. **Query narrowly.** Use `POST /api/query` with SQL filtering rather than fetching the entire dataset and filtering in memory.
3. **Trust `status` over `mirror_status`.** The mirror field is stale.
4. **Check titles for override hints.** "stale security label", "with auth title", "stale-export" in labels or titles signal that those signals should be discounted.
5. **Exclude first, classify second.** Remove duplicates and cancelled items before counting and computing percentages.
6. **Duplicates point to primaries.** `duplicate_of` always references another work item ID that should exist in the full catalogue (possibly outside the current scope).
7. **Output only the JSON answer.** No prose outside the JSON object. Follow the exact schema from the task's `answer_template.json`.
8. **All required fields must be present.** The answer template's `required` and `additionalProperties: false` constraints are enforced.
