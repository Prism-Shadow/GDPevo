---
name: eng-portfolio-review
description: >
  Query and analyze engineering work-item portfolios from a shared REST API.
  Use this skill whenever the task involves portfolio mix comparison against
  targets, SLA aging audits with overdue/breach-rate calculations, or
  release-readiness assessments with milestone tracking, blocker analysis,
  and dependency-chain resolution. Also use it when the user mentions
  work-item classification, SLA compliance, release gating, or any
  analysis that references the work-item REST API endpoints and asks for
  structured JSON output from them.
---

# Engineering Portfolio Review

## Quick start

Before any analysis, read the environment access file (likely named
`environment_access.md` or similar) to obtain the base URL and any
authentication token needed for the `/api/query` endpoint. The solver's
task prompt will point you at a `<TASK_ENV_BASE_URL>` placeholder; replace
it with the actual base URL from the access file.

Identify which analysis type the task requires, then follow the
corresponding workflow below. Read [references/api-reference.md](references/api-reference.md) for
the full endpoint catalog, data model, and field semantics when you need
precise field names or endpoint capabilities.

Every task provides an answer template in its `input/payloads/` directory.
Fill that template with computed values; do not invent a new output shape.

## Data integrity: the stale-mirror rule

The API may return *mirror* or *legacy* fields that look authoritative but
are not. The train evidence shows records where a mirror status disagrees
with the canonical status, or a legacy category disagrees with the
authoritative portfolio classification.

Always prefer these authoritative sources over mirror/export fields:

| Signal | Trust | Suspect |
|---|---|---|
| Status | The canonical status field | `mirror_status`, `export_status` |
| Portfolio category | The explicit `portfolio_category` field, or classification resolved from type + label + title (see below) | `legacy_category`, `mirror_category` |
| Release membership | The work item's own `release_id` field | Mirror-derived release associations |
| Blockers / dependencies | The blocker and dependency endpoints | Mirror blocker fields on the work item |

## Work item classification

Every work item maps to exactly one of four portfolio categories:

- **NewFeature** – new product capability or user-facing functionality
- **TechDebt** – code quality, refactoring, or architectural improvement
- **Reliability** – stability, resilience, monitoring, incident prevention
- **Security** – vulnerabilities, access control, audit, compliance

When a work item carries an explicit `portfolio_category` field, use it.
When the field is missing or ambiguous, resolve the category from the
strongest available signal in this order:

1. Prefer the authoritative category field when present and not a legacy field.
2. When category is missing, inspect the `type` field (e.g. a type of "bug"
   may indicate Reliability; a type of "vulnerability" points to Security).
3. When type is also ambiguous, inspect `labels` or `tags` for category-bearing
   tokens (e.g. "tech-debt", "security-review").
4. As a last resort, inspect the `title` for category-indicative terms.

When multiple signals conflict, the category field (if authoritative) wins,
then type, then labels, then title.

## Primary records and duplicates

Work items can exist in multiple records: one *primary* record and zero or
more *duplicate* records that point at it. A duplicate record has a field
(often `duplicate_of`) that contains the id of the primary record.

- **Primary records** are the canonical representation. Count them once in
  all populations — do not double-count duplicates.
- **Duplicate records** must be identified, excluded from primary counts,
  and reported separately when the answer template has a slot for them.
- A record that `duplicate_of` points to itself, or that has no
  `duplicate_of` value, is a primary.
- When `duplicate_of` references an out-of-scope work item (one not in the
  current team/quarter/product-area scope), treat the local record as a
  primary for counting purposes but still flag the cross-reference.

## Cancelled records

Work items with an authoritative `status` of "cancelled" are excluded from
all inclusive populations (counts, percentages, readiness denominators).
Report them separately when the answer template has an exclusion slot.

## Workflow: Portfolio mix analysis

Use this workflow when the task asks for a closed-work portfolio mix, a
mix comparison against targets, or a rebalance recommendation.

### Step 1: Fetch the target mix

Call `GET /api/mix-targets` and select the row whose `scope_id` matches
the task's scope. The target row provides target percentages (as percentage
points) for the four categories. Confirm the quarter and team/product-area
filters match.

### Step 2: Fetch closed work items

Use `GET /api/work-items` or the query endpoint to fetch work items
matching the scope (quarter, teams, product areas). Filter to closed
items — authoritative status must indicate completion, not merely a mirror
field.

### Step 3: Separate primary, duplicate, and cancelled

- Remove cancelled items to an exclusion list.
- Identify duplicate items (those whose `duplicate_of` points at another
  in-scope item) and exclude them from the primary closed set; add their ids
  to the exclusion list.
- The remaining records are the **included** primary closed work items.

### Step 4: Classify each included item

Assign each included item to one of the four portfolio categories using
the classification precedence above.

### Step 5: Compute the mix

Count items per category. Compute actual percentages:

```
actual_pct = (category_count / total_included) × 100
```

Round actual percentages to **1 decimal place**.

### Step 6: Compute the gap table

For each category (ordered NewFeature, TechDebt, Reliability, Security):

```
gap_pct = actual_pct - target_pct
```

Round target, actual, and gap to 1 decimal place.

### Step 7: Identify under-invested categories

Categories with a negative gap are under-invested. Sort them from most
negative gap to least negative gap.

### Step 8: Recommend a follow-up action

- If any gap is negative: recommend `REBALANCE_CAPACITY`, with the most
  negative category as primary and second-most as secondary. Use
  rationale `LARGEST_NEGATIVE_GAP`.
