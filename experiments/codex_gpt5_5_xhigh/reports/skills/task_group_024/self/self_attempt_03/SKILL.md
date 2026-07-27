---
name: engineering-portfolio-audits
description: Derive strict JSON answers from the shared engineering portfolio environment for portfolio-mix reviews, SLA aging audits, and release-readiness assessments. Use when prompts mention work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, duplicate or cancelled records, stale mirror fields, count-based portfolio categories, breach rates, readiness scores, or ship decisions.
---

# Engineering Portfolio Audits

## Start Here

1. Read the user prompt, `environment_access.md`, and the requested answer template before querying data.
2. Use only the base URL, endpoints, and query token listed in `environment_access.md`. Prefer the REST endpoints; use `POST /api/query` with the supplied token only when endpoint joins are insufficient.
3. Load only the datasets needed for the prompt: work items, mix targets, SLA policy, releases, milestones, blockers, and dependencies.
4. Treat the answer template as binding. Preserve exact keys, enum spellings, required ordering, and numeric precision. Do not add prose when the prompt asks for JSON only.

Endpoint list responses are wrapped in top-level keys such as `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, and `blockers`; unwrap those before filtering.

## Authoritative Fields

Use authoritative work item fields for truth:

- `status`, `closed_at`, `created_at`, `due_at`
- `team`, `product_area`, `release_id`, `milestone_id`
- `duplicate_of`
- `work_type`, `labels`, `title`
- `owner`, `severity`, `priority`

Do not use `mirror_status` as status truth. Do not use `legacy_category` as category truth. Mention or flag ignored stale fields only when the output schema asks for that.

Use these complete statuses unless the prompt provides a different rubric:

```text
Closed, Done, Verified, Deployed
```

Treat these as non-complete for readiness and SLA state checks:

```text
Backlog, In Progress, Review, Reopened
```

Exclude `Cancelled` records from primary counts. Treat a record as duplicate/non-primary when either `status == "Duplicate"` or `duplicate_of` is non-null, even if another field says it is closed. When reporting duplicate clusters, group duplicate records by `duplicate_of`; if a duplicate lacks a target, exclude it from primary counts and report it only if the schema has a suitable orphan/distractor field.

## Portfolio Category Classifier

Classify every primary work item into exactly one portfolio category. Use `work_type` first; use labels and title only for fallback or ambiguous bug records. Ignore `legacy_category`.

Direct `work_type` mapping:

```text
Feature, Enhancement       -> NewFeature
Refactor, Dependency, Chore -> TechDebt
Reliability, Incident      -> Reliability
Security, Compliance       -> Security
```

For `Bug`, inspect labels and title:

- Security signals: `security`, `cve`, `auth`, `encryption`, `compliance`
- Reliability signals: `reliability`, `incident`, `outage`, `latency`, `flaky`
- If both appear, prefer Security only when the security signal is the explicit bug subject; otherwise use Reliability for operational defects.
- If no signal appears, default `Bug` to Reliability.

Fallback signal order for unknown `work_type` values:

```text
Security signals -> Security
Reliability signals -> Reliability
cleanup/migration/refactor/dependency/chore/tech-debt -> TechDebt
feature/enhancement/rollout/customer-request -> NewFeature
otherwise -> TechDebt
```

Use category order whenever the template does not specify another order:

```text
NewFeature, TechDebt, Reliability, Security
```

## Portfolio Mix Reviews

For count-based mix outputs:

1. Find the target row by the prompt's `scope_id` in `mix_targets`. Treat target fields as fractions and convert to percentage points by multiplying by 100.
2. Filter work items to the requested quarter/date range, teams, and product areas.
3. Include only primary records with `closed_at` inside the scope window and an authoritative complete status.
4. Exclude duplicates, duplicate pointers, and cancelled records; report those IDs in the template's exclusion fields when present.
5. Count items by portfolio category. Do not use story points for mix unless the prompt explicitly asks for points.
6. Compute `actual_pct = count / total_included * 100`, rounded to one decimal place. Use `0.0` for every category when the denominator is zero.
7. Compute `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
8. Order included IDs by `closed_at` ascending, then ID ascending, unless the template says otherwise.

Recommendation rules:

- If the target row is missing, multiple target rows conflict, or the denominator is zero, choose an investigation/data-quality action when the schema supports it.
- If any category has a negative gap, recommend rebalancing toward the category with the most negative gap. If a secondary category is requested, choose the largest positive gap as the capacity source; break ties by category order.
- If no category has a negative gap, choose a maintain-current-mix action with null categories when the schema supports it.
- If an `owner_team` is required, choose the in-scope team most associated with the surplus category being rebalanced away from, or the team with the fewest items in the deficit category when the schema is framed that way. Break ties by the prompt/template ordering, then alphabetically.

