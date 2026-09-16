---
name: portfolio-environment-analysis
description: Solve engineering portfolio analysis tasks against the shared task environment, including portfolio mix reviews, SLA aging audits, and release-readiness assessments. Use when prompts mention work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, duplicate/cancelled records, stale mirror fields, or JSON answers shaped by an answer_template.json payload.
---

# Portfolio Environment Analysis

Use this skill to produce JSON answers from the read-only portfolio task environment.

## Workflow

1. Read the user prompt and any `input/payloads/answer_template.json` before querying data.
2. Read the runtime access file for the base URL, token, and allowed endpoints. Do not call judge endpoints.
3. Prefer the authoritative fields in the environment records:
   - Work item truth: `status`, `closed_at`, `created_at`, `due_at`, `duplicate_of`, `work_type`, `labels`, `title`, `team`, `product_area`, `owner`, `severity`, `priority`, `release_id`, `milestone_id`.
   - Ignore stale mirror/export fields such as `mirror_status` and `legacy_category` when deciding status or portfolio category.
4. Use [scripts/portfolio_tool.py](scripts/portfolio_tool.py) to fetch the allowed API data and compute a reusable summary, then adapt that summary to the exact answer template.
5. For detailed rules and edge cases, read [references/rules.md](references/rules.md).

## Helper Commands

Replace `<BASE_URL>` with the runtime environment base URL.

Portfolio mix:

```bash
python3 skill/scripts/portfolio_tool.py portfolio-mix \
  --base-url <BASE_URL> \
  --scope-id <SCOPE_ID> \
  --quarter <YYYY-QN> \
  --team "<TEAM>" --team "<TEAM>" \
  --product-area "<AREA>" --product-area "<AREA>"
```

SLA aging:

```bash
python3 skill/scripts/portfolio_tool.py sla-aging \
  --base-url <BASE_URL> \
  --as-of <YYYY-MM-DD> \
  --recent-closed-window-days <N> \
  --team "<TEAM>" --team "<TEAM>" \
  --category Security --category Reliability
```

Release readiness:

```bash
python3 skill/scripts/portfolio_tool.py release-readiness \
  --base-url <BASE_URL> \
  --release-id <RELEASE_ID>
```

## Output Discipline

Return only the JSON requested by the prompt. Preserve template field names, ordering requirements, sort order, and rounding precision. If the helper emits extra diagnostic fields, omit them unless the template asks for them.
