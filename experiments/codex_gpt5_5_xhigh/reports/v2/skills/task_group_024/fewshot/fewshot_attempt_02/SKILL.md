---
name: engineering-ops-review-json
description: Use for task_group_024-style engineering operations workspace tasks that require querying a provided API and returning exact JSON reports for portfolio work-mix reviews, reliability/security SLA aging snapshots, or release readiness and gating risk rollups. Apply when prompts reference an engineering operations/work-item environment, request_context endpoint hints, answer_template JSON shapes, products, quarters, releases, as-of dates, SLA windows, blockers, milestones, or portfolio targets.
---

# Engineering Ops Review JSON

## Core Workflow

1. Read the user prompt, `input/payloads/request_context.json`, and `input/payloads/answer_template.json`.
2. Use the base URL supplied by the prompt/context. Replace `<TASK_ENV_BASE_URL>` exactly; URL-encode query parameters such as product names.
3. Follow endpoint hints first. List endpoints normally return an object with `count` and `results`; iterate `results`.
4. Join records by IDs, using status history and the as-of date to reconstruct state at the report date.
5. Fill the answer template exactly. Preserve key names, nested shapes, enum spellings, category order, and object-vs-array choices.
6. Return JSON only. Validate with a JSON parser before final output.

Do not read environment source code, evaluator files, hidden tests, prior answers, or local implementation files. Use only the task payloads and the public API endpoints exposed by the task context.

## API Habits

- Query narrowly with the endpoint hints before exploring wider endpoints.
- Common endpoints are `/api/work-items`, `/api/status-history`, `/api/portfolio-targets`, `/api/sla-policies`, `/api/teams`, `/api/owners`, `/api/releases/{release_id}`, `/api/milestones`, `/api/milestone-items`, `/api/blockers`, and `/api/dependencies`.
- Treat `Done`, `Closed`, and `Verified` as terminal statuses. Treat `Cancelled` as not completed work unless the prompt explicitly asks for cancellations.
- Prefer status history at or before `as_of_date` over `status_export`. `status_export` and `closed_date` can be stale or future-looking. Use `closed_date` as a fallback or cross-check, not as the only source of truth.
- For as-of snapshots, ignore records created after the as-of date unless the prompt explicitly asks for future-planned work.

## Category Classification

Use this classifier for portfolio buckets and SLA policies, then apply any task-specific context or product-specific override visible in the request:

- `Security`: `work_type` in `Vulnerability`, `Security`, `Compliance`, or labels such as `security`, `vulnerability`, `compliance`.
- `Reliability`: `work_type` in `Reliability`, `Incident`, `Bug`, or labels such as `reliability`, `reliability-review`, `slo`, `resiliency`, `capacity`, `incident`.
- `TechDebt`: `work_type` in `Migration`, `Refactor`, `Platform`, `Cleanup`, or labels such as `tech-debt`, `migration`, `cleanup`, `platform`, `internal`.
- `NewFeature`: `work_type` in `Feature`, `Enhancement`, `Experiment`, or labels such as `feature`, `customer`, `growth`, `workflow`, `enhancement`.

Use precedence `Security` before `Reliability` before `TechDebt` before `NewFeature`. A `reliability-review` label moves otherwise technical-debt work into `Reliability`. In Identity Platform portfolio examples, token-rotation work and eligible duplicate customer-signal records are treated as `Security` before the normal reliability/tech-debt rules.

## Portfolio Work-Mix Reviews

Use for prompts asking for a quarterly product portfolio mix, target allocation, under-investment, or follow-up actions.

- Scope work items by the product and quarter from the prompt/context.
- Eligible items are scoped records that reached `Done`, `Closed`, or `Verified` on or before the as-of date. Exclude open, blocked, in-progress, cancelled, and stale-export records without terminal history by as-of.
- Sort `eligible_work_item_ids` ascending. `eligible_total` is its length.
- Count eligible items by category. Keep category rows in the template order.
- `actual_percentage` is `count / eligible_total * 100`, rounded to one decimal.
- `target_percentage` comes from `/api/portfolio-targets`.
- `gap_basis_points` is `(actual_percentage - target_percentage) * 100`, using the rounded one-decimal actual percentage, then rendered as an integer.
- `under_invested_categories` includes categories with a negative gap of at least 500 basis points. Smaller negative gaps still participate in `largest_negative_gap_category`.
- `largest_negative_gap_category` is the category with the most negative gap; use `null` only when there is no eligible/target comparison.
- `follow_up_actions` contains one `IncreaseAllocation` object per under-invested category. Use the owning team ID for the product from `/api/teams`. If none qualify, return an empty array, not the placeholder object.
- `evidence_sample_ids` contains the first three sorted eligible IDs in each category.

