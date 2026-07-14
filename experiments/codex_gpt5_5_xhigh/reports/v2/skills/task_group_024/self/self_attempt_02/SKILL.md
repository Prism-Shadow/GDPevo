# Engineering Operations Workspace Skill

Use this skill for engineering-operations tasks that ask for portfolio mix reviews, SLA aging snapshots, or release-readiness rollups from a remote workspace API. The final response for these tasks is usually strict JSON.

## Inputs and API Access

- Read the task prompt, `input/payloads/request_context.json`, and `input/payloads/answer_template.json` when present. The template is the output contract.
- Read `environment_access.md` for the base URL and substitute it for `<TASK_ENV_BASE_URL>`.
- Use only the public API endpoints indicated by the prompt/context unless the task clearly requires another public endpoint exposed by the same environment.
- URL-encode product names and query values with spaces.
- API list endpoints commonly return an object shaped like `{ "count": n, "results": [...] }`; use `results`, not the wrapper, for records.

## Output Contract

- Return JSON only. Do not include markdown, citations, commentary, or extra keys.
- Match the answer template exactly: same keys, nesting, array/object shapes, scalar types, and null-vs-empty-array conventions.
- Keep counts as integers. Compute percentages and ratios from counts, then round only at the final step to the precision implied by the template.
- Use deterministic ordering:
  - Category order: `NewFeature`, `Reliability`, `Security`, `TechDebt` unless the template gives another order.
  - Severity order: `S1`, `S2`, `S3`, `S4`.
  - Work item ID arrays and cluster member arrays: lexicographic by ID.
  - Milestones: target date, then milestone id.
- If a lookup is missing, preserve the source id and use the template's missing-value convention (`null`, `"Unassigned"`, or omitted only if the key is not in the template).

## Status and Date Rules

- Treat `status-history` as authoritative when it is available. `status_export`, `closed_date`, and `updated_date` can be stale, incomplete, or ahead of the requested as-of date.
- Reconstruct an item's as-of status by taking the latest status-history row whose timestamp date is on or before the task's as-of date.
- Terminal/completed statuses are `Closed`, `Done`, and `Verified`. `Cancelled` is not completed unless the template explicitly asks for cancelled work.
- The completed date is the date of the terminal status transition as of the requested date. Use `closed_date` only as a fallback when status history is unavailable for an otherwise in-scope item.
- Ignore status-history transitions, closed dates, and created items after the as-of date.
- Calendar age in days is `end_date - created_date`. A work item breaches an SLA when `age_days > target_days`; an item exactly on its target day is not overdue.
- For an inclusive recent-closed window of `N` days ending on `as_of_date`, the start date is `as_of_date - (N - 1)` days. Include terminal transitions on both boundary dates.

## Work Category Normalization

Normalize `work_type` before portfolio and SLA calculations:

| Normalized category | Work types |
| --- | --- |
| `NewFeature` | `Feature`, `Enhancement`, `Experiment` |
| `Reliability` | `Reliability`, `Incident`, `Bug` |
| `Security` | `Security`, `Vulnerability`, `Compliance` |
| `TechDebt` | `Refactor`, `Cleanup`, `Migration`, `Platform` |

Prefer this mapping over free-text labels. Labels are useful for explanations and risk notes, but category rollups should come from normalized `work_type` unless the task explicitly defines another rule.

## Portfolio Mix Reviews

- Scope work items by the exact product and quarter from the context.
- Join teams by `team_id` when the template asks for team name, director, or product line.
- For completed-work mix, count only scoped items whose as-of status is terminal and whose terminal date is within the requested quarter/review period and on or before the as-of date.
- Compute each category's actual percentage as `category_completed_count / total_completed_count * 100`.
- Compare actual percentage with `/api/portfolio-targets` by normalized category. Variance is normally `actual_percentage - target_percentage`; negative values are under target.
- If the template asks for follow-up allocation, identify the largest under-target categories first. If it asks for backlog-balanced follow-up, also count scoped non-terminal backlog as of the date by normalized category and use it to judge whether existing backlog can offset completed-work underinvestment.
- Do not count non-terminal items in completed mix. Do not include a product or quarter merely because it appears in a related release unless the context expands the scope.

## SLA Aging Snapshots

- Scope to the exact product and as-of date.
- Include only normalized `Reliability` and `Security` items unless the template explicitly includes other categories.
- Use `/api/sla-policies` by normalized category and severity to get `target_days`.
- Open aging population: scoped items created on or before the as-of date whose as-of status is not terminal.
- Recent closed population: scoped items whose as-of status became terminal within the inclusive recent-closed window.
- For open items, use `as_of_date` as the aging end date. For recently closed items, use the terminal transition date.
- Compute `age_days`, `target_days`, `over_sla_days = max(0, age_days - target_days)`, and breach status from those values.
- Join `/api/owners` and `/api/teams` for owner display names, roles, team names, and directors. Track null `owner_id` as an ownership gap if the template has such a field.
- Preserve customer-risk flags such as `customer_impact` and `escaped` when the template asks for risk summaries.
- Duplicate clusters:
  - Do not deduplicate the review population unless the template explicitly asks for deduped counts.
  - For duplicate-cluster reporting, group included items with non-null `duplicate_cluster`.
  - Choose a stable representative deterministically, normally the lexicographically smallest included work item id unless the template defines a different representative rule.
  - Report only members that are actually in the included review population.

## Release Readiness Rollups

- Fetch the release record first. Use its `product`, `release_id`, `release_date`, and `readiness_target`.
- Fetch release work items, milestones, milestone-items, status history, dependencies, blockers, owners, and teams from the hinted endpoints.
- For the core readiness population, filter release work items to the release record's product unless the task explicitly asks for cross-product release dependencies. Product-mismatched items with the release id are often distractors for the main readiness score.
- Reconstruct every scoped item status as of the requested date from status history.
- Readiness score is usually `terminal_scoped_items / total_scoped_items`; compare it with `readiness_target` using the template's expected scale (ratio or percentage).
- A milestone is complete only when all scoped milestone items are terminal as of the date. A critical milestone with open items after its target date is a gating risk.
- Active blockers count only when `active=true` and `work_item_id` is in the scoped release population. Include blocker type, severity, cause text, and item id when requested.
- Critical dependencies are gate risks when a scoped item depends on, requires, is blocked by, or validates against an upstream/downstream item that is not terminal as of the date. Treat `duplicates_signal` dependencies as duplicate-signal context, not a blocking release dependency, unless the task asks for duplicate-signal analysis.
- Prioritize open `S1`/`S2`, blocked, security, reliability, unowned, and customer-impacting items in risk summaries when the template asks for top risks.

## Common Pitfalls

- Do not use train answers, evaluator feedback, hidden judges, local environment source, or unstaged artifacts. Solve from the task input files and the public remote API.
- Do not trust `status_export` alone; it can disagree with status history.
- Do not use future transitions after the as-of date, even if `closed_date` or `updated_date` suggests a later outcome.
- Do not include cross-product records in product-scoped reviews unless the task explicitly broadens the scope.
- Do not collapse duplicate clusters for counts unless instructed; original work item records remain auditable.
- Do not invent fields or explanatory prose outside the answer template.

## Final Validation Checklist

Before returning the JSON:

- The output parses as JSON.
- The key set and value types match the template exactly.
- All dates were evaluated relative to the requested as-of date.
- Status was reconstructed from status history where available.
- Counts reconcile with the item arrays and category totals.
- Percentages/ratios use the template's scale and rounding.
- IDs, owners, teams, milestones, blockers, and duplicate clusters are sorted deterministically.
