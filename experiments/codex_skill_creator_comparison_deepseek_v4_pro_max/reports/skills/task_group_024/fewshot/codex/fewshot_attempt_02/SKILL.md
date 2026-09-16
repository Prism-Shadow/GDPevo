---
name: eng-portfolio-review
description: Engineering portfolio review and analysis against a shared portfolio-management API. Use when the user needs to compute portfolio mix vs targets, audit SLA aging for reliability/security work, or assess release readiness using work items, milestones, blockers, dependencies, and SLA policy data. Covers closed-work mix analysis, SLA breach and aging reports, release readiness scoring with ship decisions, and stale-field / duplicate / cancelled record exclusion.
---

# Engineering Portfolio Review

## Environment

The task environment is a shared HTTP API. The base URL is always supplied in the prompt. All endpoints return JSON.

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | /api/work-items | Full work-item collection |
| GET | /api/work-items/ITEM_ID | Single work item |
| GET | /api/mix-targets | Portfolio category targets |
| GET | /api/sla-policy | Severity-to-days SLA policy |
| GET | /api/releases | All releases |
| GET | /api/releases/RELEASE_ID | Single release with blockers and milestones |
| GET | /api/milestones | All milestones |
| GET | /api/dependencies | Dependency graph |
| GET | /api/blockers | All blockers |
| POST | /api/query | Read-only SQL, header X-Env-Token: portfolio-readonly |

### SQL Query Endpoint

POST /api/query accepts a JSON body with sql and params fields. The work_items table has these columns:

id, title, work_type, status, team, owner, product_area, created_at, due_at, closed_at, severity, priority, labels (JSON array string), story_points, release_id, milestone_id, duplicate_of, mirror_status, legacy_category

Date columns use YYYY-MM-DD format. severity is S1-S4. The SQL dialect supports ? positional parameters.

Use the query endpoint for all filtered retrieval. Prefer single targeted queries over fetching the full collection.

## Core Concepts

### Primary vs Non-Primary Work Items

A work item is primary (countable, included) when:
- status is NOT Duplicate or Cancelled
- duplicate_of is null (a non-null duplicate_of means it points at another record and should be excluded as a duplicate proxy)

### Stale Fields

Never use these fields for decisions - they are export snapshots that may be out of date:
- mirror_status - use status instead
- legacy_category - classify items yourself from work_type, labels, and title signals

### Exclusion Rules

When assembling a primary work set for any analysis:
1. Duplicates: status = Duplicate OR duplicate_of IS NOT NULL => add to duplicate list, exclude from primary counts
2. Cancelled: status = Cancelled => add to cancelled list, exclude from primary counts
3. Distractors (mix analysis): items that share the scope team/product-area but are duplicates or cancelled - list separately, do not count in primary mix

For each excluded duplicate record, record the primary_id it references via duplicate_of.

## Classification: Portfolio Categories

Every included work item must be assigned exactly one of four categories: NewFeature, TechDebt, Reliability, Security.

### Signal Sources (in priority order)

1. Labels (highest weight): parse the JSON array; check for category-signal keywords
2. work_type: the item declared type
3. Title: scan for category-signal keywords (used as tiebreaker)

### Signal Keywords

Security category signals:
- Labels: security, cve, auth, encryption, compliance
- work_type: Security, Compliance
- Title: security, cve, auth, encrypt, consent

Reliability category signals:
- Labels: reliability, outage, latency, incident, flaky
- work_type: Incident, Reliability
- Title: reliability, outage, latency, incident

TechDebt category signals:
- Labels: cleanup, refactor, migration, deprecate, dependency, debt
- work_type: Refactor, Chore, Dependency, Bug
- Title: cleanup, refactor, migration, deprecate, dependency

NewFeature category signals:
- Labels: feature, rollout, enhancement
- work_type: Feature, Enhancement
- Title: feature, rollout, enhancement

### Conflict Resolution

When signals from different categories are present:

1. Security signals dominate: a security keyword in labels or work_type=Security/Compliance overrides a Feature/Enhancement work_type - the item is Security
2. Reliability signals override NewFeature: work_type=Incident or reliability keywords in labels override Feature/Enhancement work_type - the item is Reliability
3. Within the same domain: when labels are mixed but all point to the same category or adjacent categories, use work_type as the tiebreaker
4. Title as tiebreaker: when labels and work_type are ambiguous, scan the title for the strongest category keyword

Decision tree:
1. Does the item have any Security-label keyword, Security/Compliance work_type, or Security title keyword? => Security
2. Does the item have any Reliability-label keyword, Incident/Reliability work_type, or Reliability title keyword? => Reliability
3. Does the item have any TechDebt-label keyword, Refactor/Chore/Dependency/Bug work_type, or TechDebt title keyword? => TechDebt
4. Otherwise => NewFeature

Apply these checks in order. The first match wins.

### Count-Based Mix

Percentages are based on item counts, not story points. Round all percentages to 1 decimal place.

actual_pct = round((count / total_included) * 100, 1)
gap_pct = round(actual_pct - target_pct, 1)

## SLA Aging Analysis

### SLA Policy

The /api/sla-policy endpoint returns a mapping of severity to days_to_due:
- S1: 3 days
- S2: 10 days
- S3: 21 days
- S4: 45 days

### Determining Overdue Status

For each primary work item in the SLA scope (reliability/security categories), compute:

age_days = as_of_date - created_at  (in days)
is_overdue = age_days > sla_days AND status is not a closed terminal state

Closed terminal states: Closed, Verified, Done, Deployed. Items in Review, In Progress, Backlog, or other non-closed states are still active and can be overdue.

### Aging Buckets

Count primary included items into buckets by age in days: 0-3, 4-7, 8-14, 15-30, 31+.