- If no negative gaps: recommend `MAINTAIN_CURRENT_MIX`, with both
  categories null. Use rationale `NO_NEGATIVE_GAPS`.

### Step 9: Sort and order

- Work item id lists: sort by `closed_at` ascending, then id ascending.
- Team name lists: sort alphabetically.

---

## Workflow: SLA aging audit

Use this workflow when the task asks for SLA compliance, overdue work
items, aging distributions, breach rates, or escalation queues.

### Step 1: Fetch the SLA policy

Call `GET /api/sla-policy` to obtain SLA target durations per category.

### Step 2: Fetch work items in scope

Fetch work items for the specified teams and categories. Use the
authoritative category field for filtering; do not rely on labels or
titles alone.

### Step 3: Separate primary, duplicate, and cancelled

Remove cancelled items. Identify duplicates (`duplicate_of` points at
another record) and exclude them from primary counts but report them
as duplicate clusters when the template asks for them.

The remaining records are the **included primary** population.

### Step 4: Compute overdue

An item is overdue when:

- Its `sla_target_date` (or equivalent SLA deadline field) is before the
  as-of date, AND
- It is not recently closed. "Recently closed" means closed within the
  recent-closed window (e.g. 14 or 21 days before the as-of date).
  Items closed within that window are counted in scope but not as overdue.

The breach rate is:

```
breach_rate = overdue_count / included_primary_count
```

Round to **3 decimal places**.

### Step 5: Compute aging buckets

For overdue items, compute age as:

```
age_days = as_of_date - sla_target_date
```

Bucket counts into: 0–3, 4–7, 8–14, 15–30, 31+.

### Step 6: Compute team and owner hotspots

Count overdue primary items per team. Sort teams alphabetically.

Find the owner/team pair with the most overdue items. If an owner is
missing, use `"UNASSIGNED"` as the owner value. This is the top hotspot.

### Step 7: Compute escalation queue

When the template requires an escalation queue, order overdue primary
items by severity (S1 first, then S2, S3, S4), and then by age descending
within each severity band. The most severe, longest-overdue items appear
first.

### Step 8: Sort and order

- All id lists: sort lexicographically (ASCII ascending).
- Teams: sort alphabetically.
- Duplicate clusters: sort by `primary_id` ascending; `duplicate_ids` in
  each cluster sorted lexicographically.

---

## Workflow: Release readiness assessment

Use this workflow when the task asks for a release ship/no-ship decision,
milestone completion metrics, blocker analysis, or dependency-chain
resolution.

### Step 1: Fetch the release

Call `GET /api/releases/{release_id}` to get the release record and its
milestone list.

### Step 2: Fetch milestone and work item data

For each milestone in the release, fetch work items from the milestone
record or the work items endpoint. Identify which items are primary (not
duplicates) and not cancelled.

### Step 3: Compute milestone completion

For each milestone:

```
completion_pct = (complete_primary / primary_total) × 100
```

"Complete" means the authoritative status is a terminal/closed state.
Round to **1 decimal place**.

Sort milestone results by `milestone_id` ascending.

### Step 4: Identify gating work items

Gating items are **non-complete** primary work items belonging to the
release. They gate readiness because their incomplete status blocks
the release. Sort these ids ascending with no duplicates.

### Step 5: Analyze blockers

Call `GET /api/blockers` and filter to unresolved blockers on release
work items. Count unresolved high-impact blockers by exact cause string.
Use the cause text exactly as it appears in the API response — do not
normalize or rewrite it.

### Step 6: Analyze critical dependency chains

Call `GET /api/dependencies` and find chains where a release work item
is blocked by a dependency that is not yet complete. Walk the chain:

1. Start from each non-complete release work item.
2. Follow dependency edges from blocked item to blocking item.
3. Continue until the chain reaches a non-complete item (the root blocker).
4. Record the path as an ordered list of work item ids: from the blocked
   release item to the non-complete dependency.

Sort chains lexicographically by the full path string representation.

### Step 7: Compute readiness score

```
readiness_score = complete_primary_count / total_primary_count
```

Round to **3 decimal places**.

### Step 8: Decide ship recommendation

- If any gating items are `S1` severity, or blockers are unresolved,
  or readiness score is below a reasonable threshold (e.g. below 0.70):
  `NO_SHIP`.
- If readiness is adequate but some lower-severity items remain open:
  `SHIP_WITH_WATCH`.
- If all work is complete and no blockers exist: `SHIP`.

When the answer template constrains the decision to specific enum values,
honor those constraints. The exact threshold should be informed by the
data: if more than ~30% of primary work is incomplete, or if high-severity
gating items exist, `NO_SHIP` is typically appropriate.

---

## General ordering and precision rules

These rules apply across all workflows unless the task's answer template
overrides them:

- **Work item id lists**: sort lexicographically (ASCII ascending).
- **Team name lists**: sort alphabetically.
- **Category lists**: the canonical order is NewFeature, TechDebt,
  Reliability, Security.
- **Percentages**: round to 1 decimal place unless the template specifies
  otherwise.
- **Rates (breach, readiness)**: round to 3 decimal places.
- **gap_pct**: always `actual_pct − target_pct`.
- **Duplicate clusters**: sort by `primary_id` ascending, with
  `duplicate_ids` within each cluster sorted lexicographically.

---

## Reference

See [references/api-reference.md](references/api-reference.md) for the
complete endpoint catalog, field dictionary, and data-model notes.
