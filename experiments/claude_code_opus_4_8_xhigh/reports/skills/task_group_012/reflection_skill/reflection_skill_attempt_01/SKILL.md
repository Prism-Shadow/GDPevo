---
name: peopleops-console
description: >-
  Resolve HR "PeopleOps Console" lifecycle-control tasks against a read-only JSON
  API (onboarding closeout, folder + formal-notice review, leave source
  precedence, payroll/accrual readiness, and recruitment reconciliation). Use
  this skill whenever a task asks you to verify, reconcile, validate, or review a
  People Ops / HR lifecycle record and return a structured JSON answer that
  matches a provided answer_template.json with normalized business labels — even
  if the prompt does not name "PeopleOps". Strong triggers: an answer template
  with enum allowed_values like submitted/draft/superseded, defective notice
  defect codes, approve_closeout / hold_for_folder_and_notice_defects /
  ready_with_monitoring, or fields named excluded_*_ids, folder_ready,
  notice_defects, recruitment_cost_total, payroll_handoff_gate. It encodes the
  query order, source-precedence and exclusion rules, folder-readiness set
  comparison, notice-defect detection, audit scoping, gating, cost summation,
  and the exact output conventions these tasks are graded on.
---

# PeopleOps Console — lifecycle control resolver

You are answering HR lifecycle "control" questions against a local read-only JSON
API. Each task names one focal entity (an employee, a case, an opening, an offer,
or a folder), asks you to determine the authoritative state and the correct
control action, and gives you an `answer_template.json` whose every field you must
fill with a value of the right type — usually a **normalized enum label** drawn
from that template's `allowed_values`.

The grader compares your JSON to a gold answer key by key. There is no partial
credit inside a field: a value is either the exact normalized label or it is
wrong. So the whole game is (1) gather the right evidence and (2) map it to the
**correct label for each field's specific role**. Most mistakes are not factual —
they are picking a plausible-but-wrong sibling label.

## Golden rule: read the template first, then work backwards

Before querying anything, open `answer_template.json` and read every field, its
`type`, and its `allowed_values`. The template tells you exactly what the task is
really about and which distinctions matter. Two fields can look similar but mean
different things (e.g. an "evidence source" vs an "action" vs an "escalation").
Treat each field as a question you must answer from evidence, and never reuse one
field's value in another field just because they share a vocabulary.

Output a single JSON object with **exactly** the template's keys — no extra keys,
no missing keys, no markdown, no commentary. Match each declared `type`:
`string` → raw id/name as stored; `integer`/`number` → numeric (not a string);
`boolean` → true/false; `enum` → one allowed label; `list[...]` → a JSON array.

## Environment access

Everything is behind a local JSON API (see `environment_access.md` in the task
for the base URL and the full endpoint list). The web UI login is for humans
only; the JSON API needs no auth. Use the API directly, e.g. `curl -s <base>/...`.
Never read server source or data files on disk.

Key endpoints (names are stable across this task family):
- `/api/summary`, `/api/manifest` — counts and module overview.
- `/api/employees?q=` — employee profiles (q is a case-insensitive substring
  filter over scalar fields).
- `/api/cases` and `/api/cases/<id>` — case summaries and full detail
  (approvals, attachments, comments, audit_events, policy_refs).
- `/api/policies` and `/api/policies/<id>` — policy documents (the rules).
- `/api/payroll-ledgers?q=` — salary / leave assignment rows.
- `/api/recruitment?q=` — openings with candidates, offer_register, cost_ledger,
  notice_packets, payroll_precheck_records.
- `/api/documents?q=` — folders with files, required_files, tags, required_tags,
  ready flag.
- `/api/messages?q=` — lifecycle notices (carry quality/defects/status).
- `/api/audit?q=&case_id=` and `/api/audit/<id>` — audit events.
- `/api/attachments/<id>` — raw attachment text.

## Standard operating procedure (query order)

Work from authority outward. A good general order:

1. **Resolve the focal entity by its id** from the prompt (employee, case,
   opening, …). Look it up directly; do not browse whole collections.
2. **Pull the controlling records** for the question:
   - leave/payroll → `/api/payroll-ledgers` filtered to that entity (assignment
     history rows).
   - case/folder/notice → `/api/cases/<id>` plus `/api/documents` for the folder
     and `/api/messages` / case `notice_packets` for the notice.
   - recruitment → `/api/recruitment` for the opening's full packet.
3. **Read the governing policy** referenced by the case/task
   (`policy_refs` or a source-precedence policy) to learn the precedence,
   readiness, and notice-requirement rules. The policy — not your intuition —
   defines what "ready", "controls", and "required" mean.
4. **Pull the audit event(s)** for the entity. The audit detail frequently states
   the authoritative conclusion in words (e.g. which record controls, that a
   profile is stale, that something is ready). When an audit event names the
   controlling record or result, trust it.
