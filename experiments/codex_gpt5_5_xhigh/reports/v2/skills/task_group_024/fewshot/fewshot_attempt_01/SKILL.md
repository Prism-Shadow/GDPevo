---
name: engineering-ops-review
description: Complete engineering operations workspace review tasks that require querying a remote REST API and returning strict JSON for portfolio work-mix, reliability/security SLA aging, or release readiness rollups. Use when prompts mention engineering operations/work-item workspace APIs, product or release scoped reviews, portfolio targets, SLA aging, blockers, milestones, dependencies, owners, teams, or an answer_template.json contract.
---

# Engineering Ops Review

## Operating Rules

Use the task's `environment_access.md` to get the remote base URL and replace `<TASK_ENV_BASE_URL>` with it. Do not inspect local environment source, evaluator files, hidden tests, previous runs, or training answers while solving a test task.

Read the prompt, `input/payloads/request_context.json`, and `input/payloads/answer_template.json` first. The template is the output contract: return JSON only, with exactly those keys, value shapes, and field-name variants. Do not add normalizing fields such as `included_count` if the template does not include them.

Use the endpoint hints from `request_context.json`. Most list endpoints return:

```json
{"count": 0, "results": []}
```

Single release endpoints return one object. URL-encode product names in query strings.

Useful endpoints by task type:

- Portfolio: `/api/work-items?product=...&quarter=...`, `/api/status-history?product=...`, `/api/portfolio-targets?product=...&quarter=...`, `/api/teams`
- SLA aging: `/api/work-items?product=...`, `/api/status-history?product=...`, `/api/sla-policies`, `/api/owners`, `/api/teams`
- Release readiness: `/api/releases/{release_id}`, `/api/milestones?release_id=...`, `/api/milestone-items?release_id=...`, `/api/work-items?release_id=...`, `/api/status-history?product=...`, `/api/dependencies`, `/api/blockers?active=true`, `/api/owners`, `/api/teams`

The public `/web/policies` page may be used for business policy notes and SLA target confirmation. Do not use any train-only judge or answer oracle during test solving.

## Data Reconciliation

Do not trust one snapshot field blindly. Work-item exports can be stale:

- `status_export` can disagree with `closed_date` or status history.
- `closed_date` can be future relative to the requested as-of date.
- A work item can have `closed_date` populated but a status-history event of `Cancelled`; exclude cancelled work unless explicitly requested.

For as-of logic, build an as-of state per item:

1. Use status-history events with `timestamp` on or before the as-of date.
2. Take the latest such event as status-as-of.
3. Treat terminal delivery statuses as `Closed`, `Done`, or `Verified`.
4. Treat `Cancelled` as excluded from completed/review populations.
5. Treat future close dates after the as-of date as not yet closed.

For day counts, use calendar date difference: `end_date - created_date`. Do not add one day. For open work, `end_date` is the as-of date. For work closed on or before the as-of date, `end_date` is the close date.

Sort IDs lexicographically ascending unless the template says otherwise. Preserve template order for category rows and aging buckets.

## Work Category Classification

The API does not provide a reliable direct portfolio category. Classify each item from all available metadata: `work_type`, `labels`, `title`, `description`, `target_area`, duplicate-cluster signal, and broader product context.

Use these cues, with the most specific business intent winning:

- `Security`: `security`, `vulnerability`, `compliance`, access control, exposed credential, token rotation, audit evidence, compliance evidence, threat model, privilege boundary, or security-review wording. Security intent can override generic feature or tech-debt fields.
- `Reliability`: `reliability`, `reliability-review`, `incident`, `bug`, `slo`, `resiliency`, `capacity`, failover, retry storm, SLO breach, timeout spike, customer escalation, or operational hardening wording. Reliability-review can override generic tech-debt fields.
- `TechDebt`: `tech-debt`, `cleanup`, `migration`, `platform`, `internal`, refactor, modernize, retire legacy, service boundary, platform dependency, or job-flow cleanup, unless security or reliability intent is clearer.
- `NewFeature`: `feature`, `enhancement`, `experiment`, `customer`, `growth`, workflow, onboarding path, analytics panel, customer setting, add/expand/launch/improve product-delivery wording, unless a security/reliability/tech-debt cue is stronger.

Do not drop duplicate-cluster work items. Classify them by their signal text and work type, and keep them auditable in the requested population.

## Portfolio Work-Mix Reviews

Scope work items by product and quarter. Eligible work items are scoped items completed by the as-of date and not cancelled as of that date. `status_export` does not need to look terminal if `closed_date` or status history establishes completion.

Compute:

- `eligible_work_item_ids`: all eligible IDs sorted ascending.
- `eligible_total`: length of eligible IDs.
- Category rows in the template's category order, normally `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- `count`: eligible items in that category.
- `actual_percentage`: `count / eligible_total * 100`, rounded to one decimal. Use `0.0` if total is zero.
- `target_percentage`: from `/api/portfolio-targets`, rendered as a number with one decimal when examples use decimals.
- `gap_basis_points`: integer basis points from the rounded actual percentage minus target percentage, multiplied by 100.

