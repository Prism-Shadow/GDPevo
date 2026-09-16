---
name: engineering-portfolio
description: "Portfolio-mix review, SLA aging audit, and release-readiness assessment for an engineering work-item environment exposed through a REST API. Use when a task asks you to classify closed work items into portfolio categories (NewFeature, TechDebt, Reliability, Security), compare actual mix against target mix, audit SLA breaches and overdue aging, assess release readiness against milestones and blockers, or produce structured JSON answers from work-item, release, milestone, blocker, dependency, mix-target, and SLA-policy endpoints. Also use when the task references scope_id-based mix targets, as-of-date SLA windows, release gating, or duplicate/cancelled exclusion logic in an engineering-portfolio context."
license: MIT
compatibility: designed for deepagents-code
---

# Engineering Portfolio Analysis

## Overview

This skill covers three analytical workflows against a shared engineering work-item REST API:

1. **Portfolio Mix Review** — Classify closed work items into four categories (NewFeature, TechDebt, Reliability, Security), compare count-based actual mix against target mix percentages, identify under-invested categories, and recommend a rebalance action.
2. **SLA Aging Audit** — Filter primary (non-duplicate, non-cancelled) work items by team and SLA-relevant categories, compute aging buckets relative to an as-of date, identify overdue items against SLA policy by severity, flag duplicate clusters, missing owners, and calculate breach rate.
3. **Release Readiness Assessment** — For a specific release, compute milestone completion metrics, identify gating (non-complete) work items, count unresolved high-impact blockers by cause, trace critical dependency chains, and produce a readiness score and ship decision.

All workflows share a common data model. See [references/data_model.md](references/data_model.md) for the full field reference and API endpoint details.

## Common Rules for All Workflows

### Authoritative vs Stale Fields
- The `status` field on each work item is authoritative. Ignore `mirror_status` — it is a stale export snapshot and does not reflect current state.
- The `legacy_category` field is a legacy hint only. Do not use it as the primary classification signal.
- For release-related work, use the work item's `release_id` and `milestone_id` fields, not any mirrored or export-derived fields.

### Duplicate and Cancelled Handling
- Work items with `status` "Duplicate" must be excluded from primary counts. Their `duplicate_of` field points to the canonical item. Report excluded duplicate IDs separately.
- Work items with `status` "Cancelled" must be excluded from primary counts. Report excluded cancelled IDs separately.
- A Duplicate record may itself have been closed within the scope window. Still exclude it from primary counts regardless of its `closed_at` date.

### Primary vs Non-Primary Records
- A "primary" work item is one whose `status` is not "Duplicate" and not "Cancelled".
- Primary items are the denominator for all counts, percentages, and rates.
- Duplicate clusters (canonical to duplicates) should be reported as metadata but must not inflate primary counts.

### Ordering Conventions
- Sort work-item ID lists lexicographically (ASCII sort) unless the task template specifies a different order (e.g. `closed_at` ascending then `id` ascending).
- Sort team lists alphabetically.
- Sort gap/mix table rows in the fixed category order: NewFeature, TechDebt, Reliability, Security.
- Sort duplicate clusters by `primary_id` lexicographically, with `duplicate_ids` within each cluster sorted lexicographically.

### Numeric Precision
- Percentages derived from counts: divide the category count by the primary total, multiply by 100, round to 1 decimal place (portfolio mix tasks) or 3 decimal places (breach rate, readiness score).
- Gap values: `actual_pct - target_pct`, rounded to the same precision as the percentages.
- When a category has zero items and the total is zero, treat percentages as 0.0.

## Workflow 1: Portfolio Mix Review

### Scope Determination
1. Read the task prompt for: scope_id, quarter (e.g. 2025-Q4), teams, product area(s), and target scope_id.
2. Fetch mix targets from `GET /api/mix-targets` and find the row whose `scope_id` exactly matches the target scope_id from the prompt. This row provides the target percentages: `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct`. These are decimals (e.g. 0.34 = 34%); multiply by 100 and round to 1 decimal place for display.
3. The quarter defines the closed-date window: a closed work item's `closed_at` must fall within the calendar quarter (e.g. 2025-Q4 = 2025-10-01 through 2025-12-31).

