---
name: engineering-portfolio-audits
description: Analyze engineering portfolio task environments and produce strict JSON answers for portfolio mix, SLA aging, and release-readiness reviews. Use when prompts mention work items, mix targets, SLA policies, releases, milestones, blockers, dependencies, stale mirror/export fields, duplicate or cancelled records, <TASK_ENV_BASE_URL>, environment_access.md, or answer_template.json.
---

# Engineering Portfolio Audits

## Core Workflow

1. Read the user prompt and the referenced `answer_template.json` before querying data. Treat schema descriptions as requirements for sorting, rounding, field names, and enum choices.
2. Read `environment_access.md` for the base URL, allowed endpoints, and any query token. Use only the listed endpoints. Prefer REST endpoints; use `/api/query` only for targeted checks, passing the runtime token header from `environment_access.md`.
3. Fetch the needed datasets once and keep their top-level wrappers in mind: endpoints return objects such as `work_items`, `mix_targets`, `sla_policy`, `releases`, `milestones`, `dependencies`, and `blockers`.
4. Use authoritative fields on the core records. Do not use `mirror_status` as truth, and do not let `legacy_category` or labels such as `stale-export` override authoritative `status`, `work_type`, `release_id`, `milestone_id`, `closed_at`, or `duplicate_of`.
5. Return exactly the JSON object requested by the template. Do not include prose outside the JSON.

## Shared Record Rules

- Treat these statuses as complete: `Closed`, `Done`, `Deployed`, `Verified`.
- Treat primary/canonical work as records where `status` is not `Duplicate`, `duplicate_of` is empty, and `status` is not `Cancelled`.
- Exclude duplicate records from primary denominators when either `status == "Duplicate"` or `duplicate_of` is populated. If duplicate clusters are requested, group duplicates by `duplicate_of` when present; records marked duplicate without a canonical id are exclusions/distractors, not primary work.
- Exclude cancelled records from primary work even when they have `closed_at` or a stale mirror status that looks complete.
- Sort ID lists exactly as requested. If no task-specific order is given, sort lexicographically for plain ID sets and by `(closed_at, id)` for closed-work lists.

## Portfolio Category Resolver

Use `work_type` as the primary category signal. Labels, title terms, and `legacy_category` are fallbacks only when `work_type` is missing or unrecognized.

Recognized `work_type` mapping:

```text
Feature, Enhancement       -> NewFeature
Refactor, Chore, Dependency -> TechDebt
Reliability, Incident, Bug -> Reliability
Security, Compliance       -> Security
```

Fallback signal order for unknown types:

```text
Security:    security, cve, auth, encryption, compliance
Reliability: reliability, incident, outage, latency, flaky, bug
TechDebt:    refactor, cleanup, migration, dependency, chore
NewFeature:  feature, enhancement, rollout, customer-request
```

Do not reclassify a recognized `work_type` because a label, title, or legacy category conflicts with it.

## Closed Portfolio Mix

1. Convert the requested quarter to an inclusive date range.
2. Select primary work items with `closed_at` inside the quarter and matching all scoped teams and product areas.
3. Use item counts, not story points, for category counts and mix percentages.
4. Pull the target mix from `mix_targets` using the requested `scope_id` when provided. Target values are fractions; convert to percentage points.
5. Compute `actual_pct = count / total * 100` and round to one decimal place. Compute `gap_pct = actual_pct - target_pct` after converting the target to percentage points, then round to one decimal place.
6. Under-invested categories are categories with negative gaps, ordered from most negative to least negative.
7. For rebalance actions, use the largest negative gap as the primary category. If a secondary category is required, choose the largest positive gap as the source category, using the template's category order as a tie-breaker. If an owner team is required, choose the scoped team with the lowest included count in the deficit category, using the prompt/template order as a tie-breaker.
8. Report same-scope quarter distractors requested by the template, especially duplicates and cancelled records, but do not count them in the primary mix.

## SLA Aging

1. Resolve the SLA categories using the portfolio category resolver, usually `Reliability` and `Security`.
2. Select records matching the scoped teams and categories with `created_at <= as_of`.
3. Include primary work that is still open as of the date, plus primary work closed in the recent closed window. Use `as_of - window_days <= closed_at <= as_of` for the inclusive recent-closed window.
4. Build duplicate clusters from duplicate records that match the same team/category/as-of/window scope, then exclude them from all primary counts.
5. Use the SLA policy as the due rule: allowed days come from `/api/sla-policy` by severity. Do not calculate breaches from `due_at` if it conflicts with the severity policy.
6. For active work, set `age_days = as_of - created_at`. For recently closed work, set `age_days = closed_at - created_at`. Use date differences in whole days, not inclusive day counts.
7. A primary item is overdue when `age_days > policy_days_for_severity`.
8. Aging buckets are normally `0-3`, `4-7`, `8-14`, `15-30`, and `31+`, based on `age_days`.
9. Missing-owner lists include primary included records whose `owner` is null or empty.
10. Breach rate is `overdue_primary_count / included_primary_count`, rounded to the precision requested by the template.
11. For overdue hotspots, count overdue primary records by team and owner, using `UNASSIGNED` for missing owners. Break ties by team name, then owner name unless the prompt gives another rule.
12. For escalation queues, sort overdue primary work by severity rank `S1` to `S4`, then numeric `priority` ascending, then days overdue descending, then id.

## Release Readiness

1. Fetch the release, its milestones, work items, blockers, and dependencies. Use `release_id` and `milestone_id` as authoritative; ignore mirror fields.
2. Primary release work is work with the matching `release_id`, excluding duplicate and cancelled records.
3. For each milestone in the release, compute `complete_primary`, `primary_total`, and `completion_pct = complete_primary / primary_total * 100`, rounded as requested. Include every release milestone even when it has zero work, and sort by `milestone_id` if required.
4. `readiness_score` is completed primary release work divided by the primary release denominator, rounded as requested.
5. Gating work item ids are primary release work items whose authoritative `status` is not complete. Sort and de-duplicate them.
6. Unresolved blockers have `resolved_at` empty and `status` not `Resolved`. High-impact blockers are `High` or `Critical`. Count causes by exact `cause` text; do not drop a blocker just because its work item is otherwise complete.
7. For dependency chains, build paths from a primary release work item through `dependencies.blocked_id -> depends_on_id`. Include paths that end at a work item whose authoritative status is not complete; traverse further if the dependency has its own dependencies. Sort chains lexicographically by the full path.
8. Use ship decisions consistently: choose `NO_SHIP` when high-impact unresolved blockers, gating primary work, or non-complete readiness dependency chains remain; choose `SHIP_WITH_WATCH` when primary work is complete but lower-impact unresolved risks remain; choose `SHIP` only when primary work is complete and no unresolved readiness risks remain.

## Output Checks

- Match the template exactly: no extra keys, no missing required keys, and enum values exactly as written.
- Preserve requested category row order, team order, and object shape.
- Round only final reported values to the requested precision.
- Recompute denominators after exclusions; never include duplicate or cancelled work in primary totals.
- When a value is ambiguous, prefer the authoritative field hierarchy in this skill and make the output deterministic through stable sorting.
