# Analysis playbook — signal → finding → enum

The four deliverable variants share one analysis. This playbook maps hub signals to the finding
archetypes and to the *kinds* of enum values templates use. Enum spellings differ per template —
always pick the **closest member of the current `answer_template.json`'s enum list**; never
invent a value.

## A. The material-vs-noise filter (apply first)

Keep a row only if it is one of the material signals below. Discard routine/process-hygiene rows —
they are volume padding and belong in *no* finding, category status, or action.

| Table | KEEP (material) | DROP (noise) |
|---|---|---|
| retention_events | post_hold_loss, should_exist_missing, auto_purged, post_hold_partial_recovery; retained/available (as archives); system_loss (in context) | routine dated `policy_destroyed_pre_hold` counts as *no-fault*, not a defect |
| custodian_sources | status lost/not_collected; tags collection_gap, personal_*, *_erasure, post_hold_wipe, signal_missing, board_materials, deleted_channel, purged_mail, archive_available, remediation_source, valuation_source_gap | routine, scope_exception, bare metadata_gap |
| review_documents | tags miscoded_nonresponsive, zero_claim_contradiction, unrecovered_file, valuation_red_flag, unsupported_* | routine, duplicate, family_member, metadata_gap, custodian_alias, potentially_responsive, privilege_overlay, review_escalation |
| privilege_entries | incomplete_log, over_designated, third_party_waiver, family_mismatch | clean |
| qc_findings | miscoded_privilege, zero_claim_contradiction, miscoded_nonresponsive | metadata_gap, date_normalization, near_duplicate, family_break, duplicate_overlay |
| production_stats | zero_claim_contradicted | closed, produced, supplement_pending, rolling_review |
| remediation_actions | rows targeting PRIV-*/QC-*/RET-*/SRC-*/DOC-* | action_id `*NOISE*`; bare-category target with sampling_review/low severity |

## B. The pre-hold / post-hold rule (most important distinction)

For any retention or source loss, compare the loss date to the matter's `hold_date`:

- **Before hold + policy-compliant** (`policy_destroyed_pre_hold`, or a source destroyed on a
  documented retention schedule pre-hold) → **NOT a gap / no fault.** Status maps to a
  "policy loss / no gap" enum; action maps to "no action (policy loss)". Report it only where a
  template explicitly wants the full retention-event ledger; otherwise it is the *reason* a
  touched category is left un-flagged.
- **After hold** (`post_hold_loss`, `post_hold_wipe`, `post_subpoena_erasure`, `remote_erasure`,
  deletions dated after hold) → **preservation FAILURE.** High/critical; production impact
  "source lost"; action = disclose to government / disclose preservation issue.
- **Should-exist-missing** → a required record absent → "missing required record"; action =
  locate missing record.

## C. Finding archetypes → enum intent

For each material row, emit one finding/risk object. Choose enum members whose *meaning* matches:

| # | Signal | issue/risk type intent | source/production status intent | recommended action intent | typical owner intent |
|---|---|---|---|---|---|
| 1 | retention_events post_hold_loss | preservation_failure / post_hold_loss | source_lost / lost | disclose_to_government / disclose_preservation_issue | outside_counsel / litigation_counsel |
| 2 | policy_destroyed_pre_hold | retention_loss but no_gap | not_applicable | no_action / no_action_policy_loss | records_mgmt / compliance |
| 3 | should_exist_missing | missing_required_record | source_missing | locate_missing_record | compliance_audit / records |
| 4 | auto_purged / deleted_channel comms | collection_gap / preservation | source_missing/lost | collect/restore, or search archive if one exists | it_messaging / ediscovery_vendor |
| 5 | custodian_sources not_collected/lost personal_* | collection_gap / personal_source_gap | not_collected / source_missing | collect_source / collect_personal_device | forensics / client_it |
| 6 | archive_available source or retained/available retention event | archive_available | source_available / available_archive | search_archive / collect_archive | ediscovery_vendor / records |
| 7 | privilege_entries incomplete_log | privilege_log_gap | withheld_unlogged | supplement_privilege_log | privilege_team |
| 8 | third_party_waiver / third_party=1 | privilege_waiver / third_party_waiver | privilege_exposure | waiver_assessment_and_disclosure | privilege_counsel / privilege_team |
| 9 | over_designated / miscoded_privilege | over_designation / privilege_miscoding | recode_needed | privilege_re_review / privilege_recode_and_log | privilege_team / review_qc |
| 10 | miscoded_nonresponsive | responsiveness_miscode | not_produced / recode_needed | recode_and_produce | review_qc / review_vendor |
| 11 | production_stats zero_claim_contradicted (+ docs) | zero_claim_contradiction / responsiveness_miscode | not_produced | recode_and_produce / disclose | review_qc / outside_counsel |
| 12 | produced_status unrecovered / unrecovered_file | post_hold_loss / collection_gap | source_lost | forensic_recovery | forensics |

