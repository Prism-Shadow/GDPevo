---
name: eng-portfolio-review
description: "Engineering portfolio intelligence for mixed work-tracking environments. Use when preparing portfolio mix reviews, SLA aging audits, release readiness assessments, or any analysis of work items across teams and product areas. Handles: (1) portfolio category classification of work items into NewFeature, TechDebt, Reliability, and Security, (2) target-vs-actual mix gap analysis, (3) SLA overdue and aging bucket calculations with severity-based policies, (4) release readiness scoring from milestone completion, blocker, and dependency data, (5) detection and exclusion of duplicates, cancelled items, stale mirror fields, and legacy category signals. Trigger on phrases like 'portfolio mix review', 'SLA aging audit', 'release readiness assessment', 'closed work portfolio', 'engineering portfolio', 'mix target analysis', or when working with work item data from the shared task environment API."
license: MIT
compatibility: designed for deepagents-code
---

# Engineering Portfolio Review

## Overview

Analyse work-tracking data from the task environment API to produce portfolio mix
reviews, SLA aging audits, and release readiness assessments. The environment
exposes REST endpoints for work items, mix targets, SLA policy, releases,
milestones, dependencies, and blockers. The data contains deliberate distractor
signals (stale mirror fields, legacy categories, duplicate records, cancelled
items) that must be handled with explicit exclusion and classification rules.

## Quick Start

Fetch environment data with the bundled query script:

```bash
TASK_ENV_BASE_URL=http://task-env:9024 python scripts/query_env.py work-items
```

All endpoints share a common base URL provided in the task prompt. No
authentication is required for the standard GET endpoints. The SQL query
endpoint (`POST /api/query`) may require a token supplied in
`environment_access.md`.

Available endpoints: `/api/work-items`, `/api/work-items/{id}`,
`/api/mix-targets`, `/api/sla-policy`, `/api/releases`, `/api/releases/{id}`,
`/api/milestones`, `/api/dependencies`, `/api/blockers`, `/api/query`.

## Portfolio Category Classification

Every included work item must be classified into exactly one of four categories:
**NewFeature**, **TechDebt**, **Reliability**, **Security**. Use the priority
chain below. See [references/classification.md](references/classification.md)
for the full label-to-category mapping and worked examples.

### Classification Priority Chain

1. **Labels** (strongest signal). Scan the `labels` array for category keywords.
   When multiple category signals are present, resolve with this priority:
   Security > Reliability > TechDebt > NewFeature.
2. **Work type** (`work_type` field). Used when labels produce no clear signal.
3. **Legacy category** (`legacy_category` field). Used as a tiebreaker when
   labels and work_type are ambiguous. Never use as a primary signal.
4. **Title keywords**. Final tiebreaker. Scan the `title` string for
   category-signal substrings.

### Special Signal Handling

- **Stale markers**: When a title contains "stale" next to a category keyword
  (e.g. "stale security label"), the referenced classification signal is
  unreliable. Deprioritise that signal and rely on remaining signals.
- **`stale-export` label**: Treat as noise. A `stale-export` label does not
  contribute to any category signal. Rely on other labels and fields.
- **`mirror_status` field**: Always ignore. Use `status` as the authoritative
  state. The `mirror_status` field is a stale export artefact.
- **`legacy_category` field**: Never use as the primary classification signal.
  Use only as a tiebreaker when signals from labels and work_type are
  ambiguous or absent.

### Classification Examples

| Labels | Work Type | Legacy | Title | Result |
|--------|-----------|--------|-------|--------|
| `[feature, rollout, security]` | Feature | security | "...stale security label..." | **Security** — the security label is present; the title's "stale" descriptor flags a stale *label* but the label is genuinely a security signal |
| `[auth, encryption, cleanup, refactor]` | Refactor | tech-debt | — | **TechDebt** — labels are ambiguous (auth/encryption suggest Security, refactor suggests TechDebt); legacy tiebreaker resolves to TechDebt |
| `[reliability, latency, flaky]` | Bug | quality | — | **Reliability** — labels are unambiguous reliability signals |
| `[feature, rollout]` | Enhancement | security | — | **Security** — no label signal; legacy tiebreaker tips to security |
| `[cleanup, flaky, reliability]` | Chore | quality | "queue cleanup for flaky reliability alert" | **Reliability** — labels have a clear reliability signal |
| `[migration, cleanup, auth]` | Dependency | security | — | **Security** — auth label + security legacy agree |
| `[outage, reliability, feature]` | Enhancement | new | — | **Reliability** — labels provide a reliability signal |

## Exclusion Rules

Before counting or including a work item, apply these exclusion checks in order:

