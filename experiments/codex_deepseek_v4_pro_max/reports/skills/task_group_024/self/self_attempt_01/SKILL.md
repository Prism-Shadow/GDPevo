# Engineering Portfolio Operations Skill

Use this skill when the task involves engineering portfolio data analysis: portfolio mix reviews, SLA aging audits, release readiness assessments, or any work that queries a portfolio REST API with work items, mix targets, milestones, releases, blockers, dependencies, and SLA policies.

## Environment Connection

- The portfolio API base URL is provided at runtime as `<TASK_ENV_BASE_URL>`.
- Read `environment_access.md` for the full endpoint catalog and any required authentication tokens.
- When the `environment_access.md` specifies a restricted SQL query endpoint, use it for complex data retrieval that REST endpoints cannot express.
- SQL queries require the header specified in `environment_access.md`. Only `SELECT` and `WITH` statements are permitted. Parameterize with `?` placeholders and pass values in a `params` array. Results are capped at 1000 rows.

## Field Authority: Authoritative vs. Stale Mirror Fields

Work items may carry both authoritative fields and stale mirror/export copies. This is a recurring data-quality trap.

- **Always use authoritative fields.** The canonical field names are the ones from the live work item schema (e.g., `status`, `portfolio_category`, `owner`, `severity`, `team`, `product_area`, `closed_at`, `duplicate_of`).
- **Ignore mirror/export fields** such as `mirror_status`, `legacy_category`, `exported_owner`, or any field prefixed with `mirror_`, `legacy_`, or `export_`. These are snapshots that may be out of date.
- When a task template asks whether mirror fields were ignored, answer affirmatively (the agent must have relied on authoritative fields).

## Primary vs. Duplicate Records

- Work items may reference another work item as their canonical record via a `duplicate_of` field or equivalent link.
- **Primary records** are those that are not marked as duplicates of another item.
- **Duplicate records** must be excluded from all counts, percentages, rates, and primary ID lists.
- When a task requires reporting duplicate clusters, group them as objects mapping `primary_id` to its `duplicate_ids` array.
- Duplicate clusters must still be reported even though duplicates are excluded from primary metrics.

## Portfolio Category Classification

Every portfolio analysis uses exactly four categories, always in this display order:

1. NewFeature
2. TechDebt
3. Reliability
4. Security

**Classification resolution order:**
1. Use the authoritative `portfolio_category` field if populated with a recognized value.
2. If `portfolio_category` is missing, null, or unrecognized, resolve from `type`, `labels`, and `title` signals using the strongest available signal.
3. Never use `legacy_category` or any mirror field for classification.

## Closed vs. Open Work Items

- **Portfolio mix tasks** count only closed/completed work items. Determine closure from the authoritative `status` field (e.g., `Done`, `Closed`, `Completed`).
- **SLA aging tasks** consider open (non-closed) items and check them against SLA deadlines. Exclude items closed within the `recent_closed_window_days` window, as they were recently resolved.
- **Release readiness tasks** consider all work items linked to the release and milestones. Completion is determined from authoritative status.

## Cancelled and Distractor Exclusion

- **Cancelled items**: Identify work items with a cancelled/withdrawn status from the authoritative `status` field. Exclude them from the primary portfolio mix. Report them in exclusion lists when the task schema requires it.
- **Distractor records**: Some records may appear related to the scope (same team, product area, quarter) but should not be counted as primary closed portfolio work. Common distractors include: items from different quarters mis-tagged, items in non-closed states other than cancelled, or items belonging to different product areas. Exclude them and report in distractor/exclusion lists.

## Mix Target Lookup

- Retrieve mix targets from the `/api/mix-targets` endpoint.
- Filter by `scope_id` to find the target row for the current analysis.
- Target percentages are given per category as percentage points.

## Computation Rules

- **Category percentages**: `(category_count / total_primary_count) * 100`, rounded to **1 decimal place**.
- **Gap**: `actual_pct - target_pct`, rounded to **1 decimal place**. Negative gap means under-invested.
- **Breach rate**: `overdue_primary_count / total_included_primary_count`, rounded to **3 decimal places**.
- **Readiness score**: `completed_primary_count / total_primary_count` for the release, rounded to **3 decimal places**.
- **Milestone completion**: `completed_primary / primary_total` per milestone, as a percentage rounded to **1 decimal place**.
- All metrics are based on **item counts**, never story points or effort estimates.

