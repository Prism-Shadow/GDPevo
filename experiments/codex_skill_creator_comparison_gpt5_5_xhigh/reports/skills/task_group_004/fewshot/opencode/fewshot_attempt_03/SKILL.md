---
name: apex-retention-ops
description: Use this skill whenever a task asks for JSON from the ApexCloud Retention Operations API, including renewal risk queues, retention action boards, QBR metrics packets, receivables and pipeline reviews, churn export validation, outreach rankings, A/R aging, billing snapshots, support/NPS/usage health, CRM opportunities, HR/event operations context, or ApexCloud policy codes. Trigger even when the user only mentions ApexCloud, customer success operations, QBR metrics, AR aging, churn exports, or a controlled-answer template.
---

# ApexCloud Retention Ops

Use this skill to solve ApexCloud Retention Operations tasks by fetching the allowed API/export data, reconciling source precedence, and returning the requested JSON only.

## Standard Workflow

1. Read the user prompt and any `input/payloads/answer_template.json`.
2. Identify the task family: renewal risk queue, retention action board, QBR metrics packet, receivables/pipeline operations review, or churn validation/outreach ranking.
3. Use the API base URL supplied in the prompt. If the prompt contains `<TASK_ENV_BASE_URL>`, substitute the task environment base URL available to the solver.
4. Prefer the bundled helper for deterministic extraction and shaping:

   ```bash
   python scripts/apex_ops.py \
     --prompt /path/to/input/prompt.txt \
     --template /path/to/input/payloads/answer_template.json \
     --base-url http://task-env:9004/
   ```

   Omit `--template` when there is no template. The script writes one JSON object to stdout.
5. Inspect the JSON before returning it. Verify top-level keys, enum values, sort order, and precision against the prompt/template.
6. Return only JSON. Do not include commentary, markdown fences, or intermediate calculations in the final answer.

## Source Rules

Read [references/apex_rules.md](references/apex_rules.md) when you need to reason manually or verify the script output. The most important conventions are:

- Current ARR comes from posted `/api/billing/snapshots` at the task as-of date; fall back to account profile ARR only when no snapshot exists.
- Clean support tickets exclude duplicates, spam, and cancelled tickets; count only `open` and `closed` tickets.
- SLA compliance is the percentage of clean tickets where both first-response and resolution SLA flags are true.
- A/R overdue balance uses only older buckets: `61_90 + 90_plus`.
- A/R rows link to CRM accounts by exact legal-name match, not aliases or similar names.
- Open expansion pipeline is summed from open opportunities with close dates inside the requested window.
- Currency uses two decimals, percentages use one decimal, scores/counts are integers, and probabilities use three decimals unless the prompt says otherwise.

## Helper Coverage

The helper script is intentionally portable: it uses only the Python standard library and API/export endpoints listed in the task environment. It can parse common prompt wording for:

- Account IDs, date ranges, months, as-of dates, and top-N requests.
- Retention-board follow-up calendars.
- Receivables follow-up due dates.
- QBR account, quarter months, and review due date.
- Churn candidate shortlists.

If parsing fails, do the same computation manually from the rules reference, then shape output with the template.

## Policy Codes

When the answer template asks for policy code fields, use the ApexCloud conventions inferred for this API:

- Risk model: `RS-6`
- ARR source: `REV-4`
- Support hygiene: `SUP-8`
- Action priority: `ACT-5`
- Board sort: `BORD-4`
- Exposure formula: `EXP-6`
- Calendar policy: `CAL-5`
- Receivable trigger: `RCP-7`
- CRM match: `CM-5`
- Pipeline window: `PW-6`
- Follow-up scope: `FS-4`
- Churn model protocol: `MOD-7`
- Churn probability scale: `PRB-4`
- Churn deployment rule: `DEP-5`
- Outreach mapping: `OUT-2`
