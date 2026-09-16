---
name: engineering-portfolio-json-solver
description: Solve JSON-only engineering portfolio environment tasks that require querying shared work-item, portfolio mix target, SLA, release, milestone, blocker, dependency, or restricted SQL endpoints; use for tasks asking Codex to compute portfolio mix, SLA aging/breach metrics, duplicate clusters, release readiness, ship decisions, gating work, blockers, dependency chains, or schema-constrained answers from a TASK_ENV_BASE_URL and environment_access.md.
---

# Engineering Portfolio JSON Solver

Use this workflow for shared engineering portfolio tasks that require a JSON answer built from runtime environment data.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before querying data.
2. Extract the exact scope: dates, quarter, release, teams, product areas, categories, recent-closed window, target `scope_id`, and required output ordering.
3. Read `environment_access.md` only for runtime access details: base URL substitution, endpoint list, query token, and authentication/query syntax. Do not copy access secrets into the final answer.
4. Query authoritative environment endpoints first. Use restricted SQL only to inspect or cross-check staged environment data, not to bypass prompt logic.
5. Build the answer from current authoritative records. Treat mirror, export, cached, legacy, or denormalized fields as stale when they conflict with source-specific records.
6. Validate the final object against the template shape, required keys, enum values, ordering rules, and rounding precision. Return only JSON, with no prose.

## Data Handling Rules

- Keep a traceable intermediate table of candidate work items with id, team, product area, status, category signals, owner, severity, dates, duplicate/canonical fields, release or milestone links, blockers, dependencies, and exclusion reason.
- Apply every scope filter explicitly. A related-looking record is not in scope unless it satisfies all scoped dimensions.
- Count primary work items, not story points, unless the prompt explicitly says otherwise.
- Exclude duplicates from primary counts. Detect duplicates from explicit duplicate/canonical/primary references, duplicate status/type fields, or records that point at another work item as their primary. Report duplicate clusters when the template asks for them.
- Exclude cancelled work from closed portfolio mixes and primary SLA/release denominators unless the template explicitly asks to report cancelled exclusions.
- Preserve requested ordering exactly. Common orderings are lexicographic id order, closed-at ascending then id ascending, milestone id ascending, category order `NewFeature`, `TechDebt`, `Reliability`, `Security`, and duplicate clusters by `primary_id`.
- Use empty arrays or empty objects when no qualifying records exist, if the schema permits them.

## Category Resolution

Resolve each included item to exactly one portfolio category.

1. Prefer the authoritative current category field or category endpoint when present.
2. If authoritative category is absent, resolve from current type, labels, component, and title/body signals.
3. Use consistent conventions: security/vulnerability/CVE/application-security signals map to `Security`; incident/SLA/availability/resilience/reliability signals map to `Reliability`; cleanup/refactor/platform upkeep/dependency upgrade signals map to `TechDebt`; product/customer capability signals map to `NewFeature`.
4. Ignore stale mirror or legacy category fields when they conflict with current work item fields.
5. If conflicting current signals remain unresolved, surface the conflict only through the template's allowed data-quality/action fields.

## Portfolio Mix Tasks

For closed-work portfolio mix reviews:

- Select primary, non-cancelled, non-duplicate work items in the scoped quarter, teams, and product areas. Use `closed_at` or the authoritative closure date, not mirror status.
- Include only records that represent closed portfolio work. Exclude same-scope distractors such as duplicates, cancelled records, non-closed work, out-of-quarter closures, non-primary records, or wrong product/team records.
- Sort included ids by `closed_at` ascending, then id ascending, unless the template says otherwise.
- Compute `category_counts` from item counts.
- Compute actual percentage as `round(count * 100 / total_included, 1)`, with zero percentages when the denominator is zero.
- Read the target mix row matching the requested target scope id. Keep target percentages as percentage points rounded to one decimal place.
- Compute `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
- Under-invested categories are categories with negative gap, ordered from most negative to least negative.
- Recommended rebalance categories come from the largest negative gap first, then the next negative gap when the schema asks for a secondary category. Use maintain-current-mix only when there are no negative gaps. Use a data-quality action only when unresolved conflicts prevent a reliable mix.

## SLA Aging Tasks

For SLA aging or breach audits:

- Primary SLA population is scoped by team and SLA-relevant categories. Include open primary work and primary work closed within the prompt's recent-closed window, unless the prompt narrows this further.
- Exclude duplicates from the primary population but report their clusters when requested.
- Use SLA policy data for thresholds. Match policies by category, severity, work type, or any policy keys the environment exposes.
- Prefer explicit SLA fields such as start, due, breached, paused, closed, or resolved timestamps. When explicit due/breach fields are absent, compute age from the authoritative SLA start date or creation date to the as-of date for open work, and to the closed/resolved date for recently closed work.
- Mark overdue primary work by comparing the applicable due date or threshold to the as-of/closed evaluation date. Recently closed work can still be a breach if it closed after its SLA deadline.
- Bucket age using the exact inclusive ranges named by the template, such as `0-3`, `4-7`, `8-14`, `15-30`, and `31+`.
- Missing owners are included primary ids whose current owner/assignee is null, empty, or absent.
- Team and owner hotspots count overdue primary records. Represent missing owners as `UNASSIGNED` when the template asks for an owner label. Break ties deterministically by team name, owner label, then id evidence.
- Breach rate is `round(overdue_primary_count / included_primary_count, 3)`, or `0.000` logically when the denominator is zero.
- Escalation queues should follow the environment's explicit priority if available. Otherwise sort overdue primary work by severity priority, earliest due date or largest overdue age, then id.

## Release Readiness Tasks

For release-readiness assessments:

- Use release and milestone endpoints as release truth. Do not trust stale work item mirror fields for release membership or milestone state when release-specific records exist.
- Build milestone denominators from primary release work assigned to each milestone. Exclude duplicates and cancelled records unless release data explicitly marks them as primary release scope.
- A completed primary item is one whose authoritative current status is complete/done/closed according to the environment's status conventions.
- Compute `completion_pct = round(complete_primary * 100 / primary_total, 1)` for each milestone.
- Readiness score is `round(total_complete_primary / total_primary_denominator, 3)`.
- Gating ids are unique non-complete primary release work items that gate readiness under the release data, blocker data, dependency data, or prompt definition. Sort as requested.
- Count unresolved high-impact blockers only, keyed by exact cause text.
- Build critical dependency chains as ordered id paths from blocked release work to the non-complete dependency. Sort chains lexicographically by the full path. Avoid cycles by tracking visited ids.
- Prefer an explicit environment ship policy when present. If no policy is exposed, use `NO_SHIP` for unresolved high-impact blockers or hard gating work, `SHIP_WITH_WATCH` for residual non-critical watch items, and `SHIP` only when primary work, blockers, and critical dependencies satisfy the release criteria.

## Final JSON Checklist

- The object has no keys outside the template and no missing required keys.
- Literal scope values match the prompt/template exactly.
- Id lists contain unique ids and follow the requested sort.
- Duplicate clusters list canonical primary ids and sorted duplicate ids; duplicate records are not counted as primary.
- Percentages, gaps, breach rates, and readiness scores are rounded only at final output precision.
- Category rows and severity keys appear in the order required by the template.
- Cause strings and enum values are exact.
- The final response is parseable JSON only.
