---
name: peopleops-console-review
description: >-
  Resolve PeopleOps Console (HR lifecycle portal) review tasks over its JSON
  API: onboarding closeout, leave source-precedence, payroll/accrual readiness,
  remote-work folder and formal-notice review, and recruitment outcome
  reconciliation. Use this whenever a task asks you to verify, validate,
  reconcile, or review an HR employee / case / opening / offer and return a
  structured JSON answer with normalized business labels (gate / source / scope
  / status / result / defect-code enums) matching an answer_template.json.
  Trigger even if the prompt only says "review this case", "check leave
  precedence", "reconcile recruitment", or "is this ready to close" without
  naming the portal explicitly.
---

# PeopleOps Console review

You answer governance/control questions about an HR lifecycle portal by reading
its JSON API and emitting one JSON object whose keys and enum values exactly
match a provided `answer_template.json`. The hard part is never finding the data
— it is choosing the correct normalized label and excluding the records that
look authoritative but are not. This skill encodes those decision rules.

## How to read this skill

The body below is the full operating procedure. For the exact enum vocabulary
(every allowed label, grouped by field family) and worked decision walk-throughs,
read `references/decision-rules.md` when you need to confirm a label choice or
resolve an ambiguous field. Read it whenever you are unsure which of two
similar-sounding labels applies — that is where most mistakes happen.

## Standard operating procedure (endpoint query order)

The API serves everything as JSON; interact only over HTTP at the base URL given
in the environment access doc. `q` is a case-insensitive substring filter over
any scalar field; list endpoints with no params return all rows.

1. Parse the prompt: identify the principal entity (employee, case, opening, or
   offer) by its specific ID, and note which record classes the task mentions
   (leave, payroll, folder, notice, recruitment, audit, policy).
2. Resolve the principal: hit the matching list endpoint with `?q=<id>`, then the
   detail endpoint for the full record (comments, attachments, approvals,
   audit_events).
3. Pull each linked record class the task references — only those, by the IDs you
   already have. Do not browse whole collections hunting for unrelated entities;
   the answer is built from the named entity and its directly-linked records.
4. Read the governing policy doc(s) referenced by the case for owner / scope /
   readiness rules.
5. Read the relevant audit event detail LAST. The audit `detail` string very
   often names the controlling record and states the normalized result label
   verbatim — treat it as the tie-breaker, not the starting point.

## Source precedence and exclusion rules

Most fields hinge on picking the one authoritative record among look-alikes and
listing the rest as excluded. The trap is a Draft or later-period row carrying a
higher salary or more leave days — bigger numbers are bait, not authority.

- Leave: the latest APPROVED (or submitted) leave assignment for the effective
  period controls. Exclude Draft, Superseded / obsolete, and Voided rows. When an
  approved assignment plus the audit contradict the employee profile summary, the
  approved assignment wins and the profile policy is ignored.
- Payroll: the SUBMITTED salary assignment controls. Exclude Draft planning rows
  (commonly a later period and a higher salary). Superseded rows are also
  excluded.
- "Excluded IDs" list fields = the set of same-class records you dropped. Return
  them as a set (no duplicates; order not significant).
- If the audit detail explicitly names a controlling assignment ID, that ID is
  authoritative even when other rows look plausible — the other rows are
  distractors.

## Folder readiness as set comparison

A document folder is ready only when it is complete on BOTH dimensions:

```
folder_ready == (required_files ⊆ present_files) AND (required_tags ⊆ present_tags)
missing_files = required_files − present_files          (return as a set)
```

- If a required tag is missing: the tag action is "add the required tag" and a
  "missing required tags" closeout blocker applies.
- If all required tags are present: the tag action is "no tag action".
- Never mark a folder ready on partial file presence; a single missing required
  file makes it not ready.

## Notice-defect detection and the defect-code vocabulary

A formal notice is a STRUCTURED record carrying a `quality` field
(valid / defective) and a `defects[]` list of fixed codes. Read those fields
directly and copy the codes verbatim — do not paraphrase.

The notice defect codes are exactly:

- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

Choosing the notice EVIDENCE-SOURCE label is by the SHAPE of the evidence, not by
which endpoint physically stores it:

- A structured notice record (has `quality` + `defects[]`) ⇒ the evidence source
  is notice-PACKET inspection, even if that record is served from the
  messages / notifications endpoint rather than a recruitment notice block.
- Choose the "message notice inspection" label ONLY when all you have is a
  free-text message body with no structured notice record. It is a distractor in
  the common case where a structured notice exists.
- "case summary only" is for when neither a packet nor a message notice exists.

## Audit-event scoping (supporting vs excluded)

Scope membership is decided by the audit event's TOPIC, not by whether it shares
the same case or employee. A single case often carries audit events from several
topics; include only the on-topic ones.

- Leave events (e.g. leave / profile-mismatch topics) ⇒ leave_source_precedence
  scope.