## SLA Aging Audits

For SLA population outputs:

1. Load work items and SLA policy. Use item `due_at` as the operative due date when present; use the policy to validate or derive due dates only when the prompt requires it or `due_at` is missing.
2. Filter to requested teams and requested portfolio categories, using the category classifier above.
3. Include primary records created on or before the as-of date that are either active as of that date or closed in the recent-closed lookback window.
   - Active as of date: `closed_at` is null or after the as-of date.
   - Recent closed: `as_of - window_days <= closed_at <= as_of`.
4. Exclude cancelled and duplicate records from the primary population. Still collect in-scope duplicates into duplicate clusters when the template requests them.
5. For each primary record, use `effective_end = closed_at` for recently closed records, otherwise `effective_end = as_of`.
6. Mark a record overdue only when `due_at < effective_end`. A due date equal to the as-of date or closure date is not overdue.
7. Compute age in days as `effective_end - created_at` and bucket inclusively:

```text
0-3, 4-7, 8-14, 15-30, 31+
```

8. Compute breach rate as `overdue_primary_count / included_primary_count`, rounded to three decimal places. Use `0.000` if the denominator is zero.

SLA reporting rules:

- Sort ID lists lexicographically unless the template asks for escalation priority.
- List scoped teams alphabetically when team count rows are requested.
- Group duplicate clusters by `primary_id = duplicate_of`, sort clusters by `primary_id`, and sort `duplicate_ids` lexicographically.
- Use `UNASSIGNED` for missing owners in hotspot calculations; missing-owner ID lists contain included primary records whose owner is null or empty.
- Pick the top hotspot by overdue count descending, then team name, then owner name.
- For severity counts, emit all requested severity keys with zeroes when absent.
- For escalation queues, sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`; then by numeric `priority` ascending; then open/active records before recently closed records; then earliest `due_at`; then ID.

## Release Readiness Assessments

For release readiness outputs:

1. Load the release by `release_id`, then load milestones, work items, blockers, and dependencies. Use `release_id` and `milestone_id` as release truth; ignore stale mirror/export fields.
2. Build the primary release denominator from work items whose `release_id` matches the requested release and that are not cancelled, duplicate-status records, or duplicate pointers.
3. Count a primary release work item complete only when its authoritative `status` is one of the complete statuses.
4. For every milestone belonging to the release, compute:
   - `primary_total`: primary release work items assigned to that milestone
   - `complete_primary`: complete primary work items for that milestone
   - `completion_pct`: `complete_primary / primary_total * 100`, rounded to one decimal place, or `0.0` when total is zero
5. Sort milestone rows by milestone ID ascending.
6. Set `gating_work_item_ids` to sorted unique primary release work item IDs whose authoritative status is not complete.
7. Count unresolved high-impact blockers by exact `cause` text. Treat blockers as unresolved when `resolved_at` is null and the status is not resolved/closed. Treat `Critical` and `High` as high impact unless the prompt defines a different set.
8. Build dependency chains from release work to non-complete dependencies by following `blocked_id -> depends_on_id`. Include dependencies outside the release when the chain starts from release work. Avoid cycles; include a chain when the terminal dependency status is not complete. Sort chains lexicographically by the full path.
9. Compute `readiness_score = completed_primary_release_items / primary_release_denominator`, rounded to three decimal places, or `0.000` when the denominator is zero.

Ship decision default:

- `NO_SHIP` if there are non-complete primary release items, unresolved high-impact blockers, or critical dependency chains.
- `SHIP_WITH_WATCH` if primary release work is complete but unresolved low/medium blockers or monitoring dependencies remain.
- `SHIP` only when primary work is complete and there are no unresolved blockers or non-complete dependency chains.

Honor any stricter or more specific decision rubric in the prompt over this default.

## Output Discipline

- Populate exactly the shape requested by the answer template.
- Use numbers for computed counts, percentages, rates, and scores, even if the template's placeholder text is a string.
- Keep JSON arrays stable: IDs sorted lexicographically unless the template states chronological or escalation order; categories in category order; milestones by ID.
- Round only at final output precision. Preserve trailing zeroes where the consumer expects fixed precision.
- Do not include task-local final IDs, counts, percentages, dates, or decisions in this skill.
