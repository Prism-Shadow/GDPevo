# Task playbooks

Field-by-field logic per task shape. Field names come from the task's
`answer_template` — always defer to the template's exact keys, enums,
orderings, and precision. Below is *how to decide each value from the
records*. Everywhere, `criteria_results` = the governing policy's criterion
ids mapped to the case's per-criterion `result`.

## `source_precedence` selection (basis_audit)

Pick the governing precedence rule from the task shape:

| Task shape | source_precedence |
|---|---|
| Clinical determination weighing current vs stale/superseded records | `current_clinical_records_over_stale_export` |
| Coverage appeal + manufacturer-assistance intake | `payer_appeal_before_manufacturer_assistance` |
| Claim repricing against a rate benchmark | `effective_benchmark_by_plan_modifier_and_date` |
| Peer-to-peer review with new patient-specific info | `new_patient_specific_p2p_information` |
| Finance margin queue (below-threshold vs charge-sensitive) | `margin_threshold_then_charge_sensitivity` |
| Appeal triage weighing deadline vs clinical vs payment integrity | `appeal_deadline_then_clinical_then_payment_integrity` |

---

## Shape A — Prior-authorization / UM determination

Anchor: `cases` (+ authorizations, case_criteria, documents, request_lines).

- **recommendation / final_status / route / determination_letter / next_action**
  follow the criteria outcome and the authorization record's status:
  - All required criteria `met` and the auth record recommends approval →
    approve / approved / nurse-approval route / approval letter / issue-approval.
  - A criterion whose `result_if_missing` is `pend` is unmet → pend / request
    more information. One whose `result_if_missing` is `deny` is unmet → deny
    path or MD/peer escalation, per the template's enums.
  - Read the auth record's `status`/`denial_reason` as the tie-breaker for
    approve vs deny vs escalate.
- **authorization object** comes straight from the `authorizations` row:
  `auth_number`, `approved_units`, `approved_start`, `approved_end`,
  `approved_modifier`. `approved_cpt` is often a comma-joined string → split
  into a list and sort ascending by code.
- **criteria_results** = each required criterion id → its `case_criteria.result`.
- **evidence_documents** = current documents relied on (`is_current` = true),
  ascending by `document_id`. **excluded_documents** = non-current / stale
  documents (`is_current` = false), ascending by `document_id`.
- **basis_audit**: `source_precedence` = current-over-stale; controlling =
  the current evidence records; exception = the stale/excluded record(s).

## Shape B — Coverage appeal + manufacturer assistance

Anchor: `appeals` (+ case_criteria, drug_trials, assistance_screen, documents).

- **appeal_path / expedited / appeal_deadline / owner** from the `appeals`
  row. `expedited` = true only if the expedited attestation is present/requested
  (an attestation value like "not_requested" → false).
- **drug** from the case/policy subject.
- **documented_failures** vs **undocumented_or_insufficient_failures** from
  `drug_trials.documented` (1 → documented, 0 → undocumented/insufficient).
  Emit lowercase medication names, alphabetical.
- **criteria_results** from `case_criteria` (may include `partial`).
- **required_packet_items** = the *formal* packet the policy/appeal requires,
  in operational order (payer-appeal items before assistance items). Use
  exactly the enumerated required set — do not fold case-specific granular gaps
  into it.
- **missing_packet_items** = the *case-specific* gaps: the appeal-evidence gap
  first, then the assistance-info gap. When a criterion is `partial`, the
  appeal-evidence gap is the **specific** missing sub-document named in the
  criterion's `gap_description` (e.g. a specific fill/claim record), not the
  generic evidence category.
- **assistance** from `assistance_screen`: `program_name`; `status` mapped to
  the template enum (e.g. a "pending, missing income proof" state →
  eligible-but-missing-information); `missing_fields` list, alphabetical.
- **next_action**: packet incomplete on a standard appeal → request more
  information; expedited path with an income gap → complete the expedited
  appeal and request the income proof; etc., per the template enums.
- **basis_audit** `source_precedence` = payer-appeal-before-assistance.

## Shape C — Claim repricing / payment integrity

Anchor: `claims` + `claim_lines` (+ payment_benchmarks, cases).