Under-investment uses a materiality threshold: include categories at least 500 basis points below target. Smaller negative gaps can still determine `largest_negative_gap_category`, but do not create follow-up actions.

Set:

- `under_invested_categories`: materially under-invested categories in template/category order.
- `largest_negative_gap_category`: the category with the most negative gap, even if it is not materially under-invested; use `null` if no category is below target.
- `follow_up_actions`: one action per materially under-invested category, in category order, with `action: "IncreaseAllocation"` and `owner_team_id` from `/api/teams` where `product_line` matches the product.
- `evidence_sample_ids`: first three eligible IDs per category, sorted ascending.

## Reliability and Security SLA Aging

Scope to the requested product and include reliability/security-oriented items only. Use the category classifier above; reliability-review tech-debt items can be in scope.

The review population includes non-cancelled scoped items created on or before the as-of date that are either:

- still open as of the as-of date, or
- closed in the recent closed window.

The recent closed window is inclusive and starts at `as_of_date - recent_closed_window_days`. For a 21-day window ending 2026-02-15, the start date is 2026-01-25.

Do not deduplicate duplicate clusters; original work item records remain included. Report duplicate-cluster summaries separately when the template asks.

Use `/api/sla-policies` by category and severity, or the work item's `due_date` when present. A work item is overdue when the applicable end date is after its SLA due date/target:

- Open as of date: compare as-of date to due date.
- Closed within window: compare close date to due date.
- Future close date after as-of: treat as open at as-of.

Compute:

- `included_work_item_ids`: all included IDs sorted ascending.
- `included_count`: only if the template includes it.
- `overdue_work_item_ids`: overdue included IDs sorted ascending.
- `overdue_count`: only if the template includes it.
- Aging buckets for all included items, not just overdue items: `0-7`, `8-14`, `15-30`, `31+`.
- `owner_hotspots`: group overdue items with non-null owners by owner. Include groups with overdue count greater than zero. Sort by `overdue_count` descending, then `max_age_days` descending, then owner ID ascending.
- `team_hotspots`: group overdue items by team with the same sort rule.
- `missing_owner_work_item_ids`: included items with `owner_id: null`, sorted ascending.
- `escaped_severity_count`: count included items where `escaped` is true.

For duplicate clusters, group included items with non-null `duplicate_cluster`. Sort clusters by cluster ID. Use the lowest included member ID as `representative_work_item_id`; `member_ids` are included member IDs sorted ascending. Use the exact template field name, such as `duplicate_clusters` or `duplicate_cluster_representatives`.

## Release Readiness Rollups

Scope by release ID and as-of date. Fetch the release record, milestones, milestone-item links, release work items, product status history, active blockers, dependencies, owners, and teams.

Milestones:

- For each milestone, use linked milestone items as the denominator.
- Count an item complete if it is completed by the as-of date using reconciled status/close-date logic.
- Exclude cancelled items from completed counts.
- `completion_percentage` is rounded to one decimal.
- Sort milestone objects by `milestone_id` ascending.

Gating risk:

- Filter active blockers to those whose `work_item_id` is in the release work-item set and whose `created_date` is on or before the as-of date.
- Ignore active blockers created after the as-of date.
- `gating_work_item_ids` are the blocked release work item IDs sorted ascending.
- Initialize every blocker cause key shown in the template to zero, then count the filtered active blockers.
- Normalize blocker types to enum keys by removing spaces, for example `External Dependency` -> `ExternalDependency`, `Security Review` -> `SecurityReview`, `Design Decision` -> `DesignDecision`, `Data Migration` -> `DataMigration`.

Dependencies:

- Use `/api/dependencies` to trace gating or critical-path chains among release work items.
- Preserve dependency order from upstream to downstream in `critical_dependency_chain`; do not sort that list.
- Prefer chains involving a gated item, critical-path/release-gate labels, critical dependencies, or downstream blocked work. Include each work item ID once in path order.

Escalations and decisions:

- `owner_escalation_ids` are owners of gated work items sorted ascending. Include `UNASSIGNED` only if a gated item has no owner.
- Use `NoShip` and `High` when active as-of gating blockers or unresolved critical dependency chains remain at the release date or when critical milestones are materially incomplete.
- Use `Hold`/`Medium` when readiness is below target but no hard active gate remains.
- Use `Ship`/`Low` only when critical milestones meet readiness expectations and no active gating blockers remain.

## Final Validation

Before returning, parse the JSON locally and compare top-level keys against the template. Check:

- no markdown, comments, citations, or extra keys
- nulls only where the template allows them
- arrays and object-vs-array bucket shapes match the template exactly
- counts equal the lengths of their corresponding ID lists where both are present
- IDs and hotspot rows follow the required sorting rules
- percentages have one decimal where examples/templates require numeric percentages
