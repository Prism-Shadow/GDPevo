---
name: peopleops-evidence-reconciliation
description: Solve PeopleOps Console reconciliation and control-review tasks that require producing exact JSON from a provided answer_template.json. Use when the task asks Codex to verify onboarding closeout, leave source precedence, payroll assignment/accrual readiness, remote-work or lifecycle case folder readiness, formal notice defects, recruitment outcomes, audit scope, excluded records, normalized business labels, or final People Ops control actions.
---

# PeopleOps Evidence Reconciliation

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before inspecting data. Treat the template as the output contract: include exactly those keys, preserve key names, use only listed enum labels, and emit JSON only.
2. Get the task environment base URL from the prompt or local environment-access file. Use only allowed read endpoints unless the prompt explicitly asks for a permitted write such as posting a case comment.
3. Prefer API evidence over visual browsing when available. The UI can help orient navigation, but the API is easier to search, join, and verify.
4. Build a small evidence table for each requested field: selected value, source endpoint, source record id, excluded adjacent records, and reason. Do not rely on case summaries alone when the prompt asks for authoritative records, submitted records, assignment history, formal notices, folders, policies, ledgers, audit details, or messages.
5. Validate the final object against the template, then return only the JSON object. Do not include markdown, citations, explanations, or fields not present in the template.

## Useful Helpers

- `scripts/fetch_peopleops_context.py` fetches allowed PeopleOps API endpoints and optionally searches them for employee ids, case ids, opening ids, candidate ids, names, or record ids.
- `scripts/validate_answer.py` checks a draft JSON answer against the local answer template for exact keys, scalar/list types, and enum labels.

Example commands:

```bash
python skill/scripts/fetch_peopleops_context.py --base-url "$TASK_ENV_BASE_URL" --query EMP-123 --query CASE-123 --out /tmp/peopleops_context.json
python skill/scripts/validate_answer.py input/payloads/answer_template.json /tmp/answer.json
```

If `TASK_ENV_BASE_URL` is not set, read it from the task prompt or environment-access file and pass it directly with `--base-url`.

## Evidence Sources

Fetch the broad endpoints first to learn what is available:

- `/api/manifest` and `/api/summary` for module inventory and record counts.
- `/api/employees` for profile summaries. Profile leave or salary fields are not authoritative when assignment records conflict.
- `/api/cases` and `/api/cases/{case_id}` for case metadata, approvals, attachments, comments, and case-scoped audit events.
- `/api/policies` and `/api/policies/{policy_id}` for source-precedence, payroll, remote-work, and folder rules.
- `/api/payroll-ledgers` for leave assignments, salary assignments, payroll worksheets, accrual batches, and related statuses.
- `/api/recruitment` for candidates, committee outcomes, offer register, cost ledger, notice packets, and payroll precheck records.
- `/api/documents` for folder readiness, required files, present files, required tags, and present tags.
- `/api/messages` and `/api/notifications` for notice quality and communication evidence.
- `/api/audit` and `/api/audit/{audit_id}` for control conclusions and scope-specific support.
- `/api/attachments/{attachment_id}` when a case detail points to an attachment whose content is needed.

Join records by the strongest identifier in the prompt: `employee_id`, `case_id`, `opening_id`, `candidate_id`, assignment id, audit id, document id, or offer id. When the prompt names a person, use `/api/employees` or case/recruitment records to map the name to an id before joining other modules.

## Precedence Rules

Leave:

- Use the latest current-period leave assignment whose status is approved or submitted when policy, ledger, or audit evidence confirms it.
- Ignore employee profile summaries when they are stale or contradicted by approved/submitted assignment history.
- Exclude draft, voided, obsolete, superseded, older-period, or otherwise non-current leave assignment records.
- Use leave-scope audit events for leave precedence. Exclude adjacent folder, notice, payroll, or cross-module audits from leave-scope fields unless the template asks for those scopes separately.

Payroll and accrual:

- Use the current submitted salary assignment for base salary, effective date, payroll assignment id, and payroll source status.
- Exclude draft planning assignments and superseded assignments from current payroll readiness.
- Verify accrual readiness by matching submitted assignment evidence to payroll worksheet/accrual batch records and payroll-readiness audit events.
- Use payroll-scope audit events for payroll readiness. Do not let folder or notice defects change a payroll assignment field, though they may affect final closeout/control fields when the template asks for them.

Case folder and formal notice:

- Approval history establishes decision and authority, but approval alone is not enough for closeout when folder or notice checks fail.
- A folder is ready only when all required files and required tags in the document checklist are present.
- Inspect formal notice evidence from notice packets, messages, notifications, attachments, and document/audit findings. Record defects such as missing appeal instructions, missing acknowledgement deadline, missing waitlist status, missing correct policy, or missing required files/tags using the template's enum labels.
- Use document/notice-scope audits for folder and notice findings. Exclude leave or payroll audits from document/notice decisions.
- If folder or notice defects are present, the closeout gate generally becomes the defect/blocking label from the template, and the next action should remediate records or reissue notices using the template's allowed labels.

Recruitment:

- Determine selected, waitlisted, and rejected candidates from committee decisions plus accepted offer evidence, not from messages alone.
- The selected candidate must have an accepted offer when the template asks for selected offer status or payroll handoff gating.
- Sum every recruitment cost ledger line for `recruitment_cost_total`; return it as a number.
- Notice follow-up arrays should contain candidate ids only. Add candidates whose notice packet or message evidence requires follow-up.
- Payroll handoff is gated by accepted offer evidence and any submitted-after-acceptance requirement in policy or the template. Draft prechecks or assignments do not satisfy a submitted handoff gate.

Audit scope:

- Separate support from exclusion. Put audit ids in supporting fields only when their event and detail address the requested business scope.
- Put adjacent but out-of-scope audit ids in excluded fields when the prompt asks for exclusions.
- A cross-module audit package can identify related evidence, but each related audit still needs to be assigned to the correct leave, payroll, document/notice, recruitment, or closeout scope.

## Output Discipline

- Start from the template keys, not from the data shape. Every final key must appear exactly once.
- Use allowed enum strings exactly as written in the template. Do not paraphrase normalized business labels.
- Keep ids as strings, booleans as booleans, and numeric money/day fields as numbers, not quoted strings.
- Use empty arrays when the template expects a list and no qualifying records exist.
- For list fields that request candidate ids, record ids, missing files, defects, blockers, supporting audits, or excluded audits, include only the requested item type.
- Before final response, run `scripts/validate_answer.py` or manually perform the same checks: exact keys, no extras, all enum values allowed, no draft/superseded records selected as authoritative, and no markdown wrapper.
