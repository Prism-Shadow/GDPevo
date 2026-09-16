---
name: portfolio-analytics
description: Analyze engineering work-item portfolios using a shared REST API. Use this skill whenever the user asks to review portfolio mix, audit SLA aging, assess release readiness, or perform any analysis over the engineering work-item environment. Trigger on phrases like "portfolio mix", "SLA aging", "release readiness", "work item audit", "closed-work review", or when the user provides a TASK_ENV_BASE_URL and asks to produce a structured JSON report from work-item endpoints.
---

# Portfolio Analytics

Analyze engineering work items through a shared REST API to produce structured JSON reports. This skill covers portfolio mix review, SLA aging audits, and release readiness assessments. The environment and data model are the same across all three task families; what changes is the question being asked and the output template shape.

## Environment

Every task provides `<TASK_ENV_BASE_URL>` — the base URL for the shared engineering work-item API. All endpoints are relative to it. The available endpoints are:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items (supports query parameters for filtering) |
| GET | `/api/work-items/{item_id}` | Fetch a single work item by id |
| GET | `/api/mix-targets` | Target mix percentages by scope |
| GET | `/api/sla-policy` | SLA deadline policy configuration |
| GET | `/api/releases` | List releases |
| GET | `/api/releases/{release_id}` | Fetch a single release |
| GET | `/api/milestones` | List milestones |
| GET | `/api/dependencies` | List work-item dependency relationships |
| GET | `/api/blockers` | List blocker records |
| POST | `/api/query` | Run a restricted SQL query (body: `{"sql": "..."}`) |

No authentication is required. Call endpoints directly.

**Gathering data.** Start every task by fetching the relevant endpoints. For portfolio mix and SLA aging tasks, `/api/work-items` and `/api/mix-targets` or `/api/sla-policy` are usually enough. For release readiness, also fetch `/api/releases`, `/api/milestones`, `/api/dependencies`, and `/api/blockers`. Use the SQL query endpoint when you need cross-entity filtering that the GET endpoints don't support directly — it is the most efficient way to answer "which work items match these teams AND these categories AND are not cancelled."

## Data Model

Work items are the core entity. Every other endpoint provides context around them.

### Work item fields

Authoritative fields (trust these):

- `id` — unique identifier, always `WI-24024-...` format
- `team` — owning team name
- `product_area` — product area name
- `portfolio_category` — one of `NewFeature`, `TechDebt`, `Reliability`, `Security`; the canonical category for mix/SLA classification
- `status` — lifecycle status (`closed`, `open`, `in_progress`, `cancelled`, etc.)
- `type` — `primary` or `duplicate`; primary items are the ones you count
- `duplicate_of` — when type is `duplicate`, this field names the primary work item this record points at; null for primary records
- `owner` — assigned owner name, or null/missing when unassigned
- `severity` — `S1` through `S4`, used in SLA aging for escalation ordering
- `sla_deadline` — deadline date for SLA compliance
- `created_at` — creation timestamp
- `closed_at` — closure timestamp
- `title` — free-text title
- `labels` — array of label strings
- `release_id` — release this item belongs to (if any)
- `milestone_id` — milestone this item belongs to (if any)

Stale fields (ignore these):

- `mirror_status` — a denormalized copy of status that may be out of date; never use it for decisions
- `legacy_category` — an older classification field that may disagree with `portfolio_category`; always prefer `portfolio_category`

### Classification rule

When a work item's `portfolio_category` conflicts with signals from `type`, `labels`, or `title`, trust `portfolio_category` as the single source of truth. Do not reclassify based on label or title heuristics unless the task prompt explicitly asks you to resolve conflicts differently.

### Primary vs. duplicate

A work item where `type` is `"duplicate"` or where `duplicate_of` is non-null is a duplicate. Duplicates point at a canonical primary record. When the task asks for "included" or "primary" work items, exclude duplicates from the counted set. Always report duplicate clusters separately — a cluster is a primary_id paired with the list of duplicate ids that reference it.

When `duplicate_of` references an id not present in the fetched data, still report the cluster; the primary may reside outside the queried scope.

### Cancelled items

Work items with `status` `"cancelled"` are excluded from portfolio mix counts and release completion denominators. Report excluded cancelled ids separately when the output template calls for it.

