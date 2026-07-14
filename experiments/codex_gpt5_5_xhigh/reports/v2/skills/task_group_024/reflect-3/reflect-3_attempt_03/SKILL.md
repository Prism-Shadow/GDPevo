# Engineering Operations Review Skill

Use this skill for engineering-operations tasks that ask for portfolio mix reviews, SLA aging snapshots, or release readiness rollups from a remote workspace API.

## Required Workflow

1. Read the task prompt, request context, and answer template before querying the API.
2. Use the task-provided environment access instructions to replace the base URL placeholder.
3. Query the endpoints named or hinted in the request context. Prefer those hints over guessing endpoints.
4. Build the answer directly from API records and return JSON only, matching the template exactly.
5. Do not use external evaluators, prior answers, or local source files during normal solving.

## Status And Date Rules

- Treat `Closed`, `Done`, and `Verified` as terminal completion statuses.
- Use status history as the source of truth for "as of" calculations: take the last status event at or before the `as_of_date`.
- `status_export`, `closed_date`, and `updated_date` can lag, lead, or disagree with status history. Use them only as fallback when status history is missing, and never count a completion after the `as_of_date`.
- Exclude records created after the `as_of_date`.
- Date windows are inclusive. For a recent closed window of `N` days, include terminal items with `as_of_date - terminal_date <= N`.
- Age is an integer date difference:
  - open item age = `as_of_date - created_date`
  - recently closed item age = `terminal_date - created_date`

## Category Mapping

Use category priority when labels overlap:

1. Security: work type `Security`, `Vulnerability`, `Compliance`, or labels such as `security`, `vulnerability`, `compliance`, evidence/audit security themes.
2. Reliability: work type `Reliability`, `Incident`, `Bug`, or labels such as `reliability`, `slo`, `resiliency`, `capacity`, `incident`, customer escalation signals.
3. TechDebt: work type `Migration`, `Refactor`, `Cleanup`, `Platform`, or labels such as `tech-debt`, `internal`, `platform`, `migration`, `cleanup`, `reliability-review`.
4. NewFeature: work type `Feature`, `Enhancement`, `Experiment`, or labels such as `feature`, `customer`, `growth`, `workflow`.

Security wins over Reliability when both appear. Reliability-review labels do not make a TechDebt item Reliability.

## Portfolio Mix Reviews

- Scope by the product and quarter endpoint in the request context.
- When the task asks for completed work, include scoped items that reached a terminal status by the `as_of_date`, using status history.
- Do not drop `release-scope`, `release-gate`, or duplicate-looking records unless the prompt explicitly excludes them; if the scoped endpoint returns them, they may be part of the review population.
- Compute category counts from the eligible population.
- Percentages are 0-100 values, not fractions. Round actual percentages to the precision implied by the template, usually two decimals for portfolio mix.
- `gap_basis_points = round((actual_percentage - target_percentage) * 100)`.
- Under-invested categories are those with negative gap basis points, in template category order.
- `largest_negative_gap_category` is the category with the most negative gap, or `null` if none.
- Create one `IncreaseAllocation` follow-up per under-invested category. Use the product's owning team ID from the teams endpoint.
- Evidence samples should be stable: first eligible IDs in ascending order for each category, usually up to three unless the template implies otherwise.

## SLA Aging Reviews

- Include Reliability and Security category items for the product, across quarters unless the prompt adds a quarter or release scope.
- The included population is:
  - open as of the `as_of_date`, plus
  - terminal items closed within the inclusive recent closed window.
- Use SLA policy targets by category and severity.
- An item is overdue when `age_days > target_days`.
- Aging buckets are:
  - `0-7`: age <= 7
  - `8-14`: 8 <= age <= 14
  - `15-30`: 15 <= age <= 30
  - `31+`: age >= 31
- Owner hotspots count overdue included items with a non-null owner. Sort by highest overdue count, then highest max age, then owner ID unless the template specifies another order.
- Team hotspots count all overdue included items, including missing-owner work, grouped by `team_id`.
- `missing_owner_work_item_ids` lists included items with no owner, sorted ascending.
- `escaped_severity_count` counts included escaped severe items; use escaped `S1`/`S2` unless the prompt explicitly asks for all escaped items.
- For duplicate clusters, report every cluster represented in the included population. Use the first included work-item ID ascending as a stable representative, and include all included cluster members in `member_ids`, including the representative.

## Release Readiness Rollups

- Use release, milestones, milestone-items, release work-items, status history, dependencies, blockers, owners, and teams as hinted.
- Milestone completion is terminal milestone items divided by total milestone items as of the date. Round to one decimal place when requested.
- Count all milestone item references. If a referenced item lacks status history, fall back to work-item export only when its completion date is at or before the as-of date.
- Gating work items are release-scoped items with active unresolved blockers created at or before the `as_of_date`, unless the prompt defines a different gate.
- Normalize blocker cause keys to the template names, e.g. `Security Review` -> `SecurityReview`, and include zeroes for absent causes.
- `owner_escalation_ids` are the owners of gated items, sorted ascending. Include `UNASSIGNED` if any gated item has no owner.
- Critical dependency chains must remain in dependency order from upstream to downstream. Do not sort the chain after deriving it.
- Use `NoShip` when active release blockers remain on the release date or as-of date. Use `Hold` for pre-release gating risk. Use `Ship` only when no gating blockers remain and readiness targets are met.
- Use `High` risk when active blockers or materially incomplete critical milestones remain; use lower tiers only when the remaining risk is non-gating.

## Output Conventions

- Return only the JSON object. No prose, markdown, comments, citations, or extra keys.
- Preserve template key names and nesting exactly.
- Sort ordinary ID lists ascending unless the template says otherwise.
- Do not sort dependency chains or other ordered process paths after deriving them.
- Use `[]` for empty arrays and `null` only where the template uses null-capable fields.
- Keep percentages and counts numeric, not strings.

## Common Pitfalls

- Do not trust `status_export` when status history disagrees.
- Do not count future closures, future blockers, or future-created items in an as-of report.
- Do not treat `Blocked`, `Review`, `In Progress`, `New`, or `Cancelled` as completed.
- Do not classify a Security item as Reliability just because it has a reliability label.
- Do not remove duplicate customer-signal records from SLA reviews when the prompt asks to audit duplicate clusters.
- Do not omit zero-valued blocker cause keys or empty template arrays.
