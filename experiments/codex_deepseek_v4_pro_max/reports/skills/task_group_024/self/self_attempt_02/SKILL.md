---
name: portfolio-analysis
description: Shared environment portfolio analysis for engineering work-item datasets. Use when the user needs to produce a structured JSON answer for portfolio mix, SLA aging, or release readiness from REST + SQL endpoints with portfolio-category classification, duplicate/primary separation, and defined numerical-precision ordering conventions.
---

# Portfolio Analysis Skill

## Overview

This skill codifies reusable rules for analysing engineering portfolio data served through a shared environment that exposes REST endpoints and a restricted read-only SQL query endpoint. The three canonical analysis types are **portfolio mix**, **SLA aging**, and **release readiness**. Every answer is a single JSON object following a supplied template schema; prose outside the JSON is forbidden.

## Environment

- The shared environment base URL is provided at runtime as `<TASK_ENV_BASE_URL>`.
- Runtime access notes live in `environment_access.md` (or equivalent path) and list the available endpoints and any required tokens.
- All endpoints are rooted at the base URL.

### Available REST Endpoints (typical)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | List all work items |
| GET | `/api/work-items/{id}` | Single work item detail |
| GET | `/api/mix-targets` | Portfolio category target percentages |
| GET | `/api/sla-policy` | SLA thresholds by category/severity |
| GET | `/api/releases` | List releases |
| GET | `/api/releases/{id}` | Single release detail |
| GET | `/api/milestones` | List milestones |
| GET | `/api/dependencies` | Work-item dependency graph |
| GET | `/api/blockers` | Work-item blocker records |
| POST | `/api/query` | Restricted read-only SQL |

### SQL Query Endpoint

- **Method**: POST
- **Headers**: `Content-Type: application/json` and `X-Env-Token: portfolio-readonly` (or the token documented in the runtime access file).
- **Body**: `{"sql": "<SELECT or WITH>", "params": ["<value>"]}`
- **Constraints**:
  - Exactly one SQL statement per request.
  - Only `SELECT` or `WITH` statements allowed (read-only).
  - `params` must be a JSON array (use positional `?` placeholders).
  - At most 1000 rows returned per query.

## Data Model Conventions

### Portfolio Categories

Four canonical categories, always in this order:

1. **NewFeature** – new user-facing functionality
2. **TechDebt** – code health, refactoring, platform improvements
3. **Reliability** – availability, durability, monitoring, incident follow-up
4. **Security** – vulnerabilities, auth, encryption, compliance

### Primary vs. Non-Primary Records

Work items exist in several quality tiers. Always separate:

- **Primary records** – the canonical, authoritatively-fields version of a work item. Use these for counts, percentages, and metric calculations.
- **Duplicate records** – point to another work item (e.g., via a `duplicate_of` field or similar relationship). Report them in `duplicate_clusters` or `excluded_duplicate_ids` but never count them as primary.
- **Cancelled records** – status is cancelled; exclude from the closed portfolio.
- **Distractor records** – same scope but not primary closed portfolio work; exclude and report.
- **Stale mirror/export fields** – flag with `ignored_mirror_status_and_legacy_category: true` and use authoritative fields instead.

### Classification Conflict Resolution

When a work item has conflicting signals (disagreeing `type`, `label`, and `title`), resolve using portfolio category conventions:

- Prefer the authoritative `category` or `portfolio_category` field over derived labels.
- When fields disagree, use the signal that best matches the portfolio category definitions above.
- Security trumps Reliability when both apply.
- TechDebt trumps NewFeature for purely internal/platform changes.

## Ordering Conventions

- **Work item IDs**: sort lexicographically ascending (default) or by `closed_at` ascending then `id` ascending when time order matters.
- **Team names**: alphabetical ascending.
- **Categories**: always NewFeature, TechDebt, Reliability, Security (fixed order).
- **Duplicate clusters**: sort by `primary_id` ascending; within a cluster sort `duplicate_ids` lexicographically ascending.
- **Milestones**: sort by `milestone_id` ascending.
- **Dependency chains**: sort lexicographically by the full joined path.
- **Gating work item IDs**: sorted ascending, no duplicates.
- **Escalation queues**: overdue items in priority order (S1 before S2 before S3 before S4; ties broken by oldest SLA target date first).

## Numerical Precision