5. **Map evidence to the template's normalized labels** and assemble the JSON.

Only look up entities named in the prompt and records directly linked to them.
Do not enumerate collections hunting for unrelated cases/packages.

## Source precedence and exclusion (assignment history)

Profiles, case summaries, and ledgers can disagree. The authoritative value comes
from the **assignment-history record that controls**, not from a summary:

- **Leave**: the latest **approved/submitted** leave assignment for the period
  controls. **Draft**, **voided/superseded/obsolete** assignments, and a **stale
  employee-profile summary** do **not** control — even when a profile or case
  summary shows a different number.
- **Payroll/salary**: the current **submitted** salary assignment controls;
  **draft** planning assignments do not affect payroll or accrual.
- Put every non-controlling record you set aside into the matching
  `excluded_*_ids` list (drafts and superseded/voided records both go here).
- For precedence/source fields choose the label that names the controlling source
  (e.g. an approved-assignment-over-profile or approved-assignment-current-period
  label, a submitted payroll-source-status label) — not the summary/profile label.
- When an audit event explicitly says a summary is stale and names the approved
  assignment that controls, the precedence is "approved assignment over profile",
  the profile is ignored, and the next action is to update the summary.

The controlling record's stored fields supply the concrete outputs: effective
policy name, annual/balance days, base salary, effective date, assignment id.
Prefer the number the controlling/approved assignment (and any audit that names
it) gives — do not average ledger rows or pick an unrelated adjustment line.

## Folder readiness = set comparison

A folder is **ready only if it has every required file AND every required tag**.
Compute it as two set differences:

- `missing_files` = required_files − present files.
- missing tags = required_tags − present tags.
- `folder_ready` (or readiness) is true only when **both** differences are empty.

Then translate to the template's fields independently:
- `required_tag_present` reflects only the tag check.
- `folder_required_tag_action` is "add the required tag" only if a required tag is
  missing; otherwise "no tag action".
- A missing file contributes the `missing_required_files` blocker; a missing tag
  contributes the `missing_required_tags` blocker; never assume one implies the
  other — a folder can miss a file while its tags are complete, or vice versa.

## Formal-notice defect detection and vocabulary

A formal notice is **defective** if it omits anything the governing policy
requires it to contain (e.g. appeal instructions, an acknowledgement deadline,
the correct policy reference, or a waitlist status, depending on the policy and
notice type). Compare the notice's content/declared defects against the policy's
notice requirements.

Report defects using **only** these normalized defect codes (the allowed
vocabulary):
- `missing_ack_deadline`
- `missing_appeal_instructions`
- `missing_waitlist_status`
- `missing_correct_policy`

`notice_quality` is `valid` or `defective`. List `notice_defects` as a set of the
codes above (order does not matter); empty when valid.

**Notice evidence source — judge by the artifact, not the endpoint.** This is a
common trap. The `notice_evidence_source` / `notice_quality_source` field asks
*what kind of artifact you inspected*, not *which URL served it*:
- `notice_packet_inspection` — there is a **structured notice record carrying
  machine-readable fields** such as `quality`, `defects`, and `status`. This is
  the right label whenever such a structured notice object exists, **even if it is
  returned by a messages-style list endpoint**. A structured notice record is a
  notice packet.
- `message_notice_inspection` — the only notice evidence is **unstructured text in
  a message body**, with no structured quality/defects fields to inspect.
- `case_summary_only` — the notice is mentioned only in the case summary, with no
  notice artifact at all.

## Audit-event scoping (supporting vs excluded)

Each task has a single **scope** (document/notice findings, leave-source
precedence, or payroll-assignment readiness). Audit events must be filtered to
that scope:

- `supporting_audit_event_ids` = the event(s) whose subject matches the task's
  scope (e.g. a notice/defect event for a document-notice review; a leave event
  for a leave-precedence task; a payroll/accrual event for a readiness task).
- `excluded_audit_event_ids` = **adjacent in-scope-of-the-entity-but-off-topic
  events** that belong to a different track and must not influence this decision
  (e.g. a folder/tag event excluded from a leave-precedence decision). If the
  entity has no such adjacent event, this list is empty — do not invent one.
- A singular `audit_event_id` field wants the one event that supports *this*
  task's scope.
- `audit_scope` is the label naming this task's scope.
- `audit_result` / `control_result` echo what the audit event concluded
  (e.g. a stale-profile result, a ready-with-monitoring result).

## Approval vs closeout gating

An approval decision (even "approved" / "approved with conditions") does **not**
by itself authorize closeout. Gating is a separate check:

- If folder and notice records are **clean**, the gate is "approval sufficient
  when records clean", the closeout action is "approve onboarding close", and the
  final control result is "approve closeout".