## Ordering Conventions

- **Work item ID lists**: Sort lexicographically (ascending) for SLA and release tasks. For portfolio mix tasks, sort by `closed_at` ascending, then by `id` ascending.
- **Team lists**: Sort alphabetically.
- **Category rows**: Always use the fixed order: NewFeature, TechDebt, Reliability, Security.
- **Duplicate clusters**: Sort by `primary_id` ascending; within each cluster, sort `duplicate_ids` lexicographically ascending.
- **Milestone entries**: Sort by `milestone_id` ascending.
- **Gap table items**: Use the fixed category order.

## SLA Aging Rules

- **Overdue**: A primary work item is overdue if its SLA deadline (derived from severity and SLA policy) is before the `as_of` date and the item is not closed (or was closed after the deadline).
- **Aging buckets** (days past SLA deadline): `0-3`, `4-7`, `8-14`, `15-30`, `31+`.
- **Escalation priority**: Sort overdue items by severity descending (S1 highest, then S2, S3, S4), then by days overdue descending (most overdue first).
- **Missing owners**: Primary records with null, empty, or missing `owner` field must be reported separately.
- **Hotspot identification**: Group overdue primary records by `team` and `owner`. The pair with the highest count is the top hotspot. Treat missing owners as `UNASSIGNED`.

## Release Readiness Rules

- **Ship decision options**:
  - `SHIP`: Readiness score acceptable, no unresolved high-impact blockers, no critical dependency gaps.
  - `SHIP_WITH_WATCH`: Minor issues present but release can proceed with monitoring.
  - `NO_SHIP`: Unresolved high-impact blockers or critical dependency chains prevent shipping.
- **Gating work items**: Non-complete primary work items linked to the release that block readiness.
- **High-impact blockers**: Unresolved blockers with high impact/severity. Count by exact cause string.
- **Critical dependency chains**: Ordered paths from a blocked release work item through dependencies to the non-complete dependency. Sort chains lexicographically by the full path representation.
- **Milestone completion**: For each milestone in the release, compute completed primary count, total primary count, and completion percentage.

## Output Format

- Always produce a **single JSON object** matching the provided `answer_template.json` schema.
- **Do not include prose outside the JSON.** No explanations, no markdown fences unless the task explicitly allows it.
- Every required field in the schema must be present. Never omit fields even if empty (use `[]`, `{}`, `0`, or `null` as appropriate).
- Follow the schema's `additionalProperties: false` constraint — do not add extra fields.
- Respect all `const`, `enum`, `pattern`, `minItems`, and `maxItems` constraints exactly.
- When a field has a description specifying an ordering, apply that ordering.

## SQL Query Patterns

When REST endpoints are insufficient, use the SQL query endpoint. Common query patterns:

- Filtering work items by multiple criteria (team, status, quarter, category) in a single query.
- Joining work items with related tables (blockers, dependencies, milestones).
- Aggregations (counts grouped by category, team, severity).
- Identifying duplicates via self-joins or `duplicate_of` field checks.

Always parameterize values. Never interpolate user-supplied strings directly into SQL.

## Workflow Summary

1. Read `environment_access.md` for the API base URL, endpoint list, and auth tokens.
2. Inspect the task's `answer_template.json` to understand the required output shape.
3. Fetch reference data (mix targets, SLA policy, milestones, releases) from REST endpoints.
4. Fetch work items via REST or SQL query, applying scope filters (teams, quarter, product area, categories).
5. Separate primary records from duplicates and cancelled items.
6. Classify each primary work item into exactly one portfolio category using authoritative fields.
7. Apply the task's specific rules (closed-only for mix, open-overdue for SLA, release-linked for readiness).
8. Compute metrics using the conventions above (percentages, gaps, rates).
9. Order all lists and tables according to the ordering conventions.
10. Assemble the final JSON object matching every constraint in the answer template.