1. **Cancelled**: `status == "Cancelled"` -> exclude entirely. Record the ID as
   an excluded cancelled item but do not count it in any category.
2. **Duplicate**: `status == "Duplicate"` or `duplicate_of` is non-null ->
   exclude from primary counts. Record the ID and its `duplicate_of` reference
   for the duplicate-cluster report. The referenced primary item stays in the
   primary set unless it is also excluded by another rule.
3. **Out-of-scope date/quarter**: Only include items whose `closed_at` falls
   within the scope date range or quarter. Items with `closed_at: null` are
   never included in closed-portfolio analysis.
4. **Scope mismatch**: Filter by the specified `team` and `product_area` values
   from the task scope.

## SLA Aging

See [references/sla-aging.md](references/sla-aging.md) for full methodology,
aging bucket definitions, and escalation ordering rules.

### Quick SLA Rules

- The SLA policy endpoint returns a severity-to-`days_to_due` map.
- An item is **overdue** when `created_at + days_to_due < as_of` and the item
  is not yet closed (`closed_at` is null or after `as_of`).
- The **recent closed window** covers items closed within N days before
  `as_of`. These are not overdue even if they were past due at close.
- **Aging buckets**: Compute `(as_of - created_at).days` for every open primary
  item. Bucket into 0-3, 4-7, 8-14, 15-30, 31+ days.
- **SLA breach rate** = `len(overdue_primary_ids) / len(included_primary_ids)`,
  rounded to 3 decimal places.
- **Escalation order**: Sort overdue items by severity (S1 first), then by age
  descending within the same severity tier.

## Release Readiness

See [references/release-readiness.md](references/release-readiness.md) for the
complete workflow.

### Quick Release Rules

- Fetch the release, its milestones, and all work items assigned to those
  milestones.
- **Primary work**: exclude Duplicate/Cancelled items per the standard exclusion
  rules.
- **Milestone completion**: `complete_primary / primary_total` per milestone.
  An item is complete when `status` is in {Verified, Deployed, Done, Closed}.
- **Gating work items**: non-complete primary release work items that have
  open high-severity blockers or unresolved critical dependencies.
- **High-impact blockers**: blockers with `severity` in {Critical, High} and
  `status != "Resolved"`.
- **Ship decision**:
  - `NO_SHIP` when any high-impact blockers exist or any milestone is below
    a completion threshold.
  - `SHIP_WITH_WATCH` when all milestones meet minimum thresholds but minor
    issues remain.
  - `SHIP` when all milestones are fully complete with no open blockers.
- **Readiness score** = `completed_primary / total_primary`, rounded to 3
  decimal places.

## Portfolio Mix Analysis

### Mix Targets

Fetch `/api/mix-targets` and locate the row matching the task's `scope_id`.
Extract `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, and
`security_pct`. These are decimal values (e.g. 0.34 = 34.0%). Convert to
percentage points by multiplying by 100 and rounding to 1 decimal place.

### Actual Mix

After classifying every included work item (see Classification section),
compute category counts and percentage shares:

```
actual_pct = round((category_count / total_included) * 100, 1)
gap_pct    = round(actual_pct - target_pct, 1)
```

### Gap Analysis

- **Under-invested categories**: categories with `gap_pct < 0`, sorted from
  most negative to least negative.
- **Largest deficit**: the single category with the most negative `gap_pct`.
- **Recommended action**: `REBALANCE_CAPACITY` toward the largest deficit
  category. Assign the owner team that has the most included work in that
  category, or the team with the largest overall share of included work.

## Output Ordering Conventions

- Work item ID lists: sort lexicographically (ascending) unless the task
  specifies `closed_at` ascending then ID ascending.
- Team lists: sort alphabetically.
- Category tables: always order as NewFeature, TechDebt, Reliability, Security.
- Duplicate clusters: sort by `primary_id` ascending; `duplicate_ids` ascending
  within each cluster.
- Percentages: round to 1 decimal place (portfolio) or 3 decimal places (SLA
  breach rate, readiness score).

## Scripts

- [`scripts/query_env.py`](scripts/query_env.py) — Fetch data from any task
  environment API endpoint. Supports all listed GET endpoints and POST
  `/api/query`.

## References

- [`references/classification.md`](references/classification.md) — Full
  label-to-category mapping, edge cases, and worked examples.
- [`references/sla-aging.md`](references/sla-aging.md) — SLA overdue
  calculation, aging buckets, escalation queue, and breach rate methodology.
- [`references/release-readiness.md`](references/release-readiness.md) —
  Release readiness workflow, milestone completion, blocker analysis,
  dependency chains, and ship decision logic.
