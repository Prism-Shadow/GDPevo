---
name: peopleops-console-reconciliation
description: >-
  Solve PeopleOps Console HR-lifecycle reconciliation tasks against the local
  JSON API (employees, cases, payroll/leave ledgers, recruitment, documents,
  messages/notices, audit events). Use this whenever a task asks you to verify an
  onboarding closeout, validate leave or payroll source precedence, review a case
  folder and formal notice, reconcile a recruitment outcome packet, or pick the
  controlling audit event for an employee/case/opening — i.e. any prompt that says
  "use the authoritative submitted/approved record not the draft", "fill in the
  answer template", references EMP-/CASE-/REQ-/PAY-/LA-/OFFER-/AUD- IDs, or wants
  normalized business labels rather than free text. Reach for it even when the
  prompt only describes the scenario without naming the console explicitly.
---

# PeopleOps Console Reconciliation

You are an HR ops controller working a "PeopleOps Console" task. The portal holds
**deliberately conflicting** records for the same fact (several leave records, draft
vs submitted payroll, several audit events per case). Your job is to pick the
**authoritative** record, list the **excluded** losers, apply the business rules,
and emit a JSON answer that matches the task's `answer_template.json` exactly.

The scoring is on the answer JSON, so two things matter equally: getting the
**right record/decision**, and reporting it with the template's **normalized enum
labels** (not free-text). Lists are **sets** of IDs.

## Standard operating procedure

1. **Read the task assets.** Read the prompt, then
   `input/payloads/answer_template.json` (or the path the prompt gives). The template
   is the contract: every key, the `type` of each field, and for `enum` fields the
   `allowed_values` you are permitted to emit. Plan to fill exactly those keys.
2. **Reach the API.** Read the task's `environment_access.md` for the base URL, then
   `GET /health` to confirm it is up. The web-UI login is not needed — call the JSON
   API directly with `curl -s`.
3. **Identify the task shape** from the prompt and follow the matching playbook in
   `references/playbooks.md`:
   - A — Onboarding closeout verification (leave + payroll for an employee)
   - B — Case folder + formal-notice review
   - C — Leave source-precedence validation for an employee
   - D — Payroll assignment + accrual readiness for an employee
   - E — Recruitment outcome reconciliation for an opening
   A task may combine shapes; run each relevant playbook and merge the fields.
4. **Pull only the named entity's records.** Look entities up by their specific IDs
   (`?q=<ID>`, the `/<id>` detail route, or `/api/audit?case_id=<CASE-ID>`). See the
   endpoint map and field shapes in `references/api.md`.
5. **Apply the business-judgment rules** in `references/rules.md` to select the
   authoritative record, compute exclusions, test folder readiness, detect notice
   defects, choose the controlling/supporting audit event, and apply the
   approval-vs-closeout gate.
6. **Assemble the JSON**, map every decision to the template's enum label, double-
   check every required key is present and typed correctly, then return only the
   JSON (no markdown, no commentary).

## The core mental model: precedence and exclusion

Almost every field is one of: "which record is authoritative?", "which records are
excluded?", or "what does that imply?". The precedence ladder (full detail in
`references/rules.md`):

- **Approved / Submitted** record of the correct type for the period → authoritative.
- **Employee profile summary** (`/api/employees` row) → convenience summary, can be
  stale, loses to an approved/submitted assignment.
- **Case summary** text → weakest, never authoritative alone.
- **Draft / Superseded / voided / obsolete** → always excluded, even if a profile
  summary agrees with them. Excluded-ID list fields collect every loser as a set.

For leave, the controlling row is the `record_type: "Leave assignment"` that is
Approved/Submitted — not an `HRMS leave ledger` or `People Ops adjustment` worksheet
row. For payroll, it is the `Submitted` `Salary assignment`; the `Draft` is excluded.

## Reading the authoritative answer from records (not guessing)

- **Audit `detail` text is authoritative** for result labels and for which record
  won. It often literally says "QA result: <label>. <record> controls/matches ...".
  Read the label and map it to the template enum; don't infer a different one.
- **Notice quality lives in the notice/message packet** (`quality` + `defects[]`),
  not in the case summary. Copy the defect codes verbatim.
- **Folder readiness is a set comparison** of `required_files`/`required_tags`
  against `files`/`tags`; the folder-checklist attachment and `folder.tag_missing`
  audit just restate the gaps.
- **Escalation owner / SLA** must be read verbatim from the named audit package's
  `detail` (or its linked policy). Never invent a number or reuse one from another
  task — each package has its own.

## Output conventions

- The JSON must match `answer_template.json` **exactly**: same keys, correct types
  (`string`/`integer`/`number`/`boolean`/`list[...]`/`enum`).
- For `enum` and `list[enum]` fields, emit only a value from that field's
  `allowed_values`. These normalized labels (defect codes, gate labels, status,
  scope, source, result, action labels) are the output contract — prefer them over
  any free-text reasoning.
- List fields are **sets**: include every member, no duplicates; order is not
  meaningful but include each ID once. Array fields like candidate lists contain IDs
  only.
- Numbers are raw numbers (e.g. a `2026-04` period implies an `effective_date` of
  `2026-04-01`; a cost total is the arithmetic sum of every cost-ledger line).
- Return only the JSON object — no markdown fences, no explanation — when the prompt
  says so.

## Common pitfalls

- **Using a draft or superseded record because it is newest.** Recency does not beat
  approval/submission; drafts are excluded and go in the excluded list.
- **Treating a worksheet/adjustment leave row as the entitlement.** Only the
  `Leave assignment` record type is the controlling leave source.
- **Trusting the profile summary.** It can carry a stale policy even when its balance
  looks right; the approved assignment still controls and
  `profile_policy_ignored` is true.
- **Deciding notice quality or candidate outcome from the case summary.** Use the
  notice packet and the committee decision + offer respectively.
- **Including off-scope audit events in a scoped decision.** A `folder.*`/`notice.*`
  event is excluded from a leave/payroll-precedence decision (and vice versa); put it
  in `excluded_audit_event_ids`.
- **Letting an approval imply closeout.** Approval is sufficient only when records are
  clean; a defective folder or notice forces a hold.
- **Free-text enum values.** If your label is not in `allowed_values`, it is wrong —
  map it to the closest allowed normalized label.
- **Enumerating collections to "explore".** Query only the named entity's records;
  unfiltered list browsing is out of scope.

## References

- `references/api.md` — endpoint map, scope discipline, and field shapes.
- `references/rules.md` — the full source-precedence, folder, notice, audit, gate,
  recruitment, and escalation rules with the normalized vocabularies.
- `references/playbooks.md` — step-by-step query sequences per task shape.