Severity/priority: post-hold preservation loss, zero-claim contradiction, and third-party waiver
are typically **critical/high → P0/P1**; privilege-log gaps and responsiveness miscodes **high →
P1**; over-designation, available-archive follow-ups, missing-record location **medium → P2**;
pre-hold policy loss and clean/routine **low → P2/P3 or no action**. When the matter's
`remediation_actions` row exists for a finding, trust its `priority`/`severity`/`due_days`.

## D. Category coverage

1. Take the canonical code set from `subpoena_categories` for the matter.
2. For each material finding, expand its category refs (`category_code` /
   `affected_categories` / `category_impacts` / `affected_category`).
3. Per category, assign the status of its **most severe** material finding; collect the
   supporting record IDs into the ref list; set production_impact and recommended_action to
   match; count open material issues if the template wants `open_issue_count`.
4. Include only categories with a material, non-complete status (unless the template says to
   list all). A category touched *only* by pre-hold policy loss is **not** an open gap.

## E. Metrics — read each key name literally

The metric key name encodes the exact population, filter, and unit. Compute via SQL aggregation
over material rows only:

- `withheld/logged/unlogged_privilege_docs` → Σ over `incomplete_log` entries;
  `unlogged = Σwithheld − Σlogged`.
- `waived_privilege_doc_count` / `third_party_waiver_doc_count` → Σ doc_count over
  `third_party_waiver` (or `third_party=1`) entries.
- `miscoded_responsive_doc_count` → Σ doc_count over `miscoded_nonresponsive` QC findings
  (or the matching review_documents count).
- `miscoded_privileged_doc_count` → Σ over `miscoded_privilege` QC findings.
- `*_box_count` → retention_events with `volume_unit='boxes'` only (pre- vs post-hold split by
  status when both are asked).
- `post_hold_loss_event_count` → count of post_hold_loss retention events.
- personal/board/uncollected `*_source_count` → count of the matching custodian_sources.
- `available_archive_count` → count of archive/available/retained remediation sources.
- `affected_category_count` / `categories_with_open_*` → distinct material categories.
- `*_ready` / `production_ready` (boolean) → **true only if no material blocker remains.** With
  any open preservation loss, privilege-log gap, miscode, or zero-claim contradiction → false.

## F. Action plan

- Backbone = the matter's material `remediation_actions` (already carry action_type, priority,
  severity, owner, target_ref, due_days). Map hub `action_type` and hub `owner` labels to the
  closest members of *this* template's enums:
  - action_type: `privilege_rework`→supplement/recode-log; `qc_remediation`→recode/QC;
    `supplemental_collection`→collect source/device; `retention_exception_review`→disclose/locate;
    `custodian_followup`→collect/investigate; `load_file_cleanup`/`sampling_review`→QC review.
  - owner: `Forensics`→forensics; `Privilege Team`→privilege_team/privilege_counsel;
    `Review Operations`/`Vendor Team`→review_qc/review_vendor/ediscovery_vendor;
    `Legal Hold Team`→client_legal/records; `Matter Associate`→outside_counsel/legal_operations.
- Ensure every material finding is covered by an action; add a derived action if the hub lacks
  one for a required finding. Rank by priority → severity → target_ref (per the template's
  `ordering_rules`). Keep `target_refs` as real hub IDs. Drop NOISE rows.

## G. Output discipline

One JSON object. Exactly `required_top_level_keys`. Every object carries its
`item_required_keys`. Enum values ∈ the template's lists. Lists sorted per `ordering_rules`;
category-code lists uppercase + ascending. Whole-integer counts. Real hub IDs verbatim in every
ref. No prose outside the JSON.
