---
name: peopleops-console-review
description: >-
  Use this skill whenever a task asks you to review, verify, reconcile, or
  validate something in an HR "PeopleOps Console" / People Ops lifecycle portal
  exposed as a JSON API — for example onboarding closeout, leave source
  precedence, payroll/accrual readiness, policy-case folder and formal-notice
  review, recruitment outcome reconciliation, or audit-scope selection. Trigger
  it any time the prompt names a PeopleOps Console, an employee/case/opening/
  payroll-ledger/leave-assignment/audit record, and asks for a JSON answer that
  must use normalized business labels from an answer_template.json. It encodes
  the standard operating procedure: which endpoints to query, the
  source-precedence and gating rules, the notice-defect vocabulary, and how to
  produce output that exactly matches the template's enum contract.
---

# PeopleOps Console Review

This skill answers HR lifecycle-governance tasks against a running **PeopleOps
Console** JSON API. Tasks fall into a small number of recurring shapes (leave
precedence, payroll/accrual readiness, folder + notice review, recruitment
reconciliation, audit-scope selection), all of which share the same data model,
the same source-precedence philosophy, and the same output contract: **a single
JSON object whose keys and enum values exactly match the provided
`answer_template.json`.**

Your answer is graded field-by-field against a gold answer. Two things decide
whether you pass: (1) picking the **authoritative** record and excluding the
losing ones, and (2) emitting the **exact normalized enum label** the template
allows — never free text, never a synonym you invented.

## Golden rules (read first)

1. **The answer template is the contract.** Open the task's
   `answer_template.json` before doing anything else. Every output key must be
   present, types must match (`integer` vs `number`, `boolean`, `string`,
   `list[string]`, `list[enum]`), and every `enum` / `list[enum]` field must use
   one of its `allowed_values` verbatim. Do not add keys, omit keys, or
   substitute free-text explanations for enum labels.
2. **Authoritative records win; drafts and stale records lose — and you must
   name the losers.** Most fields come in pairs: a "selected/effective" value
   and an "excluded_*" list. The exclusion lists are graded too. Always identify
   *both* the winner and the records it beat.
