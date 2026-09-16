---
name: engineering-portfolio-env-solver
description: Use this skill for strict JSON tasks over a shared engineering portfolio environment. Use it whenever the prompt mentions TASK_ENV_BASE_URL, work items, portfolio mix targets, SLA aging or breach rates, release readiness or ship decisions, blockers, dependencies, duplicate clusters, stale mirror fields, or authoritative environment data.
---

# Engineering Portfolio Environment Solver

Use this skill to answer data-analysis prompts that require a single JSON object built from the shared task environment. The usual domains are portfolio mix, SLA aging, and release readiness.

## First Pass

1. Read the task prompt and `input/payloads/answer_template.json` before querying data.
2. Read `environment_access.md` only for the base URL, endpoint list, credentials, and query-token instructions.
3. Fetch the relevant REST collections. Prefer REST endpoints over SQL unless the access note explicitly supplies a valid `X-Env-Token`.
4. Build a small working table of candidate records with every field used for inclusion, exclusion, classification, sorting, and aggregation.
5. Return only the JSON object requested by the template. Do not include prose.

Optional helper: `scripts/fetch_environment.py` fetches the standard REST collections into JSON files:

```bash
python /path/to/skill/scripts/fetch_environment.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/task-env-data
```

Add `--release-id <id>` when a release-specific endpoint is useful. Add `--token <token>` only when the runtime access note gives one.

## Environment Sources

Common endpoints:

- `GET /api/work-items`
- `GET /api/work-items/{item_id}`
- `GET /api/mix-targets`
- `GET /api/sla-policy`
- `GET /api/releases`
- `GET /api/releases/{release_id}`
- `GET /api/milestones`
- `GET /api/dependencies`
- `GET /api/blockers`
- `POST /api/query` with `X-Env-Token` when a token is supplied

