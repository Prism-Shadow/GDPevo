---
name: engineering-portfolio-env
description: Solve JSON-only engineering portfolio environment tasks that use a shared task API for work items, mix targets, SLA policy, releases, milestones, blockers, and dependencies. Use for portfolio mix reviews, SLA aging audits, release readiness decisions, duplicate/distractor exclusion, canonical category/status resolution, strict answer_template.json outputs, and any prompt mentioning <TASK_ENV_BASE_URL> with these engineering portfolio endpoints.
---

# Engineering Portfolio Environment

Use this skill for tasks that ask you to inspect the shared engineering portfolio environment and return a single JSON answer.

## First Steps

1. Read the user prompt completely, then read every file in `input/payloads/`, especially `answer_template.json`.
2. Read the runtime access file for the base URL, allowed endpoints, and any query token. Prefer the documented GET endpoints; use `POST /api/query` only when the runtime access notes provide a valid token and it is genuinely useful.
3. Read [references/domain-rules.md](references/domain-rules.md) before calculating. It contains the reusable status, category, portfolio-mix, SLA, and release-readiness rules.
4. Optionally snapshot the environment with:

```bash
python3 skill/scripts/fetch_env_snapshot.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/portfolio_env_snapshot.json
```

If the prompt gives a literal base URL instead of `TASK_ENV_BASE_URL`, pass that URL directly.

## Working Method

Build the answer from authoritative API data, not from stale mirror/export fields. For work items, rely on canonical fields such as `status`, `duplicate_of`, `closed_at`, `created_at`, `due_at`, `work_type`, `labels`, `title`, `team`, `product_area`, `owner`, `severity`, `priority`, `release_id`, and `milestone_id`. Treat `mirror_status` and `legacy_category` as stale unless the answer asks you to report that they were ignored.

Use the prompt to choose the calculation path:

- Portfolio mix: filter primary closed work for the requested quarter, teams, product area/scope, classify each included item once, compare count-based percentages to the matching mix target, and report exclusions/rebalance fields requested by the template.
- SLA aging: build the primary SLA population from scoped teams and Security/Reliability categories, include open work plus recently closed work, separate duplicate clusters, calculate overdue/aging/hotspot/escalation fields, and round breach rates to three decimals.
- Release readiness: use release and milestone data as release truth, compute milestone completion over primary release work, count unresolved high-impact blocker causes, trace dependency chains from incomplete release work to incomplete dependencies, and derive the ship decision.

## Final JSON Check

Before answering:

- Match the template keys and nesting exactly. Do not add prose or markdown.
- Use real JSON numbers for counts, percentages, rates, and scores, not strings copied from template placeholders.
- Apply every ordering rule in the prompt/template. If absent, sort IDs lexicographically except portfolio included/excluded IDs that explicitly request `closed_at` order.
- Round only at the requested output precision: one decimal for percentage points, three decimals for rates/scores.
- Recompute sanity checks: count totals equal included IDs; percentages are count-based; gaps are `actual_pct - target_pct`; breach/readiness rates use the final denominators; duplicate/cancelled records are excluded from primary denominators.
