---
name: engineering-portfolio-env
description: Solve engineering portfolio environment tasks that ask Codex to inspect work items, mix targets, SLA policy, releases, milestones, blockers, or dependencies through the provided task environment and return exact JSON for portfolio mix, SLA aging, or release readiness analyses.
---

# Engineering Portfolio Environment

Use this skill when the prompt points at the shared engineering portfolio environment and asks for JSON based on work items, mix targets, SLA policy, releases, milestones, blockers, or dependencies.

## Workflow

1. Read the task prompt and the supplied answer template/schema first. The template controls field names, constants, ordering, and precision.
2. Read the runtime access file for `base_url`, allowed endpoints, and any query token. Prefer the GET endpoints; use `POST /api/query` only when a token is actually supplied.
3. Load authoritative records from the environment:
   - `GET /api/work-items` -> `work_items`
   - `GET /api/work-items/{item_id}` -> `work_item`
   - `GET /api/mix-targets` -> `mix_targets`
   - `GET /api/sla-policy` -> `sla_policy`
   - `GET /api/releases` and `GET /api/releases/{release_id}` -> release metadata, and sometimes related milestones/blockers
   - `GET /api/milestones`, `GET /api/blockers`, `GET /api/dependencies`
4. Use the helper script for draft calculations when useful:

```bash
python skill/scripts/portfolio_env.py portfolio --base-url "$BASE_URL" --quarter YYYY-Qn --team "Team A" --team "Team B" --product-area "Area A" --target-scope-id "$SCOPE_ID"
python skill/scripts/portfolio_env.py sla --base-url "$BASE_URL" --team "Team A" --team "Team B" --category Security --category Reliability --as-of YYYY-MM-DD --recent-closed-window-days N
python skill/scripts/portfolio_env.py release --base-url "$BASE_URL" --release-id "$RELEASE_ID"
```

Use the script output as a draft. Always reshape it to match the answer template exactly and re-check any task-specific ordering instructions.

## Authoritative Fields

Use `status`, `closed_at`, `created_at`, `due_at`, `duplicate_of`, `work_type`, `labels`, `title`, `team`, `product_area`, `release_id`, `milestone_id`, `severity`, `owner`, and `priority` as the source of truth.

Ignore stale or mirror/export fields for decisions and classification, especially `mirror_status` and `legacy_category`.

Treat a work item as primary only when `duplicate_of` is empty and `status` is not `Duplicate` or `Cancelled`. Treat completed work as `Closed`, `Done`, `Verified`, `Deployed`, or `Complete`.

## Portfolio Category Resolution

Classify each primary item into exactly one category using authoritative `work_type`, `labels`, and `title` signals. Apply this precedence:

1. `Security`: `work_type` Security or Compliance, or signals such as security, cve, auth, encryption, compliance.
2. `Reliability`: `work_type` Reliability or Incident, or signals such as reliability, incident, outage, latency, flaky.
3. `TechDebt`: `work_type` Refactor, Chore, or Dependency, or signals such as cleanup, refactor, migration, dependency, tech-debt, debt, maintenance, chore.
4. `NewFeature`: `work_type` Feature or Enhancement, or signals such as feature, rollout, enhancement, customer-request, new.

If no signal matches, default to `TechDebt`. Do not let `legacy_category` override this order.

## Portfolio Mix Tasks

For closed-work mix tasks:

1. Parse the quarter into an inclusive closed-date range.
2. Filter work items by prompt teams, product area(s), and `closed_at` within the quarter.
3. Include only primary completed work. Order included IDs by `closed_at` ascending, then ID ascending unless the template says otherwise.
4. Report duplicate exclusions from records with nonempty `duplicate_of` or `status: Duplicate`; report cancelled exclusions from `status: Cancelled`. For generic distractor lists, combine duplicate and cancelled records in closed-date then ID order.
5. Count categories by item count, not story points.
6. Select the mix target by the prompt `scope_id` when provided. Target values are fractions; multiply by 100 for percentage points.
7. Round actual percentages, target percentages, and gaps to one decimal place. Compute `gap_pct = actual_pct - target_pct`.
8. Sort under-invested categories by most negative gap to least negative gap. The primary rebalance category is the largest deficit. If a secondary category is requested, use the next negative gap; otherwise use null.
9. If a template asks for a recommended owner team, choose the in-scope team with the most included work in the largest deficit category; break ties by the prompt's team order.

## SLA Aging Tasks

For SLA audit tasks:

1. Filter by prompt teams and requested categories using the category resolution above.
2. Use primary work only for the SLA population. Include items created on or before the as-of date that are open as of that date, plus items closed within the recent closed window ending on the as-of date.
3. Report duplicate clusters separately when duplicate records are in the same SLA scope/window and point at a primary ID. Sort clusters by `primary_id`; sort duplicate IDs lexicographically.
4. Use `due_at` as the due date when present. If it is missing, derive it from `created_at` plus the matching `sla_policy.days_to_due` for the item's severity.
5. An open item is overdue when `due_at` is before the as-of date. A completed item in the recent closed window is overdue when `closed_at` is after `due_at`. A due date equal to the as-of date is not overdue.
6. For aging buckets, use calendar days from `created_at` to `closed_at` for completed items, otherwise from `created_at` to the as-of date. Buckets are `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
7. Sort primary and overdue ID lists lexicographically unless the template says otherwise. Sort team rows alphabetically when requested.
8. Use `UNASSIGNED` for missing owners in owner/team hotspot calculations. For escalation queues, order overdue primary work by severity `S1`, `S2`, `S3`, `S4`, then due date ascending, then numeric priority ascending, then ID.
9. Round breach rates to three decimal places as overdue primary count divided by included primary count.

## Release Readiness Tasks

For release readiness:

1. Filter primary release work by `release_id`; use `milestone_id` to group by milestone. Exclude duplicates and cancelled items from denominators.
2. Compute each milestone's `complete_primary`, `primary_total`, and one-decimal `completion_pct`. Sort milestone rows by `milestone_id` ascending.
3. Compute `readiness_score` as total completed primary work divided by total primary release work, rounded to three decimals.
4. Count unresolved high-impact blockers by exact `cause` text. High-impact blocker severities are `High` and `Critical`; unresolved means `resolved_at` is null and `status` is not `Resolved`.
5. Gating work item IDs are non-complete primary release work items with unresolved high-impact blockers or with critical dependency chains to non-complete primary dependencies. Sort them ascending with no duplicates.
6. Build dependency chains from dependency edges `blocked_id -> depends_on_id`, starting at non-complete primary release work. Follow complete dependencies transitively and emit paths that end at a non-complete primary dependency. Sort chains lexicographically by the full path.
7. Use `NO_SHIP` when unresolved high-impact blockers or critical dependency chains remain. Use `SHIP_WITH_WATCH` when no high-impact blockers/chains remain but readiness is incomplete or lower-impact blockers remain. Use `SHIP` only when release primary work is complete and no unresolved blockers/chains remain.

## Final JSON Discipline

Return exactly one JSON object when requested. Do not include prose. Preserve the template's required constants, object names, field order when practical, array ordering, and rounding precision. Validate `additionalProperties: false` templates by omitting helper-only fields that the schema does not allow.
