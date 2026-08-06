# Classification and enum mapping

The template's `answer_template.json` fixes the allowed enum values per field.
The hub's raw vocabulary differs, so every classification is a mapping from a raw
hub fact to the nearest template enum member *by meaning*. Read the template's
enum lists first; the guidance below is how to choose among them.

## Severity / risk level (domain‑driven)
Do **not** simply copy the remediation action's `severity`. Assess by the nature
of the defect:
- **policy‑compliant destruction before the hold** → **low** (defensible; often
  a "no action / policy loss" outcome).
- **loss after the hold** (post‑hold destruction, post‑subpoena device wipe,
  post‑hold auto‑purge) → **high** — this is spoliation. Reserve **critical** only
  where the template's own tiering clearly calls for it; a plain post‑hold loss is
  high.
- **large unlogged‑privilege backlog, zero‑production‑claim contradicted by
  responsive documents, privilege waiver** → **high**.
- **over‑designation, minor coding variance** → **medium/low**.

## Issue type (map raw → enum by meaning)
| Raw hub fact | Typical enum family |
|---|---|
| personal device/email/messaging lost or not collected | preservation_failure / collection_gap / personal_source_gap / personal_email/phone_gap |
| records/boxes destroyed after hold | preservation_failure / post_hold_loss |
| records destroyed before hold under policy | retention_loss / policy_destroyed_pre_hold |
| messaging system window lost / channel deleted | active_system_loss / archive_available (if a backup exists) |
| privilege log incomplete (withheld > logged) | privilege_log_gap |
| privileged docs coded non‑privileged | miscoded_privilege / privilege_miscoding |
| responsive docs coded non‑responsive / zero‑claim contradicted | responsiveness_miscode / responsive_miscoding |
| privileged material forwarded to an outsider | third_party_waiver |
| over‑designated as privileged | over_designation → often maps to "other"/downgrade when no exact enum exists |
| record that should exist is missing | missing_required_record / should_exist_missing |

## Status / production impact
- Lost/wiped source → source status *lost/destroyed*, production impact
  *source_lost*.
- Known but uncollected source → *not_collected*, impact *source_missing* /
  *not_produced*.
- Incomplete privilege log → *withheld_unlogged*.
- Miscoded responsive / zero‑claim → *underproduced* / *recode_needed*.
- Privileged‑miscode → *privilege_exposure*.
- Post‑hold loss → a protocol‑noncompliance status; pre‑hold policy loss →
  a compliant/no‑gap outcome.
- A source with an available archive/backup → an *available / remediation_available*
  status and it belongs in the "available/retained sources" list, not the risk
  list.

## action_type — derive from the issue, not the hub verb
The hub often stores a generic verb (e.g. `privilege_rework`,
`supplemental_collection`, `retention_exception_review`, `qc_remediation`). Choose
the template `action_type` from what the underlying issue actually needs:
- incomplete privilege log → **supplement_privilege_log**
- over‑designation → **recode_and_produce** (or a privilege downgrade/recode)
- third‑party waiver → **waiver_assessment_and_disclosure**
- privileged miscode → **privilege_recode_and_log** / **qc_remediation**
- responsive miscode / zero‑claim → **recode_and_produce**
- personal source not collected → **collect_source / collect_personal_device /
  collect_personal_email / collect_signal_messages** (match the medium)
- available archive/backup → **search_archive / collect_archive**
- post‑hold spoliation → **disclose_preservation_issue** (and/or forensic recovery)
- pre‑hold policy loss → **no_action / document_system_gap**
- missing required record → **locate_missing_record**

## owner
Normalize the responsible‑party string from the record's remediation action to
snake_case. If the template's `owner` enum contains that exact member, use it;
otherwise map to the nearest member (e.g. a privilege function → privilege_team /
privilege_counsel; a review function → review_qc / review_vendor / review_operations;
a forensic/collection function → forensics / ediscovery_vendor / client_it; a
retention/records function → records_management; disclosure to the government →
outside_counsel / litigation_counsel). The available members differ per template —
always pick from that template's list.

## priority and ranking
- `priority` copies the action's P0–P3.
- For rank fields, order by priority first (P0/P1 highest), then by a stable
  tiebreaker the template implies (e.g. target/record id, or action id). Some
  templates want a unique 1..N rank; others break ties by id at the same rank —
  follow the template's ordering rule wording.
- Category‑code lists: uppercase and sort ascending.

## Metrics
Compute each named metric field precisely from the material set:
- unlogged privilege = withheld − logged (from the material log‑gap anchor only).
- box counts split by pre‑hold vs post‑hold using event date vs hold date.
- source counts by type (lost personal device, uncollected board/personal source,
  available archive, …).
- doc counts by coding issue (miscoded responsive, miscoded privileged,
  third‑party‑waiver, zero‑claim).
- category counts = size of the union of affected categories across material
  records; the "categories with … gap/risk" list is that union, uppercase‑sorted.
- readiness/ready booleans are false whenever any open gap remains.
Metrics are the most mechanical, highest‑yield part of the answer — get them
exactly right.