## Output Conventions

Every task includes an `answer_template.json` that defines the exact output schema. Follow it precisely. These conventions apply across all template variants:

### Ordering

- **Work item id lists**: sort lexicographically (ASCII order) ascending.
- **Team lists**: sort alphabetically ascending.
- **Product area lists**: sort alphabetically ascending.
- **Category rows**: always use the fixed order `NewFeature`, `TechDebt`, `Reliability`, `Security` — unless the template explicitly specifies a different order.
- **Under-invested / deficit categories**: sort from most negative gap to least negative gap (i.e., ascending by gap_pct).
- **Duplicate clusters**: sort by `primary_id` lexicographically ascending. Within each cluster, sort `duplicate_ids` lexicographically ascending.
- **Milestone completion**: sort by `milestone_id` ascending.
- **Blocker cause counts**: use the exact cause strings from the API; do not normalize or paraphrase them.
- **Dependency chains**: sort lexicographically by the full joined path string.

### Precision

- **Percentages (completion_pct, actual_pct, target_pct, gap_pct)**: round to exactly 1 decimal place. Use standard rounding (0.5 rounds up).
- **Rates (breach_rate, readiness_score)**: round to exactly 3 decimal places. When the value is exactly 0, render as `0.0` (1dp) or `0.000` (3dp), not `0`.
- **All other numeric values**: integers, no decimals.

### Enum values

Use the exact enum strings from the template: `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`, `REBALANCE_CAPACITY`, `INVESTIGATE_DATA_QUALITY`, `MAINTAIN_CURRENT_MIX`, `LARGEST_NEGATIVE_GAP`, `NO_NEGATIVE_GAPS`, `DATA_CONFLICT`. Do not substitute synonyms.

### Null handling

When a field is nullable (e.g., `primary_category` or `secondary_category` in a follow-up action where no deficit exists), render it as JSON `null`, not the string `"null"` and not absent.

## Task Families

The three families differ in which endpoints to call and which calculations to perform. Read the task prompt to identify the family, then follow the patterns below. The task prompt always provides the exact scope parameters (teams, quarter, product areas, categories, as-of date, etc.).

### Portfolio Mix Review

Fetch work items matching the scope, then:

1. **Filter to closed primary items.** Exclude cancelled records and duplicates. Note both sets for the exclusion section.
2. **Classify by portfolio_category.** Count items per category — counts are item counts, not story points.
3. **Compute actual percentages.** For each category: `(count / total_included) * 100`, rounded to 1dp.
4. **Fetch target mix.** Call `/api/mix-targets` and find the row whose `scope_id` matches the task's scope. The target row provides `target_pct` for each category.
5. **Compute gap table.** For each category in fixed order: `gap_pct = actual_pct - target_pct`, rounded to 1dp.
6. **Identify under-invested categories.** Categories with negative gap_pct, from most negative to least negative.
7. **Determine follow-up action.** Use `LARGEST_NEGATIVE_GAP` rationale when gaps exist, with `primary_category` as the most negative and `secondary_category` as the second-most negative. Use `NO_NEGATIVE_GAPS` when all gaps are >= 0. Use `DATA_CONFLICT` when target and actual data seem inconsistent (e.g., target percentages don't sum near 100).

### SLA Aging Audit

Fetch work items matching the scope teams and SLA-relevant categories, then:

1. **Separate primary from duplicate.** Build the included primary id list and the duplicate cluster list. Only primary items count toward SLA metrics.
2. **Apply SLA policy.** Call `/api/sla-policy` to get the deadline rules. Compute which primary items are overdue relative to the as-of date. An item is overdue when its `sla_deadline` is before the as-of date. Treat items without an `sla_deadline` as overdue if the policy says they should have one.
3. **Build aging buckets.** Compute days from `created_at` to as-of date for each primary item. Count into buckets: 0-3, 4-7, 8-14, 15-30, 31+. If the task specifies SLA-deadline-based aging, use days from `sla_deadline` to as-of date instead.
4. **Count overdue by team.** Group overdue primary items by team, report counts. List teams alphabetically.
5. **Identify the top hotspot.** Find the (team, owner) pair with the most overdue primary items. When owner is missing, treat the owner as `"UNASSIGNED"` for hotspot purposes. Break ties by picking the first lexicographically by team then owner.
6. **Report missing owners.** List primary included ids with no owner, sorted ascending.
7. **Calculate breach rate.** `overdue_primary_count / included_primary_count`, rounded to 3dp.
8. **Build escalation queue (when required).** Sort overdue primary items by severity (S1 first) then by deadline ascending (earliest first). If the template does not include an escalation queue, skip this step.
9. **Severity breakdown (when required).** Count overdue items by severity level. Report all four levels (S1-S4), even when zero.

### Release Readiness

Fetch the release by id, its milestones, work items, blockers, and dependencies, then:

1. **Determine ship decision.** Base this on completion, blocker, and dependency signals:
   - `SHIP`: all milestones at 100%, no unresolved high-impact blockers, no critical dependency chains.
   - `SHIP_WITH_WATCH`: near-complete with minor open items that have clear resolution paths.
   - `NO_SHIP`: incomplete milestones, unresolved high-impact blockers, or blocked critical dependency chains.
   As a baseline: any milestone below 100% or any unresolved high-impact blocker typically means `NO_SHIP`.
2. **Compute milestone completion.** For each milestone in the release, count primary work items where status is `closed` (complete) vs. total primary work items. `completion_pct = (complete / total) * 100`, rounded to 1dp.
3. **Identify gating items.** Non-complete primary work items that gate release readiness. These are typically open/in-progress items in incomplete milestones that have unresolved blockers or open dependencies. Sort ascending with no duplicates.
4. **Count blockers by cause.** Filter blockers to those linked to release work items, marked high-impact, and unresolved. Count by exact `cause` text.
5. **Trace dependency chains.** For each blocked release work item, follow the dependency graph outward through non-complete dependencies. Report each chain as an ordered path from the blocked release item to the non-complete dependency at the end. Sort chains lexicographically by the full path.
6. **Calculate readiness score.** `completed_primary_count / total_primary_count`, rounded to 3dp, across all release work items.

## Data Quality Checklist

Before finalizing any output, verify:

- [ ] Did I use `portfolio_category`, not `legacy_category`, for classification?
- [ ] Did I use `status`, not `mirror_status`, for lifecycle checks?
- [ ] Did I exclude duplicate records from primary counts but still report clusters?
- [ ] Did I exclude cancelled items from denominators and report them when the template requires?
- [ ] Did I apply the correct rounding (1dp for percentages, 3dp for rates/scores)?
- [ ] Did I order lists as specified (lexicographic ids, alphabetical teams, fixed category order)?
- [ ] Did I use the exact enum strings from the template?
- [ ] Did I double-check that gap_pct is actual minus target, not the reverse?
- [ ] Did every field required by the answer template appear in my output?

## Workflow

1. **Read the prompt and the answer template.** Understand which task family this is and what shape the output must take.
2. **Fetch all needed data.** Call every endpoint that might be relevant — it is better to have extra data than to miss a record. Use the SQL endpoint for complex cross-filtering when GET parameters are insufficient.
3. **Clean and classify.** Apply the primary/duplicate split, cancelled exclusion, and category classification rules above.
4. **Compute metrics.** Follow the formulas for the task family.
5. **Assemble the JSON.** Match the template field by field. Apply ordering and precision conventions.
6. **Run the data quality checklist.** Confirm every item before returning.

## Reference

For detailed schemas and field definitions of the API entities, see [references/data-model.md](references/data-model.md).

When the task involves complex cross-filtering that the GET endpoints don't easily support, the SQL endpoint at `POST /api/query` accepts queries like:

```json
{"sql": "SELECT * FROM work_items WHERE team IN ('Team A', 'Team B') AND portfolio_category IN ('Reliability', 'Security') AND status != 'cancelled'"}
```

Use it to collapse multiple GET calls into one precise result set. The query language is a restricted SQL dialect; keep queries simple and avoid JOINs unless the task explicitly needs them.

When computing SLA aging, note that the aging bucket for an item is determined by how long it has been open relative to the as-of date. If the SLA policy defines a deadline window, overdue means the deadline has passed relative to the as-of date. Always confirm which date range the task prompt specifies for aging.