- **auth_number** from the claim (or its payment record).
- **Benchmark selection**: for each line, match `payment_benchmarks` on
  payer + member's plan_type + service_domain + cpt_code + modifier, and take
  the row whose `effective_start ≤ service_date ≤ effective_end`. That is the
  correct benchmark. An expired/superseded schedule (window ended before the
  service date) is the **stale source to reject** — and it frequently equals
  what was actually paid (the planted error).
  - **benchmark_source** = correct benchmark's `source_name`;
    **benchmark_version** = its `source_version`;
    **stale_source_rejected** = the rejected schedule's `source_name` (or the
    template's "none" when nothing is stale). This field is graded — set it.
- **Per line**: `line_id` = `claim_line_id`; `cpt_code`, `units`, `modifier`
  (null when absent); `paid_amount` from the line; `correct_allowed_amount` =
  per-unit allowed × units; `recovery_amount` = correct_allowed − paid;
  `disposition` = correct_upward (corrected > paid) / correct_downward
  (corrected < paid) / no_change (equal) / deny_line. Emit lines in
  `line_number` order.
- **Totals**: `paid_total` = Σ line paid (cross-check against the claim row);
  `correct_allowed_total` = Σ corrected; `recovery_amount` = corrected − paid.
- **resubmission_route / priority** per the case's stage and urgency (a routine
  payment-integrity correction → payment_integrity_correction / standard).
- **basis_audit** `source_precedence` = effective-benchmark-by-plan-modifier-and-date;
  controlling = the current benchmark rows; exception = the stale benchmark row.

## Shape D — Peer-to-peer (P2P) closure

Anchor: `p2p_events` (+ case_criteria, request_lines, authorizations, documents).

- **p2p_id / p2p_outcome / final_status** straight from the `p2p_events` row
  (`outcome`, `final_status`). **requested_cpt** from the request line.
- **criteria_results** = the required policy criterion ids → results.
- **unresolved_criteria** = criterion ids still unsatisfied (`not_met` /
  `unclear`), ascending. Empty only if all applicable criteria are met.
- **new_information_changed_review** (boolean) = true only if the P2P supplied
  new patient-specific info that materially changed the outcome; if the event
  notes say nothing new and the outcome upholds the adverse decision → false.
- **domain-factor list** (e.g. missing PET-over-SPECT factors) = each policy
  factor that remains unsupported, in the order the template lists them.
- **letter_type** from the final status (denied → denial, approved → approval,
  partial → partial_denial, else no_letter).
- **recommended_alternative** = the covered fallback modality when the
  requested one is denied only for a missing modality-specific factor while
  the underlying indication is still covered (else "none").
- **internal_appeal_deadline**: if the final result is adverse, add the
  internal-appeal window the task states (e.g. the plan's N-day window) to the
  **final adverse determination date** — the date the adverse decision became
  final, i.e. the P2P completion/event date — **not** the reporting date. Use
  `null` when no appeal deadline applies (non-adverse result).
- **basis_audit** `source_precedence` = new-patient-specific-p2p-information.

## Shape E — Finance / margin queue

Anchor: `service_margin`, restricted to the queue row ids the task lists.

- **Use only the listed queue row ids**, and emit `rows` in that exact order.
- Per row: `total_cost` = `variable_cost` + `fixed_cost_allocated` (use the
  task's stated cost definition); `margin` = `net_revenue` − `total_cost` (may
  be negative); `revenue_to_cost_ratio` = `net_revenue` / `total_cost` at the
  stated precision; `below_threshold` = ratio < the task's threshold;
  `charge_sensitive` = the row's flag (1/0 → boolean).
- **recommended_action**: margin threshold takes precedence over charge
  sensitivity — below_threshold → payer_contract_review; else charge_sensitive
  → monitor_charge_sensitive; else monitor_no_action.
- **below_threshold_segments / charge_sensitive_segments** = the
  `payer_segment`s meeting each flag, alphabetical.
- **top_issue** = "<segment>_<cpt>" of the top below-threshold row ("none" if
  none are below threshold). **gap_to_120pct** (or the stated target) =
  threshold × total_cost − net_revenue for that top issue, at the stated
  precision.
- **basis_audit** `source_precedence` = margin-threshold-then-charge-sensitivity;
  controlling = the queue rows driving the actioned issue; exception = the
  charge-sensitive monitored rows.

---

## Precision & ordering reminders (graded)

- Round each numeric field to the precision the template names; compute at full
  precision, round once. Ratios/percentages and currency have their own
  precisions.
- Apply every ordering note literally: ascending-by-id, alphabetical,
  as-listed (source order), and claim-line order are all used and checked.
- `null` for absent scalars (e.g. no modifier); `[]` only where an empty list
  is explicitly allowed.
