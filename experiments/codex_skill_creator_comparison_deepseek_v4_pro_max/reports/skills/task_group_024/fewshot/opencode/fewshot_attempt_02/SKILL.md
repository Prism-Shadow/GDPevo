---
name: portfolio-analyzer
description: Analyze engineering portfolio data from a shared task-environment REST API. Use this skill whenever the user asks about portfolio mix reviews, SLA aging audits, release readiness assessments, work item classification, engineering capacity planning, or any task that references a TASK_ENV_BASE_URL with work items, mix targets, releases, milestones, blockers, dependencies, or SLA policies. This skill covers portfolio category analysis, SLA breach detection, release gating, dependency chain tracing, and duplicate/distractor record handling. Even if the user does not mention "portfolio" explicitly, use this skill for any task that queries work items grouped by scope, team, quarter, or release in an engineering-operations context.
---

# Portfolio Analyzer

Analyze engineering portfolio data through a standardized task-environment REST
API. This skill covers three analysis types: portfolio mix reviews, SLA aging
audits, and release readiness assessments. Read the relevant reference files
when you need deeper detail on the data model, API endpoints, or output
conventions.

## Core Workflow

Every portfolio analysis follows the same four-phase pattern:

1. **Fetch** - collect all needed data from the environment API.
2. **Clean** - separate primary records from duplicates, cancelled items, and
   stale mirror/distractor records.
3. **Classify** - assign each primary item to exactly one portfolio category.
4. **Compute and Output** - calculate aggregates, gaps, rates, and produce a
   single JSON answer matching the provided answer template.

## Fetching Data

The environment lives at `<TASK_ENV_BASE_URL>`. Read
[references/api-endpoints.md](references/api-endpoints.md) for the full endpoint
catalog and SQL query table schema.

Start by fetching all relevant data in parallel where possible. The standard
pattern:

- **Portfolio mix**: fetch work items filtered by scope or team/quarter, plus
  mix targets.
- **SLA audit**: fetch work items, SLA policy, then determine the as-of date and
  window from the prompt.
- **Release readiness**: fetch the release by ID, then fetch its milestones,
  work items, blockers, and dependencies in parallel.

Use GET endpoints as your primary tool. Only reach for `POST /api/query` when
you need a cross-entity join that cannot be done efficiently with client-side
filtering on the REST results. When you do use SQL, write SQLite-compatible
SELECT statements.

## Cleaning: Primary vs. Non-Primary Records

A work item is **primary** (countable) only when ALL three conditions hold:

1. `status` is NOT `cancelled`.
2. `duplicate_of` is `null` (it is not a duplicate of another item).
3. `mirror_status` is `null` or empty (not a stale mirror/export record).

Items that fail any condition go into exclusion lists. Read
[references/data-model.md](references/data-model.md) for the full field
reference.

**Never** use `mirror_status` or `legacy_category` as source of truth. Always
use `status` and `category` from the work item object. Mirror fields exist
alongside authoritative fields in the API responses but contain stale data.

**Duplicate grouping**: when `item.duplicate_of` is non-null, group duplicates
by their `duplicate_of` value. The referenced item is the primary; the current
item is the duplicate. Sort duplicate clusters by primary_id ascending.

## Classifying Work into Categories

Every work item maps to exactly one of these four portfolio categories:

```
NewFeature -> TechDebt -> Reliability -> Security
```

The authoritative source is the `category` field. When the prompt says to use
portfolio category conventions for resolving conflicting signals, apply this
priority order:

1. The `category` field, when present and valid.
2. The `type` field: `Bug` -> Reliability (or Security if the title contains
   security keywords), `Story` -> NewFeature, `Task` -> TechDebt.
3. Keyword signals in the `title` field.

See [references/data-model.md](references/data-model.md) for the full keyword
mapping.

## Computing Results

After cleaning and classifying, compute the aggregates the task asks for. Three
common analysis types are covered below.

### Analysis Type: Portfolio Mix Review

1. Count primary closed work items per category.
2. Read the target mix percentages from `/api/mix-targets` for the matching
   `scope_id`.
3. Compute actual percentages: `(category_count / total_primary) * 100`, rounded
   to 1 decimal place.
