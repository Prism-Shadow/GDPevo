---
name: engineering-portfolio-review
description: Solve engineering portfolio environment analysis tasks that require JSON answers from a shared task API. Use for portfolio mix reviews, SLA aging audits, release-readiness assessments, work item classification, duplicate exclusion, stale mirror-field handling, mix target comparison, blocker/dependency analysis, and exact answer-template shaping.
---

# Engineering Portfolio Review

Use this skill when a task asks for a JSON answer from the shared engineering portfolio environment. The recurring task families are portfolio mix, SLA aging, and release readiness.

## Core Workflow

1. Read the user prompt, `environment_access.md`, and the requested answer template before fetching data.
2. Use the base URL and allowed endpoints from `environment_access.md`. Prefer REST endpoints. Use `POST /api/query` only when the runtime notes provide the required token or headers.
3. Build the answer from authoritative fields:
   - Trust `status`, `closed_at`, `created_at`, `due_at`, `release_id`, `milestone_id`, `duplicate_of`, `work_type`, `labels`, `title`, `team`, `product_area`, `owner`, `severity`, and `priority`.
   - Do not use `mirror_status` or `legacy_category` as truth for status, release membership, or category classification.
4. Separate primary work from duplicates and cancelled records before counting. A primary item has no `duplicate_of` and is not in `Duplicate` or `Cancelled` status.
5. Classify every included item into exactly one portfolio category using the precedence and field rules in [engineering_portfolio_rules.md](references/engineering_portfolio_rules.md).
6. Compute numeric results from counts, not story points, unless the prompt explicitly says otherwise.
7. Match the provided answer template exactly: required keys, nesting, sorting, enum strings, and precision override generic conventions.
8. Return only the JSON object when the task asks for JSON only.

## Helper Script

Run [portfolio_env_helper.py](scripts/portfolio_env_helper.py) to produce candidate calculations, then adapt the resulting JSON to the exact template.

```bash
python3 skill/scripts/portfolio_env_helper.py portfolio-mix \
  --base-url "$TASK_ENV_BASE_URL" \
  --scope-id "$SCOPE_ID" \
  --quarter "YYYY-QN" \
  --teams "Team A,Team B" \
  --product-areas "Area A,Area B"

python3 skill/scripts/portfolio_env_helper.py sla-aging \
  --base-url "$TASK_ENV_BASE_URL" \
  --teams "Team A,Team B" \
  --as-of "YYYY-MM-DD" \
  --window-days 14 \
  --categories "Reliability,Security"

python3 skill/scripts/portfolio_env_helper.py release-readiness \
  --base-url "$TASK_ENV_BASE_URL" \
  --release-id "$RELEASE_ID"
```

The script emits a normalized answer draft. It intentionally does not know task-specific schemas; the final response must still follow the task's `answer_template.json`.

## Task Patterns

### Portfolio Mix

Use the scoped quarter, teams, product areas, and mix target row. Include closed primary work in the quarter only. Exclude duplicates and cancelled records, but report them in the requested exclusion structure.

Sort included IDs by `closed_at` ascending, then ID. Build category rows in this order unless the template says otherwise: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Convert target fractions from `mix_targets` into percentage points. Round actual percentages and gaps to one decimal place. Define `gap_pct = actual_pct - target_pct`.

When the answer asks for under-invested categories, list categories with negative gaps from most negative to least negative. For a rebalance action, use the largest negative gap as the primary category and the next negative gap as secondary when a secondary field exists.

### SLA Aging

Use the scoped teams, categories, as-of date, and recent closed window. Include primary work that is open as of the as-of date or closed within the recent window. Treat work closed after the as-of date as open for historical calculations.

Exclude records whose `created_at` is after the as-of date. Use `due_at` as the due date. If it is missing, derive it from `created_at` plus the matching severity row in `sla_policy`. A primary item is overdue when its due date is strictly before the effective date, where the effective date is `closed_at` for work closed on or before the as-of date and the as-of date otherwise.

Aging buckets are based on calendar days from `created_at` to the effective date. Missing owners are primary included items with no owner. Duplicate clusters are reported by `duplicate_of` but excluded from primary counts. Breach rate is `overdue primary / included primary`, rounded to three decimal places.

For escalation queues, order overdue primary work by severity rank `S1`, `S2`, `S3`, `S4`, then oldest due date, then lower numeric priority, then ID.

### Release Readiness

Use release and milestone endpoints for release truth; do not infer release membership from stale mirrored fields. For each release milestone, count primary work whose `release_id` and `milestone_id` match. Treat `Closed`, `Done`, `Deployed`, and `Verified` as complete.

Count unresolved high-impact blockers only when `resolved_at` is absent, status is not `Resolved`, and blocker severity is `High` or `Critical`. Keep blocker cause strings exact. Gating work items are non-complete primary release items with unresolved high-impact blockers or critical dependency chains to non-complete work.

For dependency chains, start from non-complete primary release work that also has an unresolved high-impact blocker, then follow dependency records to dependencies. Emit ordered ID paths that end at a non-complete dependency, avoid cycles, de-duplicate paths, and sort paths lexicographically by the full path.

Readiness score is completed primary milestone work divided by total primary milestone work, rounded to three decimals. Choose `NO_SHIP` when there are gating items or non-complete critical dependency chains, `SHIP_WITH_WATCH` when readiness is imperfect or unresolved blockers remain but no hard gate is present, and `SHIP` only when primary work is complete and no unresolved blocker/dependency risk remains.
