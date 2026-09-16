---
name: support-console-resolver
description: Resolve support-console tasks that require using a shared support console API to classify service tickets, mobile/contact-center cases, mobile-data recovery worklists, or enterprise export incidents and return strict JSON answers matching a provided answer_template.json. Use when prompts mention support operations, support-console records, same-day ticket batches, queue-quality handoff, mobile support queues, mobile data recovery, or enterprise export complaint response packages.
---

# Support Console Resolver

## Workflow

1. Read the prompt, every payload file, and `answer_template.json` before calling the API.
2. Use the task's base URL exactly as provided. Confirm `/health` and `/api/catalog`, then fetch authoritative support-console records; never decide from payload wording alone.
3. Preserve the output shape, key names, enums, item ordering, numeric precision, and "return only JSON" requirement from the template.
4. For lookup and joins, use [references/support_console_rules.md](references/support_console_rules.md). For faster evidence gathering, run `scripts/fetch_support_console.py` with the task base URL and the IDs from the payload.
5. Build a small evidence table per item, apply the priority rules, compute summaries from the final decisions, and validate the JSON before answering.

## Evidence Fetching

Use the helper when several related records are needed:

```bash
python3 scripts/fetch_support_console.py --base-url "$TASK_ENV_BASE_URL" --tickets TCK-1 TCK-2
python3 scripts/fetch_support_console.py --base-url "$TASK_ENV_BASE_URL" --cases CASE-1 CASE-2
python3 scripts/fetch_support_console.py --base-url "$TASK_ENV_BASE_URL" --enterprise-incidents INC-1
python3 scripts/fetch_support_console.py --base-url "$TASK_ENV_BASE_URL" --search "client or record id"
```

The helper is intentionally read-only. If an endpoint alias fails, inspect `/api/catalog` and retry with the catalog path.

## Answer Discipline

- Keep ticket rows in payload order unless the template explicitly says otherwise.
- Sort case outputs by ascending `case_id` when requested, even if the payload order differs.
- Use empty strings, `false`, `0.0`, or `NO_ACTION` only when the template says the field is not applicable.
- Compute all summary counts from the completed decision array. Include zero counts for summary keys present in the template.
- Do not include explanation, markdown, evidence notes, or fields not present in the template.
