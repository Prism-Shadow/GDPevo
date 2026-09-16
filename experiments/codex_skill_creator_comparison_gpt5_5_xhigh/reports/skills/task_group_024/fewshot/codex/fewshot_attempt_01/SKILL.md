---
name: engineering-portfolio-env
description: Analyze the shared engineering portfolio task environment and return exact JSON for portfolio mix reviews, SLA aging audits, and release-readiness assessments. Use when a prompt references TASK_ENV_BASE_URL, work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, or asks to distinguish primary work from duplicates/cancelled/stale mirror records.
---

# Engineering Portfolio Environment

Use this skill to solve JSON-only task-environment audits. The common work is to fetch the allowed API data, identify the primary population, compute metrics, and then shape the result to the task's payload template.

## Workflow

1. Read the user prompt, `environment_access.md`, and every file under `input/payloads/`.
2. Extract the task family:
   - Portfolio mix: scope id, quarter, teams, product area(s), and mix target.
   - SLA aging: teams, as-of date, recent closed window, and requested SLA categories.
   - Release readiness: release id and required release metrics.
3. Fetch only the required API endpoints from the base URL in `environment_access.md`. Prefer `GET` endpoints; use `POST /api/query` only for filtering when useful.
4. Use authoritative fields on records: `status`, `closed_at`, `duplicate_of`, `work_type`, `labels`, `title`, `team`, `product_area`, `release_id`, `milestone_id`, `due_at`, `severity`, `priority`, and `owner`.
5. Ignore stale mirror/export fields for truth: do not decide from `mirror_status` or `legacy_category`.
6. Apply the rules in [references/rules.md](references/rules.md).
7. Return one JSON object matching the payload template exactly. Do not include prose, markdown fences, or extra keys.

## Helper Script

Use [scripts/env_audit.py](scripts/env_audit.py) to fetch the environment and compute reusable intermediate metrics:

```bash
python skill/scripts/env_audit.py portfolio \
  --base-url "$TASK_ENV_BASE_URL" \
  --quarter YYYY-QN \
  --teams "Team A,Team B" \
  --product-areas "Area One,Area Two" \
  --scope-id "scope-id-from-prompt"

python skill/scripts/env_audit.py sla \
  --base-url "$TASK_ENV_BASE_URL" \
  --teams "Team A,Team B" \
  --as-of YYYY-MM-DD \
  --window-days N \
  --categories "Reliability,Security"

python skill/scripts/env_audit.py release \
  --base-url "$TASK_ENV_BASE_URL" \
  --release-id "REL-..."
```

Treat the script output as a calculation aid, not a substitute for the task template. Rename keys, omit helper-only fields, and apply any prompt-specific ordering requested by the payload schema.

## Final Checks

- Lists are usually sorted lexicographically unless the template states another order, such as closed date order or escalation priority.
- Percentages in portfolio tasks are percentage points, not fractions.
- `gap_pct = actual_pct - target_pct`.
- SLA breach rate is overdue primary count divided by included primary count.
- Release readiness score is complete primary release work divided by primary release work.
- Validate the final answer with `python -m json.tool` before returning when possible.
