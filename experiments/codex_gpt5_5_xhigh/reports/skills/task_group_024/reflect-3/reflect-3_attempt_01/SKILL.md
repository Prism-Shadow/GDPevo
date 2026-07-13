---
name: task-group-024-engineering-ops-reviews
description: Solve engineering-operations review tasks that ask for portfolio work-mix, reliability/security SLA aging, or release-readiness JSON from workspace APIs. Use when prompts provide an engineering operations environment, request_context endpoint hints, and an answer_template for products, quarters, releases, milestones, work items, status history, blockers, dependencies, owners, teams, SLA policies, or portfolio targets.
---

# Engineering Ops Reviews

## Core Workflow

1. Read the prompt, `request_context.json`, and `answer_template.json` first. The template is the output contract; return the same keys, nesting, arrays, and scalar types with no extra fields.
2. Replace the prompt's base-URL placeholder with the provided environment base URL and query only the hinted workspace API endpoints unless the task context clearly requires an adjacent hinted family.
3. Treat `status-history` as the source of truth for as-of status. For each work item, use the latest status event at or before the as-of date. Fall back to `status_export` only when there is no usable history for that item.
4. Completed statuses are `Closed`, `Done`, and `Verified`. `New`, `In Progress`, `Review`, `Blocked`, and `Cancelled` are not completed.
5. Ignore records created after the as-of date. Do not let future closed dates, future status events, or stale `status_export` values affect an as-of review.
6. Sort ID lists ascending unless the template explicitly says not to sort. Preserve explicit template ordering for fixed rows such as category rows, aging buckets, and blocker cause keys.

## Work Category Rules

Classify work from labels and `work_type`, using this precedence when labels conflict:

1. `Security`: label `security`, or work type `Security`, `Vulnerability`, or `Compliance`.
2. `Reliability`: label `reliability`, or work type `Reliability`, `Incident`, or `Bug`.
3. `TechDebt`: label `tech-debt`, `cleanup`, `migration`, `platform`, or `reliability-review`, or work type `Cleanup`, `Migration`, `Refactor`, or `Platform`.
4. `NewFeature`: label `feature`, `enhancement`, `customer`, `growth`, or work type `Feature`, `Enhancement`, or `Experiment`.

Use security over reliability for mixed security/reliability records. Use reliability over tech debt for incident/SLO/capacity work that also has `tech-debt`.

## Portfolio Mix Reviews

- Scope from the requested product, quarter, and as-of date. A related release hint is context, not an eligibility filter, unless the prompt explicitly asks for release-scoped review.
- Eligible work is completed as of the review date and belongs to the requested product-quarter scope. Exclude duplicate/customer-signal audit records from portfolio mix unless the prompt explicitly says to keep duplicates auditable.
- Count eligible items by category in the template's category order, usually `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- Use `/api/portfolio-targets` for target percentages. Actual percentages are percentage points, not fractions. Round using the template's precision; if unspecified, one decimal is usually safest when the template shows `0.0`.
- Compute `gap_basis_points` as `(actual_percentage - target_percentage) * 100`, preferably from the unrounded ratio, then round to an integer.
- `under_invested_categories` are categories with negative gap basis points, in category-row order. `largest_negative_gap_category` is the category with the most negative gap, or `null` if none.
- `follow_up_actions` should contain one `IncreaseAllocation` action per under-invested category, assigned to the owning product team from `/api/teams`.
- Evidence samples should be deterministic: use the first few sorted eligible IDs per category, commonly three, unless the template or prompt specifies a different count.

## SLA Aging Reviews

- Include reliability/security work only. Keep duplicate customer-signal records in the included population when the template asks for duplicate clusters or the context says duplicates remain auditable.
- Include items that are open as of the review date plus items completed within the recent closed window. Use the completion status event date when history exists. Treat a window as inclusive by date difference: `(as_of_date - completion_date).days <= recent_closed_window_days`.
- Age is calendar day difference without adding one:
  - Open item age: `as_of_date - created_date`.
  - Recent closed item age: `completion_date - created_date`.
- Compare age to `/api/sla-policies` by category and severity. An item is overdue only when `age_days > target_days`, not when equal.
- Aging buckets are inclusive ranges: `0-7`, `8-14`, `15-30`, `31+`.
- Owner hotspots and team hotspots summarize overdue included items. Sort by `overdue_count` descending, then `max_age_days` descending, then ID ascending. Keep missing-owner work in `missing_owner_work_item_ids`; do not add an owner hotspot unless the template explicitly requests an `UNASSIGNED` owner row.
- Duplicate cluster reports should include one row per represented cluster in the included population. Use sorted included member IDs only. Use the lowest included work item ID as the stable representative unless task text defines another representative rule.
- `escaped_severity_count` should count included escaped items that are severe customer-impact risk, typically escaped `S1`/`S2` records.

## Release Readiness Reviews

- Query release metadata, milestones, milestone-items, release work-items, status history for the release product, dependencies, active blockers, owners, and teams.
- Milestone completion is completed milestone items divided by all milestone items, evaluated as of the review date and rounded to one decimal place when requested. Sort milestones by `milestone_id`.
- Filter active blockers to the release/milestone work population and blocker `created_date <= as_of_date`. Normalize blocker types to template keys by removing spaces, for example `Security Review` -> `SecurityReview`.
- For critical dependency chains, use critical dependency edges within the release/milestone population. Return the chain in upstream-to-downstream order; do not sort the final chain.
- Gating work items should include unresolved work in critical milestones, unresolved active blocker items, and unresolved items in critical dependency chains. Sort the final `gating_work_item_ids`.
- Owner escalations come from gated work items. Include `UNASSIGNED` only when a gated item has no owner and the template permits it.
- Ship decision and risk tier are business summaries:
  - `Ship`: no unresolved gating items and critical milestone readiness meets the release target.
  - `Hold`: material unresolved risk remains but the release is not clearly below critical readiness.
  - `NoShip`: critical milestones are incomplete or critical blockers/dependency chains remain unresolved at the go/no-go date.
  - Use `High` risk for active critical blockers, unresolved S1/S2 security/reliability work, or missed critical milestones; `Medium` for noncritical blockers or moderate target misses; `Low` only when gating risk is absent.

## Common Pitfalls

- Do not trust `status_export` when status history shows a different as-of state. Exports can be stale, future-looking, or inconsistent with `closed_date`.
- Do not use `closed_date` alone to decide completion when status history exists.
- Do not include future-created work in as-of calculations, even if it appears in a release or milestone endpoint.
- Do not collapse duplicate records unless the task asks for de-duplication. Aging reviews usually keep original duplicate work items auditable and report cluster membership.
- Do not filter portfolio reviews by release IDs just because a related release is mentioned.
- Do not include markdown, explanations, citations, or helper/debug fields in the final JSON.