3. **Read controlling facts verbatim from the source of record.** Normalized
   result/owner/SLA values (e.g. an audit `detail` string, a folder checklist,
   a notice packet's defect list, a policy clause) are stated in the data. Read
   them; do not guess. The audit `detail` text typically spells out the QA
   result that maps directly to a control-result enum.
4. **Stay on scope.** Audit-scope tasks require you to keep the controlling
   event(s) and *exclude* adjacent off-topic audit events. A leave-precedence
   decision excludes document/notice events; a document/notice decision excludes
   leave/payroll events.
5. **Lists are sets.** Order does not matter, but membership does. Include every
   item that belongs and nothing that does not.

## Environment

Read the task's `environment_access.md` for the base URL (a local host:port) and
verify the service first:

```
GET /health            -> {"ok": true, ...}
```

All endpoints are GET and need no auth (login credentials in the prompt are for
the web UI only — use the API directly). The `q` parameter is a case-insensitive
substring match against any scalar field on that resource.

| Endpoint | Use it for |
|---|---|
| `GET /api/manifest`, `GET /api/summary` | module/dataset overview, counts |
| `GET /api/employees?q=&status=` | employee profile (incl. `leave_balance_days`) |
| `GET /api/cases?q=&status=&type=` | case summaries |
| `GET /api/cases/<id>` | full case: `approvals`, `attachments`, `comments`, `audit_events`, `policy_refs` |
| `GET /api/policies?q=` / `/api/policies/<id>` | the business rules in prose (precedence, gates) |
| `GET /api/payroll-ledgers?q=&status=&type=` | **both** leave assignments and salary assignments live here |
| `GET /api/recruitment?q=` | opening: `candidates`, `offer_register`, `cost_ledger`, `notice_packets`, `payroll_precheck_records` |
| `GET /api/documents?q=` | folders: `required_files`, `files`, `required_tags`, `tags`, `ready` |
| `GET /api/messages?q=` | formal-notice messages with `quality` and `defects` |
| `GET /api/notifications?q=` | notification records |
| `GET /api/audit?q=&case_id=` / `/api/audit/<id>` | audit events: `event`, `detail`, `case_id`, `employee_id` |
| `GET /api/attachments/<id>` | raw attachment text |

**Lookup discipline.** Query by the specific IDs/names in the prompt (and the
records directly linked to them). Filter with `q=`, `case_id=`, `status=`, or a
detail endpoint. Do not page through entire collections to browse unrelated
entities — it is unnecessary and slows you down.

**Important quirk:** the `payroll-ledgers` endpoint holds *every* ledger row for
an entity, distinguished by a `record_type` field — leave assignments, salary
assignments, HRMS ledgers, People-Ops adjustments, etc. A `q=` on the numeric
part of an employee id returns all of them. Filter by `record_type` and `status`
yourself; do not assume one row.

## Standard operating procedure

1. **Parse the template** — list the output keys and, for each enum field, its
   allowed labels. This tells you exactly what evidence you must go find.
2. **Identify the subject** — employee id, case id, or opening id from the prompt.
3. **Pull the candidate records** for that subject from the relevant endpoint(s).
4. **Apply source precedence** to pick the authoritative record(s) and build the
   exclusion list(s). (See "Source precedence" below.)
5. **Read controlling text** — the audit `detail`, folder checklist, notice
   packet, and any referenced policy clause — and map it to the normalized enum
   labels. The policy documents (`/api/policies`) often state the exact rule in
   words; use them to justify your label choices.
6. **Apply the gate / scope rules** for the task shape (see task-shape table).
7. **Assemble JSON** matching the template exactly; double-check enum spellings
   and that every `excluded_*` / `missing_*` / `*_followup_*` list is complete.

For the detailed per-shape playbooks, decision tables, and the full mapping from
evidence to each enum label, read **`references/playbooks.md`**. For the precise
field-by-field reasoning that distinguishes winners from losers, read
**`references/field-rules.md`**. Consult them whenever a field's correct value
is not obvious from the data alone.

## Source precedence (the core judgment)

The console deliberately seeds conflicting records so you must apply precedence.
The governing principle, stated in the leave/payroll source policies, is:
**the latest approved or submitted record for the relevant period controls;
draft, voided, superseded, and obsolete records are excluded even when a profile
summary or case summary conflicts.**

- **Leave:** prefer the row whose `record_type` is the formal *leave assignment*
  and whose `status` is `Approved` (or `Submitted`) for the current period.
  Exclude `Superseded` and `Draft` assignment rows. An approved leave assignment
  **overrides a stale employee-profile summary** — when it does, mark the profile
  as ignored/stale and route the follow-up to update the summary. Do not pick
  HRMS-ledger or People-Ops-adjustment rows when a proper leave *assignment*
  exists; they are not the entitlement source.
- **Payroll/salary:** prefer the `Submitted` salary assignment for the period.
  Exclude `Draft` planning assignments (and `Superseded` ones). Draft prechecks
  never satisfy a readiness or accrual gate.
- **Recruitment outcomes:** the committee decision plus the offer register
  control — not a message status or a case summary. An offer must show an
  `accepted` status to count as accepted.

Take the policy text and audit `detail` as the tie-breakers; they state which
source is authoritative for the period.

## Folder readiness, notice defects, audit scope, gating

These four mechanics recur across the document/notice and closeout tasks:

- **Folder readiness = set comparison.** A folder is ready only if
  `required_files ⊆ files` **and** `required_tags ⊆ tags`. `missing_files` is the
  set difference `required_files \ files` (use the exact filenames from the
  checklist). `required_tag_present` is whether `required_tags ⊆ tags`. The
  folder's own `ready` flag should corroborate your set comparison.
- **Notice quality + defects.** Inspect the formal-notice packet/message (its
  `quality` and `defects` fields, corroborated by the audit `detail`), not the
  case summary. A notice is `defective` if it lists any defect. Emit defect codes
  only from the template's normalized vocabulary — these are the only allowed
  values and they are part of the output contract:
  `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`.
- **Audit scope.** Pick the controlling/supporting event(s) whose `event`/
  `detail` matches the task's subject, and put every adjacent off-scope event in
  `excluded_audit_event_ids`. Map the subject to the scope label the template
  offers (e.g. leave-precedence vs document/notice vs payroll-readiness scope).
  An empty exclusion list is correct when there is no off-scope event.
- **Approval-vs-closeout gating.** An approval (even "approved with conditions")
  authorizes the decision but does **not** by itself authorize closeout. The gate
  is: *approval is sufficient only when records are clean*; if the folder is
  incomplete or a notice is defective, approval is **not** sufficient — hold and
  remediate. When records are clean and an approval exists, closeout proceeds.

See `references/field-rules.md` for how these feed the `*_gate`,
`closeout_blockers`, `escalation_action`, remediation-owner, and
`final_control_result` fields, and how to read an escalation package's owner/SLA
verbatim from its detail text.

## Output conventions

- Emit exactly one JSON object, no markdown, no commentary, matching every key
  in `answer_template.json`.
- `enum` / `list[enum]` fields use an `allowed_values` label **verbatim**.
- Respect numeric types: `integer` where the template says integer, `number`
  (which may be a float) where it says number. Salary/cost are numbers; day
  counts are usually integers — but read the actual value, since adjustment rows
  can be fractional.
- `recruitment_cost_total` is the **sum of all cost-ledger line amounts**, read
  from the cost ledger (not a case summary).
- Boolean fields (`folder_ready`, `required_tag_present`, `accrual_ready`,
  `profile_policy_ignored`, `draft_payroll_allowed`) are real `true`/`false`.
- List fields are sets — complete and free of off-scope members.

## Common pitfalls

- Picking a `Draft` or `Superseded` row because it is newest or has a bigger
  number. Status precedence beats recency-of-edit.
- Forgetting to populate `excluded_*` lists — they are graded.
- Choosing an HRMS-ledger / adjustment row over the formal leave *assignment*.
- Reading notice quality or candidate outcome from the case summary instead of
  the notice packet / committee decision + offer register.
- Letting an approval auto-approve closeout while a folder or notice is defective.
- Leaking off-scope audit events into the scope decision.
- Emitting free-text or a near-synonym instead of the template's exact enum label.