### Filtering In-Scope Work Items
Fetch all work items from `GET /api/work-items`. Apply these filters:
- `team` matches one of the prompt teams
- `product_area` matches one of the prompt product areas (if specified)
- `closed_at` falls within the quarter window and is not null
- `status` is not "Duplicate" and not "Cancelled"

Watch for "distractor" records — items that match on team and product_area but use a different data schema (e.g. wrapped in a `work_item` sub-object with `legacy_category` instead of `work_type`). Exclude these from the primary mix and report them separately when the template has an exclusion field for them.

### Portfolio Category Classification
Assign each included primary work item to exactly one of: NewFeature, TechDebt, Reliability, Security.

Classification uses a three-signal cascade. Start with the strongest signal and resolve conflicts in order:

**Signal 1 — `work_type`** (strongest):
- `Security`, `Compliance` to Security
- `Reliability` to Reliability
- `Incident` to Reliability (incident follow-ups represent reliability investment), unless labels are exclusively security (cve/auth/encryption) with no reliability signals
- `Feature` to NewFeature (unless overridden by labels)
- `Enhancement` to check labels; defaults toward Security when no clear feature/reliability signal
- `Refactor`, `Chore`, `Dependency` to TechDebt
- `Bug` to check labels; with reliability labels to Reliability; with security labels to Security; otherwise to TechDebt

**Signal 2 — `labels`** (secondary):
- Labels containing `security`, `cve`, `encryption` push toward Security
- Labels containing `reliability`, `incident`, `outage`, `latency` push toward Reliability
- Labels containing `cleanup`, `refactor`, `migration`, `dependency` push toward TechDebt
- Labels containing `feature`, `rollout` (without security/reliability override) push toward NewFeature

**Signal 3 — `title`** (tiebreaker only):
- When work_type and labels conflict or are ambiguous, the title text can break the tie. Keywords: "security", "cve", "encrypt", "auth" to Security; "reliability", "incident", "outage", "latency", "retry", "flaky" to Reliability; "cleanup", "refactor", "migrat" to TechDebt; "feature", "rollout", "enhancement" to NewFeature.

**Resolution priority**: Security signals dominate Reliability signals dominate TechDebt signals dominate NewFeature. When an item has both security and reliability signals, classify as Security. When it has reliability and tech-debt signals, classify as Reliability. The presence of any security-relevant label (security, cve, encryption) on a Feature or Enhancement work_type overrides the NewFeature default and classifies it as Security.

### Mix Gap Analysis
1. Count items per category to `category_counts`.
2. Compute actual percentages: `(count / total_primary) * 100`, rounded to 1 decimal.
3. Compare against target percentages from the mix-target row.
4. Compute gaps: `actual_pct - target_pct`.
5. Identify under-invested categories: those with negative gap, ordered from most negative to least negative.
6. Recommend follow-up action:
   - `REBALANCE_CAPACITY` with `rationale_code` `LARGEST_NEGATIVE_GAP` when any gap is negative; set `primary_category` to the most-negative-gap category and `secondary_category` to the second-most-negative (or null if none).
   - `MAINTAIN_CURRENT_MIX` with `rationale_code` `NO_NEGATIVE_GAPS` when no gaps are negative.
   - `INVESTIGATE_DATA_QUALITY` with `rationale_code` `DATA_CONFLICT` when the data has conflicts that prevent a clean recommendation.

## Workflow 2: SLA Aging Audit

### Scope Determination
1. Read the task prompt for: teams, SLA-relevant categories (typically Reliability and Security), as-of date, and recent closed window in days.
2. Fetch SLA policy from `GET /api/sla-policy`. This returns an array of `{severity, days_to_due}` objects. Map each severity level to its SLA due window.

### Filtering In-Scope Work Items
Fetch all work items from `GET /api/work-items`. Apply:
- `team` matches one of the prompt teams
- The item belongs to one of the SLA-relevant categories (classify using the same portfolio category rules as Workflow 1)
- `status` is not "Cancelled" (Duplicate items are excluded from primary but tracked in duplicate clusters)
- `closed_at` is either null (open work) or falls within the recent closed window (closed_at >= as_of_date - window_days)

### Primary vs Duplicate Separation
- Work items with `status` "Duplicate" form duplicate clusters. Group them by `duplicate_of` (the canonical primary id).
- The canonical primary item must itself be in scope. If a duplicate points to an item outside scope, still report the cluster but do not count the canonical in primary totals.
- All non-Duplicate, non-Cancelled items are primary.

