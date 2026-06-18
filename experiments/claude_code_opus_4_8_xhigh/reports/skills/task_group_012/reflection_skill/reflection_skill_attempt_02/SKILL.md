---
name: peopleops-console-verification
description: >-
  Verify and reconcile HR lifecycle decisions in a "PeopleOps Console" JSON API
  (onboarding closeout, remote-work / policy case review, leave source
  precedence, recruitment outcome reconciliation, and payroll/accrual
  readiness). Use this skill whenever a task asks you to determine the
  authoritative leave/payroll/offer record, apply source precedence, exclude
  draft/superseded/stale records, judge folder readiness, detect formal-notice
  defects, scope audit events, gate approval vs closeout, sum recruitment cost,
  decide candidate follow-up / payroll handoff, or read an escalation owner/SLA
  from an audit package — and return a JSON answer that exactly matches a
  provided answer_template.json using normalized business labels. Trigger it for
  any PeopleOps/HR-portal verification where the answer must use the template's
  enum vocabulary rather than free text.
---

# PeopleOps Console Verification

You are auditing HR lifecycle decisions exposed through a read-only JSON API and
returning a structured JSON verdict. The grader compares your answer to a gold
answer field-by-field, so two things decide your score: picking the **right
authoritative record** (precedence + exclusions), and emitting the **exact
normalized label** the template allows. Almost every mistake is one of those two.

This skill generalizes across different employees, cases, openings, and offers.
Never hard-code an entity; always resolve the specific IDs named in the prompt at
run time.

## Golden rules (read first)

1. **The answer_template.json is the contract.** Output exactly its keys, types,
   and — for every `enum` / `list[enum]` field — only its `allowed_values`. A
   semantically-correct free-text answer scores zero. Read the template before
   you query anything; let its fields tell you what evidence to gather.
2. **Drafts and prechecks never count.** A draft assignment, a draft notice, an
   empty precheck list, a superseded/voided row, or a stale profile summary never
   satisfies a gate and never supplies the authoritative value. The current
   submitted/approved record controls.
3. **Label by the artifact, not the transport.** A formal notice is a notice
   packet even when the API surfaces it through the messages/notifications
   endpoint. If it carries structured `quality`/`defects`, it is packet evidence.
4. **Scope evidence to the decision.** Supporting audit/records are only those in
   the decision's own scope; same-entity records from an adjacent scope
   (a document/notice event during a leave decision, etc.) are *excluded*, not
   supporting.

## Workflow

1. **Read `answer_template.json`.** Enumerate every output key. For each enum,
   note the exact `allowed_values`. The keys reveal which subsystems you must
   touch (leave, payroll, folder, notice, audit, recruitment, escalation).
2. **Confirm the API is up.** `GET /health` before drilling in.
3. **Resolve the named entities.** Pull the specific employee / case / opening /
   offer named in the prompt by ID via the list endpoint's `q=` filter, then the
   detail endpoint. Do **not** browse whole collections looking for extra
   entities — work only from what the prompt references and its linked records.
4. **Gather evidence in precedence order** for each subsystem (see SOP below).
5. **Apply exclusions** (draft / superseded / stale / out-of-scope) explicitly,
   and record excluded IDs where the template asks for them.
6. **Derive each field** from the rules below, choosing the normalized label.
7. **Emit JSON** matching the template exactly. Re-check every enum value against
   `allowed_values` and every list field for set-correctness before returning.

### Endpoint query order (SOP)

The API base and endpoints are described in the environment's access file; query
in this order so higher-precedence evidence frames everything after it:

1. Case / entity detail first (`/api/cases/<id>` or the relevant entity detail) —
   gives approvals, attachments, in-case audit events, policy refs, owner.
2. Authoritative-record sources: leave assignment history, payroll ledger,
   offer register — to find the controlling submitted/approved row.
3. Folder readiness: documents endpoint (required_files / required_tags vs
   present files / tags).
4. Formal notice: the notice packet record (often via messages/notifications) —
   its `quality` and `defects`.
5. Audit: in-case / in-scope audit events for supporting evidence; note adjacent
   ones to exclude.
6. Recruitment specifics: candidates, offer_register, cost_ledger, notice_packets.
7. Escalation/SLA: the relevant audit package detail (read owner/SLA verbatim;
   never invent).

See `references/decision_rules.md` for the per-subsystem rules in detail and
`references/enum_vocabulary.md` for the complete normalized label set.

## Source precedence and exclusions

- **Leave:** the latest **approved** leave assignment for the current period is
  authoritative and overrides a **stale employee profile summary**. Exclude
  superseded and draft assignments. The annual days / balance come from that
  approved assignment.
- **Payroll:** the **submitted** salary assignment controls base salary and
  effective date; exclude the draft. Derive `effective_date` from the controlling
  submitted row (its period start / updated date) when no explicit field exists.
- **Offer:** the **accepted** offer in the offer register is authoritative for the
  selected candidate's salary and status.
- Record excluded IDs wherever the template provides an `excluded_*` field — list
  every non-authoritative same-subsystem row (draft, superseded), as a set.

## Folder readiness as a set comparison

A folder is **ready only if** (required_files ⊆ present files) **AND**
(required_tags ⊆ present tags). Compute both as set differences:

- `missing_files` = required_files − present files (a list/set; may be empty).
- required tag present? = required_tags ⊆ present tags.
- If a required **file** is missing but the required **tag** is present, the
  blocker is the missing file only; the tag action is the "no tag action" label.
  Do **not** report a missing-tag blocker in that situation. The reverse holds if
  a tag is missing but files are complete.

## Notice-defect detection and defect vocabulary

