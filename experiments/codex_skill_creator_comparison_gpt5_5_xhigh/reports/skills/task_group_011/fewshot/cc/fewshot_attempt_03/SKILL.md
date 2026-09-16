---
name: credit-office-json
description: Use this skill for credit office committee tasks that require JSON answers from the shared public API, including branch loan regrades, watch-list stress packets, pending application allocation, competing CRE decisions, FDIC or NCUA benchmark variance, concentration flags, CDFI factor scores, and schema/enums in answer_template.json. Trigger whenever the prompt mentions TASK_ENV_BASE_URL, branch_id, segment_id, credit policy, lending committee, or committee-ready JSON from a credit-office API.
compatibility: Requires Python 3 standard library and network access to the task API supplied in the prompt.
---

# Credit Office JSON Solver

Use this skill when a task asks for a committee-ready JSON answer from the shared credit office API. These tasks are data-reconciliation problems: fetch the public records, apply the public policy formulas, and shape the answer exactly to `input/payloads/answer_template.json`.

## Required Workflow

1. Read the prompt and `input/payloads/answer_template.json` completely before fetching data.
2. Use the API base URL from the task runner, usually `TASK_ENV_BASE_URL`; if the prompt gives a literal base URL, use that. Do not read local task-environment data files.
3. Fetch `GET /api/manifest` and `GET /api/policies` first. Treat policy payloads as authoritative if they differ from this skill's remembered formulas.
4. Fetch only public endpoints needed by the prompt:
   - Branch tasks: `/api/branches/{branch_id}`, `/api/branches/{branch_id}/metrics`, `/api/branches/{branch_id}/loans`, `/api/branches/{branch_id}/sector-exposures`, and `/api/branches/{branch_id}/applications` as applicable.
   - Bank benchmark tasks: `/api/benchmarks/fdic/q4-2024`.
   - Credit-union segment tasks: `/api/credit-union-segments/{segment_id}` and `/api/benchmarks/ncua/q1-2025`.
5. Build a small scratch derivation table before composing the final JSON. Check totals, ratios, ordering, and enum spellings against the template.
6. Return only valid JSON. Do not include narrative, citations, Markdown, comments, or fields not requested by the template.

## Helper Script

The bundled helper is optional but useful for avoiding arithmetic drift:

```bash
python scripts/credit_office_tools.py snapshot --base-url "$TASK_ENV_BASE_URL" --branch-id "$BRANCH_ID"
python scripts/credit_office_tools.py regrade --base-url "$TASK_ENV_BASE_URL" --branch-id "$BRANCH_ID" --min-rating 3
python scripts/credit_office_tools.py watchlist --base-url "$TASK_ENV_BASE_URL" --branch-id "$BRANCH_ID" --min-rating 6
python scripts/credit_office_tools.py segment --base-url "$TASK_ENV_BASE_URL" --segment-id "$SEGMENT_ID"
python scripts/credit_office_tools.py cre-compare --base-url "$TASK_ENV_BASE_URL" --branch-id "$BRANCH_ID" --applications APP-1,APP-2
```

The helper prints derivation JSON, not the final answer. Use it as an audit aid, then conform to the prompt's template.

Read [credit-office-rules.md](references/credit-office-rules.md) when the task involves rating migration, watch-list stress, application decisions, concentration limits, or benchmark comparisons.

## Output Discipline

- Match every required top-level key and nested key from the template.
- Use only allowed enum values from the template.
- Sort arrays exactly as the template says, commonly by ascending IDs, ascending enum/text keys, descending exposure, or ascending rating/status.
- Preserve identifier strings exactly from API records.
- Round currency to 2 decimals, ratios to 4 decimals, basis points to 2 decimals, DSCR to 2 decimals, and weighted scores to 1 decimal unless the template says otherwise.
- Use JSON numbers for numeric fields, not strings.
- If a calculation has no available source field, omit it only when the template allows omission; otherwise use the best supported value from fetched records and keep the derivation internally consistent.

## Common Endpoint Mapping

- Portfolio regrade: branch, metrics, loans, policies, FDIC benchmark.
- Watch-list stress: branch loans and policies; metrics only if requested for context.
- Lending allocation: branch, branch metrics, sector exposures, applications, policies, and sometimes FDIC benchmark.
- Competing CRE decision: branch, metrics, loans or sector exposures, applications, policies, and FDIC benchmark.
- Credit-union posture: segment endpoint, policies, NCUA benchmark, and manifest.

For date-bound prompts, select the metric quarter matching the review/as-of date. For `2025-03-31`, that is `2025Q1`; otherwise prefer an exact quarter match, then the latest available quarter.
