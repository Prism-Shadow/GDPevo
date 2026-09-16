---
name: engineering-portfolio-review
description: Solve engineering portfolio environment review tasks that ask for JSON answers from shared work-item APIs, including portfolio mix, SLA aging, release readiness, blockers, dependencies, duplicate handling, and stale mirror field avoidance. Use this skill whenever a task mentions work items, mix targets, SLA policy, release readiness, blockers, dependencies, or a shared task environment with an answer_template.json.
---

# Engineering Portfolio Review

Use this skill to produce schema-exact JSON answers for engineering portfolio tasks backed by the shared REST environment.

## Workflow

1. Read the user prompt, `input/payloads/answer_template.json`, and the runtime access file supplied with the task.
2. Fetch authoritative environment data from the allowed endpoints. Prefer the helper script in `scripts/env_review.py` for repeatable calculations.
3. Build the answer to match the template exactly: keep only required fields, preserve enum strings, obey requested ordering, and return JSON only.
4. Treat `status`, `work_type`, `labels`, `title`, `closed_at`, `due_at`, `duplicate_of`, `release_id`, and `milestone_id` as authoritative. Use `mirror_status` and `legacy_category` only as stale/conflict evidence, not as truth.

## Helper Script

Run the helper from the task workspace, passing the task environment access file or base URL:

```bash
python skill/scripts/env_review.py --env-file environment_access.md snapshot
python skill/scripts/env_review.py --env-file environment_access.md portfolio --scope-id SCOPE --quarter YYYY-QN --teams "Team A" "Team B" --product-areas "Area A" "Area B" --target-scope-id SCOPE
python skill/scripts/env_review.py --env-file environment_access.md sla --as-of YYYY-MM-DD --recent-closed-window-days N --teams "Team A" "Team B" --categories Reliability Security
python skill/scripts/env_review.py --env-file environment_access.md release --release-id RELEASE-ID
```

The script emits a generic JSON analysis. Map its fields into the task's exact `answer_template.json`; do not copy script-only convenience fields if the template does not request them.

## Shared Rules

- Primary work excludes records with `status` equal to `Duplicate`, `Cancelled`, or `Canceled`, and records whose `duplicate_of` points at another item.
- Completed work uses the authoritative `status` field. Treat `Closed`, `Done`, `Verified`, `Deployed`, and `Complete` as complete statuses.
- Sort lexicographic ID lists ascending unless the prompt specifies lifecycle ordering. For portfolio included IDs, use `closed_at` ascending, then ID ascending.
- Round percentage-point outputs to one decimal place and ratio outputs such as breach or readiness rates to three decimal places.
- Use count-based portfolio mix; do not weight by story points.

## Portfolio Mix

Filter closed primary work by quarter, team, and product area. Exclude duplicate and cancelled same-scope records, but report them if the template asks for exclusion flags or distractors.

Resolve each included item into one portfolio category using `work_type`, `labels`, and `title`, with this precedence:

1. `Security`: security, cve, auth, encryption, compliance, or work type `Security` or `Compliance`.
2. `Reliability`: reliability, incident, outage, latency, flaky, retry, bug, or work type `Reliability`, `Incident`, or `Bug`.
3. `TechDebt`: refactor, migration, cleanup, dependency, deprecate, legacy, chore, or work type `Refactor`, `Dependency`, or `Chore`.
4. `NewFeature`: feature, enhancement, rollout, launch, customer request, or work type `Feature` or `Enhancement`.

Compare actual percentages against the matching `mix_targets` row. Convert target fractions to percentage points. `gap_pct = actual_pct - target_pct`. Under-invested categories are negative gaps ordered from most negative to least negative. A rebalance recommendation usually points first at the largest deficit and second at the next deficit, if any.

## SLA Aging

For SLA scopes, include primary work in the requested teams and categories that was created on or before the as-of date and is either still open as of that date or closed within the prompt's recent closed window.

Calculate:

- Overdue primary work: `due_at` before the as-of date and not closed on or before `due_at`. If `due_at` is absent, derive it from `created_at` plus the SLA policy days for the item's severity.
- Aging buckets: days from `created_at` to `closed_at` for recently closed work, otherwise to the as-of date. Use buckets `0-3`, `4-7`, `8-14`, `15-30`, `31+`.
- Missing owners: included primary records whose `owner` is null or empty.
- Duplicate clusters: in-scope duplicate records grouped under `duplicate_of`; report but do not count them as primary work.
- Breach rate: overdue primary count divided by included primary count, rounded to three decimals.
- Escalation queues, when requested: sort overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then due date, priority, created date, and ID.

## Release Readiness

For release tasks, use release, milestone, work item, blocker, and dependency records. Do not use mirror fields as release truth.

- Milestone completion: for every release milestone, count primary release work by `milestone_id`; completion is complete primary divided by primary total.
- Readiness score: complete primary release work divided by all primary release work, rounded to three decimals.
- High-impact blockers: unresolved blockers with severity `High` or `Critical`; count causes by exact `cause` string.
- Gating work IDs: non-complete primary release work that has an unresolved high-impact blocker or a dependency chain to non-complete work.
- Critical dependency chains: ordered paths from blocked release work to a non-complete dependency; sort chains lexicographically by the full path.

Ship decision guidance: return `NO_SHIP` when non-complete gated work, unresolved critical blockers, critical dependency chains, or a low readiness score create hard release risk. Return `SHIP_WITH_WATCH` for residual non-critical risk. Return `SHIP` only when primary work is complete and no unresolved release risk remains.