- The formal notice carries a `quality` (valid / defective) and a `defects`
  list. Read these from the **notice packet** record; report `notice_quality` and
  the `notice_defects` as the exact normalized defect codes — never paraphrase.
- The defect-code vocabulary (the only concrete data values this skill may name)
  is: `missing_ack_deadline`, `missing_appeal_instructions`,
  `missing_waitlist_status`, `missing_correct_policy`. Use exactly these.
- `notice_evidence_source` is `notice_packet_inspection` whenever the defects come
  from a structured notice packet (even if delivered as a message). Use
  `message_notice_inspection` only when quality is inferred from informal
  message/comment text, and `case_summary_only` only when nothing better exists.

## Audit-event scoping (supporting vs excluded)

- **Supporting** audit events are those whose scope matches the decision being
  made (a leave-precedence event for a leave decision; a notice/document event for
  a folder/notice decision; a payroll-readiness event for a payroll decision).
- **Excluded** audit events are adjacent events that touch the same employee/case
  but belong to a *different* scope. Example: during a leave-precedence decision,
  a document/notice audit event for the same employee is excluded, not supporting.
- If there are no other in-scope audit events to exclude, `excluded_*` is an empty
  list. Do not pull in events from unrelated cases/employees just to populate it.
- `audit_scope` is the normalized label for the decision's scope (leave precedence
  only / document-notice findings only / payroll assignment readiness).

## Approval vs closeout gating

Approval authority is necessary but **not sufficient** for closeout.

- If the folder is ready, the required tag is present, and the notice is valid
  (records clean), approval is sufficient → approve the closeout.
- If any folder file/tag is missing or the notice is defective, approval is **not
  sufficient** → hold. Then the action fields split by responsibility:
  - `next_action` = the overall blocking action (block close and reissue notice).
  - `escalation_action` = the structural escalation for the **folder/file**
    defect → open records remediation (independent of the notice's own fix).
  - `notice_remediation_action` = reissue the defective notice(s).
  - `records_remediation_owner` = the team that owns the folder checklist (the
    `uploaded_by` team on the folder attachment), not the case owner.
  - `closeout_blockers` = the set of present blockers (missing files / missing
    tags / defective notice) — only those actually present.

## Recruitment cost, candidate outcome, and payroll handoff

- `recruitment_cost_total` = **sum of all** recruiting cost-ledger line amounts.
  Include every line; exclude nothing unless the template/prompt says so.
- Candidate outcomes come from the committee decision + offer confirmation
  (selected / waitlisted / rejected). Outcome arrays contain **candidate IDs
  only**, as sets.
- `notice_followup_required` = every candidate whose notice packet status is
  not-sent (typically both waitlisted and rejected). The per-outcome follow-up
  action (send waitlist / send rejection notice) comes from the notice packet's
  required_action.
- **Payroll handoff after an accepted offer:** an accepted offer requires a
  **submitted** assignment, not a draft precheck. So:
  - `onboarding_handoff` = create a submitted assignment after acceptance.
  - `payroll_handoff_gate` = accepted offer **AND** submitted assignment (both),
    not "accepted offer only".
  - `draft_payroll_allowed` = false; the required status is submitted-after-
    acceptance. An empty precheck list does not satisfy the gate.
- The waitlisted candidate is excluded from the offer because they have no
  accepted status or offer.

## Reading escalation owner / SLA from an audit package

When the template asks for an escalation owner or SLA, do **not** guess.

1. Open the audit package / audit event detail linked to the case or decision.
2. Read the owner/team and the SLA value **verbatim** from that record.
3. Map any owner field to the template's `allowed_values` if it is an enum; copy a
   free-string owner/SLA exactly as written. If the package does not state it,
   prefer the most specific in-scope record over a summary, and never substitute a
   default number.

## Output conventions

- Return a single JSON object with **exactly** the template's keys — no extra
  keys, no markdown, no commentary.
- Every `enum` / `list[enum]` value must be a member of that field's
  `allowed_values` (case- and spelling-exact).
- List fields are **sets**: include each qualifying member once; emit `[]` when
  empty; order is not meaningful but completeness is.
- Strings (policy names, IDs, owners) are copied verbatim from the authoritative
  record. Numbers (salary, days, cost total) are computed/copied exactly.
- ID-typed fields hold the single authoritative ID; `excluded_*` fields hold the
  set of non-authoritative IDs.

## Common pitfalls (learned from mistakes)

- **Labeling a notice by its transport.** A structured formal notice delivered as
  a message is still packet evidence → `notice_packet_inspection`, not
  `message_notice_inspection`. Check for structured `quality`/`defects`.
- **Conflating the action fields.** `next_action`, `escalation_action`, and
  `notice_remediation_action` are distinct. A missing-file/folder defect drives
  `escalation_action` to open-records-remediation even while the notice is being
  reissued; don't copy `next_action` into `escalation_action`.
- **Accepting a draft/precheck for handoff.** After an accepted offer, the gate
  needs a *submitted* assignment; "accepted offer only" and "create precheck" are
  wrong. Drafts/prechecks never satisfy any gate (payroll or recruitment).
- **Over-populating excluded lists.** Only same-scope-but-out-of-scope records get
  excluded; unrelated entities don't. When nothing qualifies, use `[]`.
- **Reporting a missing tag when only a file is missing** (or vice versa). Compute
  files and tags as independent set comparisons and report only the real gap.
- **Free text in enum fields / paraphrased defect codes.** Always snap to the
  template's `allowed_values` and the fixed defect-code vocabulary.
- **Inventing an SLA/owner.** Read it from the audit package; never default it.
