# PeopleOps Console Reconciliation

Use this skill for Northwind PeopleOps Console tasks that ask for HR lifecycle evidence reconciliation and a JSON answer matching an `answer_template.json`.

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` first. The template controls every key, type, and normalized enum label.
2. Read `environment_access.md`, open the remote base URL listed there, and replace any prompt URL like `127.0.0.1:<port>` with that remote URL. Log in with the provided credentials if the UI asks.
3. Search exact IDs from the prompt first, then names if needed. Prefer authoritative workspace records over dashboard cards or case summaries.
4. Build a small evidence matrix before answering: source record, status, period/effective date, supporting audit event, and excluded nearby records.
5. Return only the JSON object. Do not include markdown, comments, explanations, extra keys, or labels outside the template.

## Useful Console/API Routes

The UI mirrors these review endpoints:

- `/api/cases?q=...` and `/api/cases/{case_id}`: case overview, approvals, attachments, comments, audit events, and policy references.
- `/api/employees?q=...`: employee profile summaries; useful context, but can be stale.
- `/api/payroll-ledgers?q=...`: leave assignments, salary assignments, payroll/accrual evidence, statuses, periods, salary, and batch IDs.
- `/api/recruitment?q=...`: candidates, committee decisions, offer register, cost ledger, notice packets, payroll precheck records, and sometimes audit IDs.
- `/api/documents?q=...`: folder readiness, required files, filed files, required tags, and current tags.
- `/api/messages?q=...`: formal notice body, status, quality, and defect labels.
- `/api/audit?q=...` and `/api/audit/{audit_id}`: scoped audit support for source-precedence, document/notice, and payroll-readiness findings.
- `/api/policies/{policy_id}`: source-precedence and gate rules referenced by cases.

## Source Precedence

- Policy documents and authoritative module records outrank dashboard metrics, employee profile summaries, comments, and case summaries.
- Employee profile summaries are context only when assignment history, ledgers, policies, and audit detail disagree with them.
- Leave setup: use the current-period approved or submitted leave assignment confirmed by leave ledger/policy/audit evidence. Exclude draft, superseded, voided, obsolete, or unrelated-period leave records. When confirmed assignment evidence conflicts with the profile summary, ignore the profile for the effective policy and days.
- Payroll setup: use the submitted salary/payroll assignment for salary, effective date, and accrual readiness. Exclude draft planning assignments and superseded records even if they are newer or have larger salary values.
- Onboarding closeout: verify both effective leave and submitted payroll setup. Approval is sufficient only when the authoritative records are clean and excluded records are non-authoritative.
- Remote-work or document-review cases: approval history does not override folder or notice defects. Folder readiness requires all required files and required tags. Formal notice quality comes from notice packet/message inspection and matching audit detail.
- Recruitment reconciliation: candidate outcomes come from committee decision plus offer register confirmation. Only an accepted offer can drive payroll handoff. Waitlisted and rejected candidates should not receive offer/payroll treatment. Sum every recruiting campaign cost ledger line for `recruitment_cost_total`.

## Audit Scope Rules

- Include only audit events tied to the target ID and the business scope requested by the template.
- Use `leave_source_precedence_only` for leave/profile/assignment precedence findings.
- Use `document_notice_findings_only` for folder checklist and formal notice quality findings.
- Use `payroll_assignment_readiness` for submitted salary assignment, accrual batch, or payroll readiness findings.
- Exclude adjacent audit events that are from a different case/opening/employee or from the wrong scope, even if they mention similar defects.
- If the template asks for both supporting and excluded audit IDs, include supporting IDs that decide the target scope and list nearby wrong-scope IDs separately.

## Output Conventions

- Use enum values exactly as allowed in the answer template; do not paraphrase normalized business labels.
- Keep booleans as `true`/`false`, numbers unquoted, and empty lists as `[]`.
- Arrays for candidate outcomes must contain candidate IDs only.
- Excluded-record fields should use the exact record IDs from the source module, not names or descriptions.
- Defect arrays should use the template's defect labels, usually matching notice or folder inspection labels.
- For dates, use the explicit source effective date when present; otherwise use the date portion of the authoritative assignment timestamp/period that establishes the effective state.
- For cost totals, add all relevant cost ledger amounts; do not use case-summary estimates.

## Common Pitfalls

- A newer draft does not outrank an older submitted or approved record.
- A case can be approved but still blocked by missing required files, missing tags, or defective formal notices.
- A notice can require action even when the related candidate/case decision is otherwise final.
- A broad audit search may surface plausible but unrelated events; scope and ID matching matter.
- Recruitment payroll handoff is not for every interviewed candidate; it follows accepted-offer rules and submitted handoff/precheck requirements.
- Do not infer final JSON labels from prose. Map the evidence back to the exact allowed labels in the template immediately before answering.
