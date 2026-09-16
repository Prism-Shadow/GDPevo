# PeopleOps Evidence Rules

These rules are derived from recurring PeopleOps reconciliation tasks. They are source-control heuristics, not fixed answers. Always defer to the current prompt, current records, and the exact `answer_template.json`.

## General Source Precedence

- Prefer structured, authoritative records over summaries. Assignment history, submitted payroll records, offer registers, cost ledgers, document folders, notice packets, policies, and scoped audit events outrank dashboard/case/profile summary prose when they conflict.
- Prefer current-period/effective-date records over stale records. If dates or periods differ, verify the requested period in the prompt.
- Prefer approved or submitted records over draft, superseded, worksheet, message-only, or case-summary-only records.
- Keep rejected records visible. Many templates ask for excluded leave IDs, payroll IDs, audit IDs, or blockers; fill these from records rejected due to draft, superseded, stale, incomplete, or adjacent-scope status.

## Leave and Employee Policy

- For effective leave setup, start with the employee profile only to identify the person and any possible conflict.
- Then inspect leave assignment history or payroll-ledger leave records, policy documents, and audit events.
- An approved/current leave assignment controls over a stale profile summary when ledger, policy, or audit evidence confirms it.
- Exclude draft leave assignments, superseded assignments, stale worksheet values, and audit events that discuss unrelated document/notice findings rather than leave source precedence.
- For annual/balance days, use the authoritative assignment/ledger/policy value requested by the template field name. Do not average profile and ledger values.

## Payroll Assignment and Accrual Readiness

- Use submitted payroll assignment records for salary, assignment ID, and effective date. Draft assignment records are evidence to exclude, not a source for final salary.
- If multiple submitted/superseded payroll records exist, select by requested period/effective date and status.
- For accrual readiness, look for a payroll/accrual batch record and a scoped audit event confirming readiness or blockers.
- Use payroll-specific audit scope labels for payroll assignment and accrual decisions; exclude leave or document/notice audit events from payroll-readiness fields.

## Policy Cases, Folder Readiness, and Formal Notices

- A final approval event establishes decision, authority, and approval ID, but it does not make a case ready to close when the folder or notice is defective.
- Folder readiness comes from document folder evidence: compare `required_files` with `files`, `required_tags` with `tags`, and inspect the folder `ready` flag.
- Notice quality comes from notice packet/message/notification evidence: use `quality`, `defects`, required action, and actual notice content when available.
- If required files or tags are missing, or a formal notice is defective, the control result should hold/block/reissue according to the enum labels available in the current template.
- Remediation owner/action fields should track the defect type: records/folder defects route to records remediation, notice defects route to notice reissue/remediation, and clean folders/notices require no action.

## Recruitment Reconciliation

- Use the recruitment workspace for candidate outcomes. Candidate tables, interview/committee decisions, offer register, notice packets, and cost ledger outrank case summary or messages alone.
- Selected candidates require selection evidence plus accepted offer evidence when the template asks for offer status or payroll handoff.
- Waitlisted and rejected arrays should contain candidate IDs only when the template requests IDs. Do not include names or explanatory strings in those arrays.
- Sum every recruiting campaign cost ledger amount for `recruitment_cost_total`; do not use a displayed subtotal unless it matches the ledger.
- Payroll handoff should be gated by accepted offer status and the assignment/precheck status required by the template. Draft payroll is not sufficient unless the template explicitly permits draft records.
- Notice follow-up should come from notice packet status, quality, defects, or required action. Follow-up for waitlisted and rejected candidates is separate because their required notice types differ.

## Audit Scope and Exclusions

- Determine the audit scope from what the field is deciding, not from nearby record order.
- Include supporting audit IDs that directly verify the requested decision.
- Exclude adjacent audit IDs when they belong to a different decision scope, such as document/notice findings near a leave-source task or leave-source findings near a payroll-readiness task.
- If the template has both `audit_event_id` and `supporting_audit_event_ids`, use the primary/scoped audit as `audit_event_id` and include it in the supporting list unless the prompt specifies otherwise.

## JSON Normalization

- Enum labels must be copied from the template exactly, including underscores and capitalization.
- Lists must be JSON arrays. For `list[string]`, use strings only; for `list[enum]`, use only allowed enum labels.
- Numeric salaries, balances, days, and totals should be numbers, not quoted strings.
- Booleans should be `true` or `false`, not `"yes"` or `"no"`.
- Return no markdown, comments, or provenance text unless the task explicitly asks for explanation.