- **Percentages in mix/gap tables** and **milestone completion**: round to **1 decimal place**.
- **Breach rates** and **readiness scores**: round to **3 decimal places**.
- `gap_pct = actual_pct - target_pct` (in percentage points).
- Counts are always integer item counts (not story points).

## Analysis Types

### 1. Portfolio Mix

**Purpose**: Compare the actual distribution of closed work items across the four portfolio categories against a target mix.

**Key steps**:
1. Load the `mix_targets` row matching the `scope_id`.
2. Collect in-scope closed work items (by team, product area, quarter).
3. Classify each item into exactly one portfolio category.
4. Exclude duplicates, cancelled items, and distractors.
5. Compute count-based percentages, compare with targets, and compute gaps.
6. Identify under-invested categories (negative `gap_pct`).
7. Recommend a follow-up action:
   - `REBALANCE_CAPACITY` when there are negative gaps.
   - `INVESTIGATE_DATA_QUALITY` when data conflicts are present.
   - `MAINTAIN_CURRENT_MIX` when no negative gaps exist.

**Template fields**: `scope`, `included_work_item_ids`, `category_counts`, `category_percentages` / `mix_table`, `gap_table`, `under_invested_categories`, `follow_up_action`, `exclusion_flags` / `excluded_distractor_ids`.

### 2. SLA Aging

**Purpose**: Measure how many SLA-governed work items are overdue, their aging distribution, and team/owner hotspots.

**Key steps**:
1. Load the SLA policy to determine thresholds per category and severity.
2. Filter work items by team, category, and status (not recently closed within the window).
3. Separate primary from duplicate records.
4. Classify each primary item by SLA status (overdue or not) based on the SLA target date relative to the as-of date.
5. Compute aging buckets: `0-3`, `4-7`, `8-14`, `15-30`, `31+` days overdue.
6. Identify the team/owner hotspot with the most overdue primary records.
7. Compute breach rate = overdue primary count / included primary count.
8. When severity is available, produce severities S1–S4 and an escalation queue.

**Template fields**: `scope`, `included_primary_ids`, `overdue_primary_ids`, `aging_bucket_counts`, `team_overdue_counts`, `top_hotspot`, `duplicate_clusters`, `missing_owner_ids`, `breach_rate`, `overdue_counts_by_severity`, `escalation_queue_ids`.

### 3. Release Readiness

**Purpose**: Decide whether a release can ship based on milestone completion, blockers, and dependency health.

**Key steps**:
1. Load the release record by release ID.
2. Load all milestones belonging to this release.
3. For each milestone, count completed primary work items vs. total primary work items.
4. Identify gating work items: non-complete items tied to the release that gate readiness.
5. Collect unresolved high-impact blockers and group counts by exact cause text.
6. Trace critical dependency chains: ordered work-item-ID paths from a blocked release item to a non-complete dependency.
7. Compute readiness score = completed primary work / total primary work.
8. Decide the ship verdict:
   - `SHIP`: readiness score meets threshold, no unresolved high-impact blockers.
   - `SHIP_WITH_WATCH`: ship but with unresolved blockers or incomplete critical dependencies.
   - `NO_SHIP`: readiness score too low or critical blocking issues.

**Template fields**: `release_id`, `ship_decision`, `milestone_completion`, `gating_work_item_ids`, `blocker_cause_counts`, `critical_dependency_chains`, `readiness_score`.

## Answer Delivery

- Output a **single JSON object** that conforms exactly to the provided `answer_template.json` schema.
- Do not include any prose, explanation, or markdown wrapping outside the JSON object.
- Validate all field names, enum values, array cardinalities, and numerical formats against the template before returning.
- Use the exact field names and structure from the template — do not rename or restructure.

## Excluded Records Reporting

When the template requires exclusion reporting:

- **Excluded duplicate IDs**: items whose `duplicate_of` or equivalent field points to another work item.
- **Excluded cancelled IDs**: items with status `cancelled` (or equivalent terminal cancelled status).
- **Excluded distractor IDs**: in-scope items that match the team/product-area/quarter filters but should not be counted as primary closed portfolio work (e.g., mirror records, legacy-category items, or items whose authoritative status is not closed).
- Always set `ignored_mirror_status_and_legacy_category` to `true` to signal that stale mirror and legacy fields were consciously ignored in favour of authoritative sources.
