---
name: finance-ops-reporting
description: Solve Crescent Finance Ops reporting tasks that provide prompt.txt plus payloads/request_memo.json, environment_access.json, and answer_template.json. Use for branch close, regional management, compensation current-year or forecast, and weekly payroll JSON answers from the Finance Ops API.
---

# Finance Ops Reporting

Use this skill for Crescent Finance Ops tasks that ask for a single JSON answer from the Finance Ops API.

## Fast Path

1. Read the task prompt and the three payload files: `request_memo.json`, `environment_access.json`, and `answer_template.json`.
2. Run the bundled calculator from the task input directory:

```bash
python /path/to/skill/scripts/finance_ops_report.py /path/to/task/input
```

If `payloads/environment_access.json` contains a placeholder base URL, pass the actual task environment URL:

```bash
python /path/to/skill/scripts/finance_ops_report.py /path/to/task/input --base-url http://task-env:9009/
```

3. Return the script's JSON object only. Do not add prose, Markdown, citations, or extra keys.

## Manual Fallback

If the script cannot classify a new variant, read [references/calculation-rules.md](references/calculation-rules.md) and compute the requested fields manually. Keep the output shaped by `answer_template.json`, not by examples from other tasks.

## Guardrails

- Use only the task-local payloads and the Finance Ops API endpoints listed for the task.
- Round currency fields to 2 decimals and percent or ratio fields to 4 decimals unless the task template says otherwise.
- Keep stable ID lists ascending unless the field is explicitly a descending rank or top/bottom fact.
- For payroll `per_musician`, sort by `musician_id`; sort `conflict_flags` alphabetically.
- Never copy prior answer values into a new response. Recompute every field from the current memo, template, and API data.