## SLA Aging Snapshots

Use for reliability/security aging, overdue, duplicate cluster, owner hotspot, or missing-owner reports.

- Scope work items by product and include only records classified as `Reliability` or `Security`.
- Include records created on or before the as-of date that are either still open as of the as-of date or reached a terminal status within the recent closed window. The inclusive window rule is `as_of_date - terminal_date <= recent_closed_window_days`.
- Treat records with a terminal date after the as-of date as open at the as-of date.
- Define `lifecycle_end` as the terminal date when terminal by as-of, otherwise the as-of date.
- `age_days` is whole calendar days from `created_date` to `lifecycle_end`.
- Get SLA targets from `/api/sla-policies` by classified category and severity. Do not rely on the work item `due_date`; it can reflect a raw work type instead of category overrides.
- A record is overdue when `age_days > target_days`, not when equal.
- Aging bucket counts cover all included records, not just overdue records. Use `0-7`, `8-14`, `15-30`, `31+` with the template's object or array shape.
- Owner hotspots group overdue records by non-null `owner_id`. Include owners with `overdue_count >= 2` or `max_age_days >= 60`. Sort by overdue count descending, max age descending, then ID ascending.
- Team hotspots group overdue records by `team_id`; include teams with overdue work and sort the same way.
- Duplicate cluster sections include every duplicate cluster represented in the included population. Use sorted included member IDs; the representative is the first sorted included member.
- `escaped_severity_count` counts included escaped records with high severity (`S1` or `S2`).
- `missing_owner_work_item_ids` contains overdue included records with `owner_id` null, sorted ascending. Do not include non-overdue null-owner records.

## Release Readiness Rollups

Use for release readiness, go/no-go, risk tier, milestone completion, gating work, blockers, dependencies, or owner escalation.

- Query the release object, milestones, milestone-items, release work items, product status history, active blockers, dependencies, owners, and teams.
- Use the release product and as-of date as the primary scope. Watch for cross-product records linked to a release; exclude clearly unrelated records from gating/escalation and reconcile milestone denominators against the release scope and template.
- Milestone completion is completed items divided by total milestone items, rounded to one decimal. Count an item complete if it reached `Done`, `Closed`, or `Verified` by the as-of date; use `closed_date <= as_of_date` as a fallback when status history is absent.
- Sort milestone objects by `milestone_id`.
- `gating_work_item_ids` are release-scoped items with active unresolved blockers as of the as-of date and no terminal status by as-of. Sort ascending.
- Initialize every blocker cause key shown in the template to `0`. Count active blockers for gating items only. Normalize blocker types by removing spaces, e.g. `Security Review` -> `SecurityReview`.
- `critical_dependency_chain` is an unresolved dependency path involving a gating item, ordered upstream to downstream. Preserve dependency order; do not sort this list.
- `owner_escalation_ids` is the sorted unique owner IDs of gating items. Use `UNASSIGNED` only for a gated item with no owner.
- Use `NoShip` when gating blockers remain. Use `Hold` when no active gating blocker remains but readiness target, critical milestones, or critical dependencies are not acceptable. Use `Ship` only when gates are clear and readiness meets the release target.
- Use `High` risk when there are active gating blockers or materially incomplete critical milestones; `Medium` for readiness gaps without hard gates; `Low` when release health is clear.

## Output Conventions

- Match the template exactly: no extra keys, no missing keys, no markdown, no comments.
- Remove placeholder example objects when a result list is empty.
- Preserve enum spellings from the template, such as `IncreaseAllocation`, `Ship`, `Hold`, `NoShip`, `Low`, `Medium`, `High`.
- Sort IDs ascending unless the template says not to sort, such as dependency chains.
- Keep category rows and aging buckets in template order.
- Use JSON `null` only where the template uses or implies null; otherwise use empty arrays/objects as shaped.
- Cross-check totals: list lengths must match count fields, bucket counts should sum to their intended population, category counts should sum to eligible totals, and percentages should correspond to the rounded rules.

## Common Pitfalls

- Do not trust `status_export` alone; status history often explains stale or future exports.
- Do not treat duplicate clusters as deduplicated work. Count all included member records unless the template specifically asks only for representatives.
- Do not use `due_date` for SLA overdue calculations when SLA policies are available.
- Do not include feature/new-feature records in SLA aging unless the prompt explicitly widens scope beyond reliability/security.
- Do not include placeholder rows from `answer_template.json`.
- Do not include prose, citations, or code fences in the final task answer.