Collection responses are JSON wrappers such as `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, and `blockers`.

Use canonical fields from the environment. In particular:

- Trust `status`, `closed_at`, `duplicate_of`, `release_id`, `milestone_id`, `team`, `product_area`, `work_type`, labels, title, owner, severity, priority, and due dates.
- Treat `mirror_status` and `legacy_category` as stale/export fields unless the prompt asks you to report that they were ignored.
- Treat `status: Duplicate` or non-null `duplicate_of` as duplicate evidence. Duplicates are reportable but not primary work.
- Treat `status: Cancelled` as excluded work.
- Closed/complete statuses are normally `Closed`, `Done`, `Verified`, and `Deployed`. Non-complete statuses include `Backlog`, `In Progress`, `Review`, and `Reopened`.

## Portfolio Category Resolution

Classify each included work item into exactly one of:

`NewFeature`, `TechDebt`, `Reliability`, `Security`

Use canonical `work_type` as the strongest structured signal, then labels and title as supporting signals. Do not use `legacy_category` as truth. The staged examples include intentional conflicts, so make an evidence table instead of relying on one keyword.

Category signals:

- `NewFeature`: `Feature`; feature, rollout, launch, new capability, enhancement/polish when no stronger reliability, security, or debt signal is present.
- `TechDebt`: `Refactor`, `Dependency`, `Chore`; cleanup, refactor, migration, deprecation, dependency, stale export cleanup.
- `Reliability`: `Reliability`, `Incident`, `Bug`; reliability, incident, outage, latency, flaky, postmortem, alert, recovery.
- `Security`: `Security`, `Compliance`; security, cve, auth, encryption, consent, audit, exception, compliance evidence.

Conflict handling:

- Explicit incident/reliability/outage/flaky/latency evidence overrides generic feature or rollout labels.
- Explicit security/compliance/cve/security/auth/encryption evidence overrides generic feature or rollout labels unless the item is clearly a refactor/dependency/cleanup debt item.
- Refactor/dependency/chore/cleanup/migration evidence usually maps to `TechDebt`, but do not let it override explicit `Security`, `Compliance`, `Reliability`, `Incident`, or `Bug` work types.
- Phrases like "stale label", `stale-export`, `mirror`, or legacy-only categories are noise markers, not primary classification evidence.

When the prompt says "portfolio category conventions," apply these rules consistently, then verify that every included primary item is counted once.

## Portfolio Mix Tasks

Use this workflow for Q/quarter portfolio mix prompts:

1. Parse the scope: quarter, teams, product areas, scope ID, and target scope ID.
2. Fetch `mix_targets` and select the row whose `scope_id` exactly matches the target. Convert target decimals to percentage points by multiplying by 100.
3. Filter work items to the requested teams, product areas, and quarter. Use closed date for quarter membership.
4. Include only primary closed work: canonical complete status, non-null `closed_at`, no duplicate marker, and not cancelled.
5. Record exclusions requested by the template:
   - duplicate IDs: in-scope records with `status: Duplicate` or non-null `duplicate_of`
   - cancelled IDs: in-scope records with `status: Cancelled`
   - distractors: records matching visible scope hints but not primary closed portfolio work
6. Sort included IDs by `closed_at` ascending, then ID ascending unless the template says otherwise.
7. Count categories by item count, not story points.
8. Compute actual percentages as `count / total * 100`, rounded to one decimal place.
9. Compute `gap_pct = actual_pct - target_pct`, rounded to one decimal place.
10. List categories in `NewFeature`, `TechDebt`, `Reliability`, `Security` order for mix/gap tables.
11. Under-invested categories are those with negative gaps, ordered from most negative to least negative.
12. For a rebalance recommendation, choose the largest negative-gap category as primary. If the schema asks for a secondary category, use the next most negative category or `null` when none exists. If no category is under target, use the no-negative-gaps action when available.

## SLA Aging Tasks

Use this workflow for SLA aging, overdue, breach-rate, hotspot, and escalation prompts:

1. Parse teams, categories, as-of date, and recent closed window length.
2. Load work items and `sla_policy`.
3. Resolve category using the portfolio rules, then keep items in the requested SLA categories.
4. Include primary records only:
   - created on or before the as-of date
   - not duplicate and not cancelled
   - either open/non-complete as of the as-of date, or closed within the recent window ending on the as-of date
5. If a closed date is after the as-of date, treat the item as still open at the as-of date.
6. Use `due_at` when present. If missing, compute due date from `created_at + sla_policy[severity].days_to_due`.
7. Overdue logic:
   - open primary work is overdue when `due_at < as_of`
   - recently closed primary work is overdue when `closed_at > due_at`
   - due on the as-of date is not overdue
8. Age logic:
   - open work age is `as_of - created_at` in whole days
   - closed work age is `closed_at - created_at` in whole days
   - bucket inclusively: `0-3`, `4-7`, `8-14`, `15-30`, `31+`
9. Duplicate clusters: report duplicate records that match the scope/time/category or point at an included primary item. Group by `duplicate_of`, sort clusters by `primary_id`, and sort each `duplicate_ids` list.
10. Missing owners are included primary records with null or empty owner.
11. Team overdue counts use overdue primary records and teams sorted alphabetically.
12. Owner/team hotspots group overdue primary records by `(team, owner)`, using `UNASSIGNED` for missing owners. Choose highest count, then deterministic alphabetical tie-breakers.
13. Breach rate is `overdue_primary_count / included_primary_count`, rounded to three decimal places. Use `0.000` when the denominator is zero and the schema allows it.
14. Escalation queues should order overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then earliest `due_at`, then lower numeric priority, then ID.

## Release Readiness Tasks

Use this workflow for release-readiness and ship-decision prompts:

1. Parse the release ID.
2. Fetch the release-specific endpoint when available, plus milestones, work items, blockers, and dependencies.
3. Authoritative release work is primary work with `release_id` matching the release, excluding duplicates and cancelled records. Do not use mirror status for release truth.
4. Milestone completion:
   - group primary release work by `milestone_id`
   - `complete_primary` counts canonical complete statuses
   - `primary_total` counts all primary release work in the milestone
   - `completion_pct = complete_primary / primary_total * 100`, rounded to one decimal
   - sort rows by `milestone_id`
5. `readiness_score` is total completed primary release work divided by total primary release work, rounded to three decimals.
6. Unresolved high-impact blockers have the release ID, no `resolved_at`, an open/non-resolved status, and severity `High` or `Critical`. Count them by exact `cause` text.
7. `gating_work_item_ids` are sorted unique non-complete primary release work items that have unresolved high-impact blockers or are blocked by non-complete readiness-critical dependencies.
8. Dependency chains:
   - build a directed graph from `blocked_id` to `depends_on_id`
   - start from non-complete primary release work, especially items already gating readiness
   - follow dependency edges without cycles
   - include ordered ID paths that end at a non-complete dependency
   - sort chains lexicographically by the full path
9. Ship decision:
   - `NO_SHIP` when unresolved high-impact blockers or non-complete critical dependency chains remain
   - `SHIP_WITH_WATCH` when only low/monitoring blockers, non-gating incomplete work, or watch items remain
   - `SHIP` when primary release work is complete and no unresolved readiness risks remain

## JSON Discipline

- Match the answer template exactly. If it is a JSON Schema, obey required fields, constants, enums, `additionalProperties: false`, and ordering descriptions. If it is a descriptive JSON template, reproduce the same key structure with real values.
- Use numbers for numeric outputs, not strings, unless the template explicitly asks for strings.
- Round only at the output boundary:
  - one decimal place for percentages
  - three decimal places for breach/readiness rates
- Keep stable ordering:
  - ID lists lexicographic when requested
  - included portfolio work by `closed_at`, then ID when requested
  - category rows as `NewFeature`, `TechDebt`, `Reliability`, `Security`
  - teams alphabetically unless the template specifies a custom order
  - duplicate clusters by `primary_id`
  - dependency chains lexicographically by the full path
- Before final output, verify:
  - all included IDs are primary records
  - all excluded duplicate/cancelled/distractor IDs really match the prompt's exclusion definition
  - category counts sum to total included
  - percentages and gaps reconcile with counts and targets
  - breach/readiness numerators and denominators match the listed IDs
  - no stale mirror or legacy field changed the canonical result

Return a single valid JSON object and nothing else.