4. Compute gaps: `gap_pct = actual_pct - target_pct` (rounded to 1 decimal).
5. Identify under-invested categories: those with negative gap_pct, ordered from
   most negative to least negative.
6. The follow-up/recommended action: `REBALANCE_CAPACITY` targeting the category
   with the largest negative gap, using `LARGEST_NEGATIVE_GAP` as rationale.

Sort included work item IDs by `closed_at` ascending, then by `id` ascending.
Excluded distractor/duplicate/cancelled IDs follow the same sort.

### Analysis Type: SLA Aging Audit

1. Determine the primary population: work items in scope for the given teams,
   matching the SLA-relevant categories (typically Reliability and Security).
2. Determine overdue items: primary items where the SLA target resolution
   duration (from `/api/sla-policy`, keyed by severity) has elapsed relative to
   `created_at` and the as-of date. Items closed within the recent window do not
   count as overdue.
3. Compute aging buckets by days since `created_at` (for open items) or days
   open before closure (for recently closed). Bucket boundaries: 0-3, 4-7, 8-14,
   15-30, 31+.
4. Find the owner+team hotspot: the owner/team pair with the most overdue
   primary records. Use `UNASSIGNED` when owner is null.
5. Build duplicate clusters from items where `duplicate_of` is non-null.
6. Compute breach rate: `overdue_primary_count / included_primary_count`, rounded
   to 3 decimal places.
7. For escalation queues: sort overdue primary items by severity descending,
   then `created_at` ascending, then ID ascending.

### Analysis Type: Release Readiness Assessment

1. Fetch the release by ID, then fetch its milestones, all associated work items,
   blockers, and dependencies.
2. Determine milestone completion: for each milestone, count completed primary
   work items vs. total primary work items. Completion percentage is rounded to
   1 decimal place. Sort milestones by milestone_id ascending.
3. Identify gating work items: non-complete primary release work items that block
   readiness. Sort ascending with no duplicates.
4. Count unresolved high-impact blockers by exact cause text. Only count blockers
   where `resolved` is false and `impact` is high.
5. Trace critical dependency chains: follow `dependencies` to find paths from
   blocked release work items through to non-complete dependencies. Each chain
   is an ordered array of work item IDs. Sort chains lexicographically by the
   full path.
6. Compute readiness score: `completed_primary / total_primary`, rounded to 3
   decimal places.
7. Ship decision logic:
   - `SHIP` when readiness_score >= 0.90 and no unresolved high-impact blockers.
   - `SHIP_WITH_WATCH` when readiness_score >= 0.75 but with minor concerns.
   - `NO_SHIP` when readiness_score < 0.75 or unresolved high-impact blockers
     exist on gating items.

## Output Conventions

Read [references/conventions.md](references/conventions.md) for the full
sorting and precision reference. The key rules:

- **IDs**: lexicographic ascending.
- **Teams**: alphabetical ascending.
- **Categories**: always `NewFeature, TechDebt, Reliability, Security` order.
- **Percentages**: 1 decimal place.
- **Rates**: 3 decimal places.
- **Gaps**: `actual_pct - target_pct`, in percentage points.

## Answer Template

Every task provides an `answer_template.json` in the input payloads. Read it
before computing results. It defines the exact JSON shape, required fields,
allowed enum values, and any additional constraints. Your output must match that
schema exactly - no extra fields, no missing required fields, no prose outside
the JSON object.

Pay close attention to field naming differences between templates. For example,
one portfolio mix template may use `gap_table` and `under_invested_categories`
while another uses `mix_table` and `largest_deficit_category`. Do not assume
uniform naming; always read the template.

## Common Pitfalls

- Treating `mirror_status` or `legacy_category` as truth instead of `status` and
  `category`.
- Counting duplicates or cancelled items in primary totals.
- Forgetting to round percentages to 1 decimal place or rates to 3 decimal places.
- Using the wrong category order in tables (must be NewFeature, TechDebt,
  Reliability, Security).
- Computing gap as `target - actual` instead of `actual - target`.
- Using stale mirror/export status fields to determine completion instead of
  authoritative `status`.
- Including recently-closed items in the overdue count for SLA audits when the
  task specifies a recent closed window.
- Not sorting IDs lexicographically (which treats digits character-by-character,
  not numerically).