### SLA Breach Calculation
For each primary item:
1. If `closed_at` is not null, the item is already closed — it is not overdue.
2. If `closed_at` is null, compute age: `as_of_date - created_at` in days.
3. Look up the SLA `days_to_due` for the item's `severity`.
4. If `age > days_to_due`, the item is overdue.

### Aging Buckets
For each primary item (open or recently closed), compute age from `created_at` to `as_of_date` in days. Bucket into: 0-3, 4-7, 8-14, 15-30, 31+. Count items per bucket.

### Hotspot and Team Overdue
- Compute overdue counts per team.
- Find the owner/team pair with the most overdue primary items. If multiple tie, use the one with the owner appearing first alphabetically. If owner is missing, use "UNASSIGNED".
- Report `missing_owner_ids`: primary items with null/empty `owner`.

### Breach Rate
`breach_rate = overdue_primary_count / included_primary_count`, rounded to exactly 3 decimal places.

### Escalation Queue (when required)
Order overdue primary items by priority for follow-up. Use this precedence: S1 before S2 before S3 before S4. Within the same severity, order by earliest `created_at` first (oldest items first).

## Workflow 3: Release Readiness Assessment

### Scope Determination
1. Read the task prompt for the release ID under review.
2. Fetch the release from `GET /api/releases/{release_id}` or from the full list at `GET /api/releases`.
3. Fetch all milestones from `GET /api/milestones`. Filter to those whose `release_id` matches the target release.
4. Fetch all work items, blockers, and dependencies from their respective endpoints.

### Milestone Completion
For each milestone of the release (sorted by `milestone_id` ascending):
1. Find all work items whose `milestone_id` matches and whose `status` is not "Duplicate" (primary work items).
2. Count completed primary items: those with `status` in the completed set. Treat any of these as completed: `Done`, `Deployed`, `Verified`, `Closed`, `Resolved` (use the exact status strings observed in the API).
3. Compute `completion_pct = (complete_primary / primary_total) * 100`, rounded to 1 decimal.

### Gating Work Items
Identify non-complete release work items that gate readiness:
- Work items whose `release_id` matches the target release
- `status` is not in the completed set AND not "Duplicate"
- Sort ascending, no duplicates.

### Blocker Analysis
Fetch blockers from `GET /api/blockers`. Filter for:
- `release_id` matches the target release
- `severity` is "High" or "Critical" (high-impact only)
- `status` is not "Resolved" (unresolved only)

Count by exact `cause` string. Use the cause text verbatim as the key.

### Critical Dependency Chains
Fetch all dependencies from `GET /api/dependencies`. For each dependency edge:
- The `blocked_id` is the release work item that is blocked.
- The `depends_on_id` is the work item it depends on.
- The `relation` describes the nature.

A critical dependency chain exists when: a release work item (has the target `release_id`) is `blocked_id` in a dependency edge, AND the `depends_on_id` work item is itself not complete (status not in completed set).

Build chains by walking from the blocked release work item. If the dependency is itself blocked by another item (transitive), include the full ordered path: `[blocked_release_item, ..., non_complete_dependency]`. Each link in the chain represents one dependency edge.

Sort chains lexicographically by the full path (compare the string representation of the path array).

If no such chains exist, return an empty array.

### Readiness Score
`readiness_score = total_completed_primary_release_items / total_primary_release_items`, rounded to 3 decimal places.

Count across all milestones: sum of completed primary items divided by sum of all primary items for the release.

### Ship Decision
- `SHIP` when readiness_score >= 0.95 AND there are zero unresolved high-impact blockers AND zero gating work items.
- `SHIP_WITH_WATCH` when readiness_score >= 0.80 AND there are zero unresolved high-impact blockers, but there are gating work items.
- `NO_SHIP` when there are unresolved high-impact blockers, OR readiness_score < 0.80, OR there are gating work items of a severity or nature that block release confidence.

When in doubt between SHIP_WITH_WATCH and NO_SHIP, the presence of any unresolved High or Critical blocker is decisive for NO_SHIP.

## Resources

- **[references/data_model.md](references/data_model.md)** — Complete field reference for every API entity, endpoint catalog, and status value semantics. Load this when you need to look up field names, status values, or endpoint behavior.
