---
name: northstar-payer-ops
description: Resolve Northstar Health Plan payer-operations tasks against the shared task environment and return exact JSON outputs. Use for prior authorization, pharmacy appeal, peer-to-peer, claim repricing, payment-integrity, rate-schedule, and therapy margin queue prompts that provide an answer_template.json and Northstar environment access.
---

# Northstar Payer Ops

Use this skill to produce a single JSON answer for Northstar payer-operations tasks. The task prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` are the output contract.

## Core Workflow

1. Read the prompt, task context, and answer template before querying the environment.
2. Identify the target business object: case ID, appeal ID, claim ID, P2P case, or queue row IDs.
3. Use only the network environment named in the task. If the prompt shows a placeholder base URL, resolve it from the task's environment access note. Use the task-provided bearer token for SQL.
4. Query narrowly. Prefer target-specific business endpoints such as `GET /api/cases/{case_id}`. Use `POST /sql/query` with JSON body `{"sql": "..."}` only for tables and IDs needed by the target.
5. Do not list unrelated records, inspect task-environment source files, or infer from records outside the requested target and its linked records.
6. Fill exactly the keys required by the answer template. Respect enum choices, list ordering, null handling, date formats, and numeric precision from the template.
7. Return JSON only, with no markdown or narrative.

For field derivations, table relationships, formulas, and audit rules, read [references/northstar-payer-ops.md](references/northstar-payer-ops.md).

## Output Discipline

- Treat `answer_template.json` as authoritative when field names, enum values, ordering, or precision differ from intuition.
- Use environment records over local memo wording when the environment supplies structured facts, statuses, criteria, lines, rates, or finance rows.
- Use the task context for scope limits such as queue row IDs, reporting period, threshold definitions, and requested as-of date.
- Derive values from current target records; do not reuse values from examples or from unrelated cases.
- When a required value is absent, use the template's allowed null, empty list, status, or route rather than adding explanatory fields.