- If the folder or notice is **defective**, the gate flips to "approval not
  sufficient when folder or notice defective", the closeout action / next action
  is "block close and reissue notice", and the final control result is "hold for
  folder and notice defects".
- Record the `final_decision` (the approval body's actual decision and authority)
  separately from the gate — a case can be "approved with conditions" yet still be
  held for defects.

**Escalation vs next-action are different fields.** When a case has folder/records
defects, the **escalation track** is to **open records remediation** (owned by the
folder/records owner), while the **notice track** is handled by the next-action /
notice-remediation fields ("block close and reissue notice" / "reissue defective
notices"). Do not copy the notice action into the escalation field. Escalation
collapses to the notice action (or to "no action") only when there is no separate
records-remediation track to open.

For ownership/SLA fields, read the **owner from the governing source**: the
records-remediation owner is the folder/records owner named by the folder policy
or the folder record; an escalation owner/SLA, when the task supplies an audit or
escalation package, is read from that package's stated fields — quote the package,
do not guess a name or number. Choose the owner label from the template's
allowed_values that matches.

## Recruitment reconciliation

For an opening's outcome packet:
- **Candidate outcomes** come from the committee decision plus offer
  confirmation. Bucket each candidate as selected / waitlisted / rejected; the
  status source is "interview feedback and offer" and the outcome control is
  "committee decision with offer confirmation".
- **Offer**: the selected candidate's offer id, its base salary, and its status
  (e.g. accepted) come from the offer register.
- **Cost total** = the **sum of every line in the recruitment cost ledger** (add
  all line amounts). The cost source is the recruitment cost ledger.
- **Follow-up notices**: every candidate whose notice has not been sent needs
  follow-up — `notice_followup_required` lists those candidate ids; waitlisted →
  "send waitlist notice", rejected → "send rejection notice". Notice quality
  source is "notice packet inspection" when a structured notice packet exists.
- **Offer exclusion for waitlisted**: a waitlisted candidate is excluded because
  they have no accepted status or offer.

**Recruitment-stage handoff stays at the recruitment stage.** This is a trap:
- The **gate** that triggers an onboarding handoff at the recruitment stage is
  simply that an **accepted offer exists** → `accepted_offer_only`.
- The **handoff action** at this stage is to **create the payroll precheck**
  (`create_payroll_precheck`) — the first artifact in the handoff chain — not to
  create the final submitted assignment.
- The strict "submitted assignment required, drafts not allowed" requirement is
  expressed in the *downstream* fields and is still asserted there: the required
  assignment status is "submitted after acceptance", draft payroll is **not**
  allowed (false), and the handoff control result is "submitted handoff required
  after acceptance". Keep those strict — only the recruitment-stage *trigger*
  (gate) and *action* (handoff) use the earlier/looser labels.

## Output conventions

- Emit JSON with exactly the template's keys; no extras, none missing.
- Use the normalized enum label verbatim from `allowed_values`; never free text.
- Numbers are numeric; booleans are true/false; ids/names are strings as stored.
- Treat every `list[...]` field as a **set**: include each id once, order does not
  matter, and use `[]` for "none" (never `null`, never a string).
- `excluded_*` lists must contain every set-aside record (drafts + superseded/
  voided + off-scope audit events as applicable).

## Common pitfalls (learned from prior mistakes)

These are the errors that actually cost points; check each before you finalize:

1. **Labeling a notice source by endpoint instead of artifact.** A structured
   notice record with quality/defects fields is `notice_packet_inspection` no
   matter which list endpoint returns it. Reserve `message_notice_inspection` for
   plain message-body text with no structured fields.
2. **Copying the notice action into the escalation field.** Escalation for a case
   with records defects is "open records remediation"; the notice block/reissue
   action belongs in next-action / notice-remediation. They are parallel tracks.
3. **Over-applying employee-side payroll strictness to the recruitment trigger.**
   The recruitment handoff gate is `accepted_offer_only` and the action is
   `create_payroll_precheck`. The "submitted assignment / no drafts" strictness
   lives only in the *_status_required and *_control_result fields.
4. **Inventing excluded items.** Only list `excluded_*` entries that actually
   exist (a real draft/superseded record, a real adjacent off-scope audit event).
   If none exist, the list is `[]`.
5. **Letting an approval imply closeout.** Always run the gate separately; a case
   can be approved yet held for defects.
6. **Reading the wrong number.** Use the value the controlling/approved record (or
   the audit event that names it) gives; ignore unrelated adjustment lines and
   stale summaries.
7. **Folder file/tag conflation.** Check files and tags independently; a folder
   can fail one and pass the other.
8. **Free-text or wrong-type values.** Every enum must be an exact allowed label;
   numbers numeric; lists as arrays/sets.

For the full per-area label inventory and the field-by-field role map, see
`references/field-guide.md`.
