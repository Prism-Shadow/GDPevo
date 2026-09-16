---
name: engineering-portfolio-audit
description: Analyze shared engineering portfolio task environments and produce schema-exact JSON answers for work item portfolio mix, SLA aging, release readiness, blockers, dependencies, duplicate clusters, stale mirror fields, and prompts that provide a TASK_ENV_BASE_URL plus answer_template.json.
---

# Engineering Portfolio Audit

Use this skill to answer task-environment prompts that ask for portfolio mix, SLA aging, or release readiness from work item data. Treat the prompt and `input/payloads/answer_template.json` as the output contract.

## Core Workflow

1. Read the user prompt, answer template, and runtime access file. Extract the base URL, allowed endpoints, scope filters, dates, precision, ordering, and required JSON keys.
2. Fetch the environment data. Prefer `scripts/fetch_env_snapshot.py` for documented GET endpoints:

   ```bash
   python3 skill/scripts/fetch_env_snapshot.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/task-env-snapshot.json
   ```

   If a restricted SQL query token is supplied, pass it only to documented query calls that need it. The observed GET endpoints are sufficient for portfolio mix, SLA aging, and release readiness tasks.
3. Load `references/analysis-rules.md` for reusable field semantics, filtering rules, calculations, and tie-breakers.
4. Work from authoritative fields on the primary records. Ignore stale mirror/export fields such as `mirror_status` and `legacy_category` unless the prompt or template explicitly asks for a flag showing that they were ignored.
5. Separate primary work from duplicates and cancelled records before calculating totals. Report duplicate clusters and exclusions only in fields that ask for them.
6. Build the JSON object directly against the template. Preserve required key names, enum values, list ordering, and number precision. Return JSON only, with no prose.

## Validation Checklist

- Confirm every required template key is present and no disallowed key is added.
- Confirm all IDs are unique in primary lists unless the template says otherwise.
- Confirm denominator choices before calculating percentages and breach rates.
- Confirm date windows are inclusive unless the prompt says otherwise.
- Confirm stable ordering: template descriptions override the defaults in the reference.
- Parse the final answer with `python3 -m json.tool` before returning it.