- Folder / notice / document events ⇒ document_notice_findings scope.
- Payroll events ⇒ payroll_assignment_readiness scope.
- `supporting_audit_event_ids` = the in-scope events. `excluded_audit_event_ids`
  = adjacent same-case events of a different topic that must be dropped from this
  decision. If there is no adjacent off-topic event, return an empty list — do
  not invent exclusions.

## Approval vs closeout gating

An approval decision and the authority to close a case are different things. An
approval — even an "approved with conditions" decision — is NOT sufficient to
close when the folder is not ready OR a formal notice is defective.

- Defective folder or notice ⇒ gate = "approval not sufficient when folder or
  notice defective"; final result = "hold for folder and notice defects"; next
  action follows the defect (reissue a defective notice, or open records
  remediation for a missing-file folder defect).
- Folder ready and notice valid (records clean) ⇒ gate = "approval sufficient
  when records clean"; final result = "approve closeout" / "approve onboarding
  close".
- `closeout_blockers` is a set built from the actual defects found: missing
  required files, missing required tags, defective formal notice — include each
  only if present.

## Recruitment cost summation and candidate-outcome / handoff rules

- `recruitment_cost_total` = the sum of ALL cost-ledger line amounts for the
  opening. Sum every line; do not filter.
- Candidate buckets come from each candidate's committee decision: selected /
  waitlisted / rejected. Arrays contain candidate IDs only.
- `notice_followup_required` = candidates whose notice status / notice-packet
  status is "not sent". Waitlisted ⇒ send a waitlist notice; rejected ⇒ send a
  rejection notice.
- Selected offer: read its status from the offer register (accepted / draft /
  withdrawn / none).

Payroll handoff has THREE distinct concepts that share vocabulary — keep them
separate, because conflating them is the most common error:

1. The GATE / trigger (minimal precondition to start a handoff) is having an
   accepted offer alone ⇒ "accepted offer only". Do NOT fold the downstream
   submitted-assignment requirement into the gate.
2. The IMMEDIATE next action depends on which artifacts already exist. If the
   payroll-precheck records list is empty, the first step is to CREATE the
   payroll precheck ⇒ "create payroll precheck". Choose
   "create submitted assignment after acceptance" only when a precheck already
   exists / a submitted assignment is the immediate artifact to produce.
3. The EVENTUAL required end-state is still a submitted assignment after
   acceptance: status-required = "submitted after acceptance",
   handoff-control-result = "submitted handoff required after acceptance",
   draft payroll allowed = false.

The internally consistent recruitment-handoff answer when an offer is accepted
but no precheck exists yet is therefore: gate = accepted offer only; immediate
action = create the precheck; end-state required = submitted after acceptance.

## Reading escalation owner / SLA from an audit package (procedure)

When a task asks for the remediation owner, escalation owner, or an SLA, read it
from the GOVERNING POLICY DOCUMENT or the audit package's stated owner / SLA
fields — not from the case owner. The team that owns the case and the team that
owns a specific defect's remediation are frequently different. Locate the policy
referenced by the case (or the audit package), read its named owner / SLA, and
report that. (No concrete owner or SLA value is fixed here; always read it live
for the entity in front of you.)

## Output conventions

- Emit a single JSON object whose keys exactly match the provided
  `answer_template.json` — same key names, nothing added, nothing omitted.
- Enum fields must use a value verbatim from that field's `allowed_values`.
  Never invent a label and never substitute free-text.
- `list[...]` fields are sets: no duplicates, order not load-bearing. Empty when
  nothing qualifies (e.g. no excluded audit events).
- Types: integers stay integers, money is a number, booleans are real booleans.
- Effective date when there is no explicit `effective_date` field: derive it from
  the controlling record's period as the first of that month
  (`"YYYY-MM"` ⇒ `"YYYY-MM-01"`).
- Output only the JSON. No markdown fences or commentary unless the template /
  prompt explicitly asks for them.

## Common pitfalls

These are the mistakes that actually happen; each maps to a rule above.

1. Picking an evidence-source label from WHERE data is stored instead of its
   SHAPE — a structured notice in the messages endpoint is still packet
   inspection.
2. Conflating gate (trigger) vs immediate action vs eventual end-state when
   several enums share words like "submitted" / "accepted". Answer each field for
   its own concept.
3. Choosing the most "advanced" action label when the current artifacts dictate
   an earlier step — an empty precheck list means create the precheck first.
4. Letting a higher salary or higher day count on a Draft / later-period row beat
   the authoritative submitted-or-approved row.
5. Including off-topic same-case audit events in a scoped supporting list, or
   inventing exclusions when none exist.
6. Marking a folder ready on partial completeness, or treating files and tags as
   one check instead of two independent set comparisons.
7. Reporting the case owner as the remediation owner instead of reading the
   policy / audit package owner.
