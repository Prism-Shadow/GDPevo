---
name: portfolio-review
description: Solve engineering portfolio review tasks (mix analysis, SLA aging, release readiness) against a portfolio-management REST API. Use this skill whenever the prompt mentions portfolio mix, SLA aging, release readiness, work items, mix targets, SLAs, milestones, blockers, or dependencies backed by a task-env HTTP API.
---

# Portfolio Review Skill

You are solving an engineering portfolio review task against a shared REST API environment. Every task follows the same core workflow: explore the API, collect authoritative records, classify and filter work items, compute metrics to specified precision, and return a single JSON answer matching the provided answer template exactly.

## Environment Access

The task provides a base URL (usually `<TASK_ENV_BASE_URL>` or similar) and an access token in `environment_access.md`. Always start by verifying connectivity with `GET /health`.

Available endpoints:
- `GET /api/work-items` — all work items
- `GET /api/work-items/{item_id}` — single work item
- `GET /api/mix-targets` — target mix percentages per scope
- `GET /api/sla-policy` — SLA policy definitions
- `GET /api/releases` — releases
- `GET /api/releases/{release_id}` — single release
- `GET /api/milestones` — milestones
- `GET /api/dependencies` — dependency records
- `GET /api/blockers` — blocker records
- `POST /api/query` — read-only SQL queries (use `X-Env-Token` header)

Access token header: `X-Env-Token: portfolio-readonly`

Use `curl` with `-s` and `-H "X-Env-Token: portfolio-readonly"` for all API calls. For the SQL endpoint, POST a JSON body like `{"sql": "SELECT ..."}`.

## Authoritative Data Rule

Work item records may contain stale mirror/export fields. Always use the **authoritative** fields (e.g., `status`, `category`, `closed_at`, `team`, `owner`, `severity`, `milestone_id`, `release_id`) from the primary record, not mirror duplicates or legacy fields. When the prompt says "do not use stale mirror fields", treat the primary work item row as truth and ignore mirrored copies of the same work item.

## Work Item Classification

Classify each work item into exactly one portfolio category. The valid categories are:

- `NewFeature`
- `TechDebt`
- `Reliability`
- `Security`

When resolving category from conflicting signals (type, label, title), use this priority order:

1. The authoritative `category` field on the work item, if it matches one of the four valid categories.
2. If the category field is ambiguous, null, or absent, inspect the work item's `labels` array for a label matching one of the four categories.
3. If labels do not resolve the category, inspect the `title` for keywords: "security", "vuln", "CVE", "auth", "entitlement", "compliance" → Security; "reliability", "resilience", "failover", "availability", "SLO", "latency" → Reliability; "refactor", "migrate", "upgrade", "debt", "cleanup", "deprecate" → TechDebt; "feature", "enable", "launch", "add", "build", "integrate" → NewFeature.
4. If none of the above resolve, default to `TechDebt` unless the work item content clearly indicates otherwise.

When the prompt says "ignore legacy category" or "ignored_mirror_status_and_legacy_category", only use the authoritative fields as described above.

## Primary vs Non-Primary Records

Work items can appear multiple times in the API: as a primary record and as duplicates, cancelled items, or distractors (records that look in-scope but should not count). Follow these rules:

**Duplicates**: A work item whose authoritative `status` or `type` indicates it is a duplicate of another work item (e.g., status = `duplicate`, or it has a `duplicate_of` field pointing to another ID). Exclude duplicates from primary counts. Group duplicates by the primary ID they reference.

**Cancelled items**: A work item with `status` = `cancelled` (or equivalent). Exclude from primary counts.

**Distractors**: Records that share scope parameters (team, quarter, product area) but are not primary closed portfolio work items. Examples include mirror records, items with non-standard status values that have been superseded, or items pointing to a different release. Exclude these.

Always inspect `status`, `type`, `mirror_of`, `duplicate_of`, and related pointer fields to determine whether a record is primary.

## Mix Analysis Workflow

For portfolio mix reviews:

1. Fetch `/api/work-items` and `/api/mix-targets`.
2. Identify the target mix row matching the scope's `scope_id`.
3. Filter work items by the scope parameters (teams, quarter, product areas). Use the authoritative `team`, `quarter`, and `product_area` fields.
4. Keep only closed primary work items for the quarter. A work item is "closed" when its authoritative `status` indicates completion (typically `closed`, `done`, `completed`). Exclude open, in-progress, cancelled, duplicate, and distractor records.
5. Classify each included work item into one portfolio category.
6. Count items per category. Compute percentages: `(category_count / total_included) * 100`, rounded to 1 decimal place.
7. Compute gaps: `actual_pct - target_pct`, rounded to 1 decimal place.
8. Identify under-invested categories (negative gaps), ordered from most negative to least negative.
9. Determine the follow-up action based on the largest negative gap.

## SLA Aging Workflow

For SLA aging reviews:

1. Fetch `/api/work-items` and `/api/sla-policy`.
2. Filter work items by scope teams. Keep only work items whose authoritative `category` matches the SLA categories (typically `Reliability` and `Security`).
3. Separate primary records from duplicates.
4. For primary records, compute `days_open` from `created_at` (or `opened_at`) to the as-of date. If the item was recently closed (within the window), days open goes from created to closed; otherwise it goes from created to as-of.
5. An item is "overdue" when `days_open` exceeds the SLA threshold for its severity or category, per the SLA policy.
6. Compute aging bucket counts: count primary items by days-open ranges (e.g., 0-3, 4-7, 8-14, 15-30, 31+).
7. Compute team overdue counts: group overdue primaries by team.
8. Find the top hotspot: the owner/team pair with the most overdue primary records. If multiple tie, pick the first alphabetically by team then owner.
9. Compute breach rate: `overdue_primary_count / included_primary_count`, rounded to 3 decimal places.
10. When severity breakdown is required (e.g., S1-S4), group overdue primaries by their authoritative `severity` field.
11. For escalation queues, order overdue primaries by priority: higher severity first, then by oldest (longest days open) first.

## Release Readiness Workflow

For release readiness assessments:

1. Fetch the specific release via `GET /api/releases/{release_id}`.
2. Fetch milestones via `GET /api/milestones` and filter to those belonging to the release (check `release_id` field).
3. For each milestone, fetch the associated work items. Count completed primary work items (authoritative `status` = `closed`/`done`/`completed`) and total primary work items.
4. Compute milestone completion percentages to 1 decimal place.
5. Identify gating work items: non-complete primary work items in the release that block readiness. Include only items whose authoritative `status` is not closed/done/completed and that are not duplicates/cancelled.
6. Fetch blockers via `GET /api/blockers`, filter to high-impact unresolved blockers for this release's work items. Count by exact cause text.
7. Fetch dependencies via `GET /api/dependencies`. Build critical chains: paths from a blocked release work item through its dependencies to the first non-complete dependency. Include only chains where the release work item itself is not complete.
8. Compute readiness score: `completed_primary_count / total_primary_count`, rounded to 3 decimal places.
9. Determine ship decision:
   - `SHIP` if readiness_score >= 0.95 and all milestones have completion_pct >= 90.0 and no critical dependency chains and no unresolved high-impact blockers.
   - `SHIP_WITH_WATCH` if readiness_score >= 0.80 and at most one condition from the SHIP criteria is unmet.
   - `NO_SHIP` otherwise.

## Ordering Conventions

Use these stable ordering rules consistently:

- **Work item ID lists**: sort lexicographically (ASCII order) ascending.
- **Team lists**: sort alphabetically ascending.
- **Milestone lists**: sort by milestone_id ascending (lexicographic).
- **Duplicate clusters**: sort by primary_id ascending; duplicate_ids within each cluster sorted lexicographically ascending.
- **Critical dependency chains**: sort lexicographically by the full path (compare element by element).
- **Included work item IDs for portfolio mix**: order by `closed_at` ascending, then by `id` ascending (lexicographic).
- **Under-invested categories**: most negative gap first.
- **Escalation queue**: highest severity first, then longest days open first (descending).

## Numeric Precision

Apply these precision rules:

- **Percentages**: round to 1 decimal place (e.g., 66.7, 11.1, 0.0).
- **Breach rates and readiness scores**: round to 3 decimal places (e.g., 0.545, 0.688).
- Use standard rounding (half-up).
- Do not add extra trailing zeros beyond the required precision unless the template schema demands it.

## Answer Assembly

Every task provides an answer template (typically `input/payloads/answer_template.json` or similar). Write output to `answer.json` (or wherever the prompt specifies). Follow these rules:

- Study the template's `required` fields, `additionalProperties: false`, `const` values, `enum` constraints, and `pattern` constraints precisely.
- Do not include extra fields beyond the template.
- Match the template's structure exactly: object shapes, array ordering, field names.
- Return only the JSON object. No prose, no markdown fences, no trailing text.
- Validate the output against the template constraints before writing.

## Defensive Checks

Before finalizing any answer, run these checks:

1. All included/excluded IDs are unique (no duplicates within a list).
2. Counts sum correctly: category counts sum to `total_included`.
3. Percentages sum to approximately 100.0 (allow ±0.2 for rounding).
4. Every ID referenced in a computed list (overdue, gating, duplicate clusters) exists in the fetched data.
5. Sorting orders match the conventions above.
6. Precision matches the rules above.

## Common Pitfalls

- **Mirror/export records**: Don't count mirrored copies of work items as separate primary items. Use the authoritative record and exclude mirror pointers.
- **Cancelled items in closed scope**: `status = cancelled` means exclude, even if the item otherwise matches the scope.
- **Duplicate counting**: A duplicate references another work item. Count only the primary, not the duplicate.
- **Stale fields**: When the prompt says to ignore mirror status or legacy category, use only the authoritative `status` and `category` from the primary record.
- **Release vs milestone scope**: Work items may belong to a milestone that belongs to a release. Count them under the release for readiness calculations.

## Reference Files

- [API Reference](api_reference.md) — endpoint details and response shapes
- [Classification Guide](classification_guide.md) — detailed classification examples from the training data