### Escalation Queue Ordering

When building an escalation queue of overdue primary items, sort by:
1. Severity descending (S1 first, then S2, S3, S4)
2. Within same severity, ID ascending (lexicographic)

### Breach Rate

breach_rate = round(overdue_primary_count / included_primary_count, 3)

### Missing Owners

Any primary included item with owner that is null or empty is a missing-owner record. List these IDs separately.

## Release Readiness Assessment

### Gathering Release Data

Use GET /api/releases/RELEASE_ID to get the release, its milestones, and its blockers in one call.

For work items in the release, query the SQL endpoint filtering by release_id. For dependencies, filter the /api/dependencies list by work items belonging to the release.

### Milestone Completion

For each milestone belonging to the release (sorted by milestone_id ascending):
- primary_total: count of primary work items (non-duplicate, non-cancelled) assigned to this milestone
- complete_primary: count of those in a completed terminal state
- completion_pct = round((complete_primary / primary_total) * 100, 1)

Completed terminal states: Closed, Verified, Done, Deployed.

### Gating Work Items

Gating work items are non-complete release work items that block readiness. Include items that:
- Have a status other than completed terminal states
- Are primary (not duplicate, not cancelled)
- Are release-scoped (belong to the release)

Sort ascending, deduplicated.

### Blockers

Filter blockers for the release. Count only unresolved high-impact blockers:
- severity is High or Critical
- status is Open (not Resolved, not Monitoring)

Group by exact cause text, count occurrences.

### Ship Decision

- SHIP: all milestones at 100% completion, zero gating items, zero unresolved high-impact blockers, readiness_score >= 0.95
- SHIP_WITH_WATCH: readiness_score >= 0.80, at most one milestone below 80%, zero Critical blockers
- NO_SHIP: anything worse (gating items present, Critical blockers unresolved, readiness_score < 0.80, or multiple milestones below 80%)

### Readiness Score

readiness_score = round(total_complete_primary / total_primary_denominator, 3)

Where total_primary_denominator is the count of all primary work items across all release milestones, and total_complete_primary is the count of completed primary work items across all milestones.

### Critical Dependency Chains

For each non-complete release work item that is gating readiness, trace dependency chains through the /api/dependencies data. A critical chain is an ordered path [blocked_release_item, ..., non_complete_dependency] where each step follows depends_on_id. Include only chains where the final dependency is also non-complete.

Sort chains lexicographically by the full path representation.

## Portfolio Mix Analysis

### Scope Definition

A mix analysis is scoped by:
- scope_id: matches a mix_targets row
- quarter: e.g., 2025-Q4
- teams: one or more engineering teams
- product_areas: one or more product areas

### Finding In-Scope Work Items

Query work_items for items matching all scope criteria (teams, product areas in the scope). Filter further:
1. Include only items with closed_at in the target quarter (use date range matching - Q4 2025 means closed_at between 2025-10-01 and 2025-12-31)
2. Exclude items with status = Duplicate or status = Cancelled or non-null duplicate_of
3. The remaining items form the closed portfolio mix

Note: the SQL endpoint does not have a quarter column. Filter on closed_at date range instead.

### Target Mix

Find the mix_targets row where scope_id matches the task scope id. The target percentages are new_feature_pct, tech_debt_pct, reliability_pct, security_pct - each as a decimal (multiply by 100 for percentage points).

### Gap Analysis

For each category (in fixed order: NewFeature, TechDebt, Reliability, Security):
- target_pct: target percentage as percentage points rounded to 1 decimal
- actual_pct: round((category_count / total_included) * 100, 1)
- gap_pct: round(actual_pct - target_pct, 1)

Under-invested categories are those with negative gap_pct, sorted from most negative to least negative.

### Follow-Up Actions

- REBALANCE_CAPACITY with LARGEST_NEGATIVE_GAP: when one or more categories have negative gaps
- MAINTAIN_CURRENT_MIX with NO_NEGATIVE_GAPS: when all gaps >= 0
- INVESTIGATE_DATA_QUALITY with DATA_CONFLICT: when exclusion flags reveal data problems that could change conclusions

## Ordering Conventions

Follow these ordering rules in all outputs:
- Work item ID lists: lexicographic ascending (default string sort)
- Team lists: alphabetical
- Category order in tables: NewFeature, TechDebt, Reliability, Security
- Mix item lists: by closed_at ascending, then id ascending
- Duplicate clusters: by primary_id ascending, with duplicate_ids sorted lexicographically
- Milestone lists: by milestone_id ascending
- Dependency chains: lexicographic by full path representation

## Rounding

- Mix percentages and gap percentages: 1 decimal place
- Breach rate: 3 decimal places
- Readiness score: 3 decimal places
- Completion percentages: 1 decimal place

## Workflow

When asked to produce a portfolio review, SLA audit, or release assessment:

1. Read the full prompt for scope (teams, product areas, quarter, as-of date, release id, categories)
2. Fetch reference data: mix-targets (for mix tasks), SLA policy (for SLA tasks), release+milestones+blockers (for release tasks)
3. Query work items using the SQL endpoint with targeted filters on team, product_area, release_id, or status
4. Classify each included item into a portfolio category using the decision tree above
5. Identify and exclude duplicates, cancelled items, and distractors
6. Compute metrics: counts, percentages, gaps, breach rates, readiness scores
7. Build ordered lists: follow the ordering conventions for IDs, teams, categories, chains
8. Output JSON matching the supplied answer template schema exactly

Use the SQL query endpoint as the primary data retrieval method - it is faster and more precise than fetching the full collection and filtering client-side.

## Reference

Detailed API field reference and example response shapes: [api_reference.md](references/api_reference.md)
