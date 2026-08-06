# Task families and field-derivation rules

Match the request to one family, then derive each answer field from the retrieved records.
The families are recognizable from `request_type`/`current_stage` on the case and from the
answer template's fields. In every family: read adjudicated results from `case_criteria`, let the
criteria pattern drive the disposition, classify current vs. stale records, and fill
`basis_audit`.

General disposition logic (shared): when required criteria are **all met**, the outcome is an
approval; when a required criterion is **not_met** (or its policy `result_if_missing` is deny),
the outcome is adverse; when something is missing/**unclear/partial** the outcome is a pend or a
request for more information; when the decision needs a physician or a completed peer review it
routes to that step. Map that outcome onto the template's `recommendation` / `final_status` /
`route` / `letter_type` / `next_action` enums using the exact spellings the template allows.

---

## A. Prior-authorization / UM nurse determination

Signals: `request_type = prior_authorization`, a nurse-review stage, `request_lines`,
`case_criteria`, an `authorizations` row, and `documents`.

- **Criteria results:** map each required criterion ID from `case_criteria.result`.
- **Disposition:** all required criteria met → approve / approved / nurse_approval / approval
  letter / issue approval. A criterion whose miss defaults to deny → denial path; a criterion
  whose miss defaults to pend → pend / request more information. Missing-info or physician-only
  judgment routes to pend or medical-director review.
- **Authorization block:** copy `auth_number`, `approved_units`, `approved_start`,
  `approved_end`, and the modifier from the `authorizations` row. Split `approved_cpt` into a
  list and order it as the template says (e.g. ascending CPT).
- **Evidence vs excluded documents:** documents with `is_current = 1` that support the criteria
  are the evidence documents; `is_current = 0` (stale/superseded/off-topic) documents are
  excluded. Order each list as specified (e.g. ascending `document_id`).

## B. Coverage-exception appeal + manufacturer-assistance intake

Signals: an `appeals` row for the case, an `assistance_screen` row, `drug_trials`.

- **Routing:** `appeal_path` and `owner` come from the `appeals` row; `expedited` is true only if
  the expedited attestation is actually present/requested. `appeal_deadline` is the recorded
  appeal deadline.
- **Medication failures:** `drug_trials` with `documented = 1` → documented failures; `documented
  = 0` (referenced without a fill/claim record, or otherwise insufficient) → undocumented/
  insufficient. Use lowercase medication names, ordered as specified (usually alphabetical).
- **Criteria results:** from `case_criteria` (met / partial / not_met …). A second required
  failure that is referenced but unproven typically makes the failures criterion `partial`.
- **Required vs missing packet items:** the required packet is enumerated on the appeal record's
  notes / policy summary; order payer-appeal items before assistance items. Missing items are the
  required items not yet on file plus assistance gaps; order appeal-evidence gaps before
  assistance-information gaps. (Assistance items such as income proof belong to the assistance
  side.)
- **Assistance block:** `program_name`, a status mapped from `assistance_status`
  (ready / missing-information / not-eligible / not-applicable), and `missing_fields` from the
  screen (ordered as specified).
- **Next action:** if the packet is incomplete, request the missing information; escalate/file
  only when the packet supports it; expedited variants pair completing the appeal with requesting
  the outstanding income proof.

## C. Claim repricing against a rate benchmark

Signals: `request_type = claim_payment_review` / payment-integrity stage, a `claims` row with
`claim_lines`, and `payment_benchmarks`.

- **Select the effective benchmark per line:** match `plan_type` (from the member) + `cpt_code` +
  `modifier` + a service date inside the benchmark's `effective_start..effective_end`. The
  currently-effective schedule is the benchmark source; a schedule whose window ended before the
  service date is **stale** and must be rejected; benchmarks keyed to unrelated CPTs are
  distractors. If the paid amount equals a stale schedule's rate, that confirms the stale rate was
  wrongly applied.
- **Per line:** `correct_allowed_amount = allowed_amount × units` (rounded to cents);
  `recovery_amount = correct_allowed_amount − paid_amount`; `disposition` = correct_upward when
  allowed > paid, correct_downward when allowed < paid, no_change when equal (deny_line only when
  the line itself is non-covered/denied). Keep claim-line order; use `null` for absent modifiers.
- **Totals:** `paid_total` and `correct_allowed_total` and `recovery_amount` roll up from the
  lines. `benchmark_source` / `benchmark_version` name the effective schedule;
  `stale_source_rejected` names the rejected stale schedule (or "none").
- **Routing/priority:** a payment-integrity correction routes accordingly; priority follows the
  case urgency and materiality.

## D. Peer-to-peer closure

Signals: `request_type = peer_to_peer`, a completed `p2p_events` row, `case_criteria`, an
`authorizations` row.

- **Outcome/status:** `p2p_outcome` and `final_status` come from the `p2p_events` row
  (uphold-adverse vs overturn-to-approval).
- **Criteria + unresolved:** map the required criterion IDs from `case_criteria`; `unresolved`
  criteria are those still not met/unclear, in ascending criterion-ID order.
- **new_information_changed_review:** true only if the P2P supplied *new patient-specific* facts
  that materially changed the review; a generic clinical argument with no new patient facts →
  false (and the intended adverse decision is upheld).
- **Missing factors:** list the policy's enumerated over-standard factors that remain
  unsupported, in the order the choices are listed.
- **Letter / alternative / deadline:** letter type follows the final status; recommend the
  standard alternative modality when the requested advanced study fails its specific factor; if
  the final result is adverse, compute the internal appeal deadline as the stated window (e.g.
  180 days) from the adverse-determination date.

## E. Margin-queue analysis

Signals: a finance queue of `service_margin` rows named in the memo, with a threshold and a
cost definition.

- **Per row (in the memo's row order):** `total_cost = variable_cost + fixed_cost_allocated`;
  `margin = net_revenue − total_cost`; `revenue_to_cost_ratio = net_revenue / total_cost`
  (to the stated precision); `below_threshold = ratio < threshold`; `charge_sensitive` from the
  row flag.
- **recommended_action:** below-threshold and *not* charge-sensitive → payer_contract_review;
  charge-sensitive → monitor_charge_sensitive; otherwise → monitor_no_action. (Precedence is
  margin threshold first, then charge sensitivity — charge-sensitive rows are tracked separately
  rather than counted as payer-service issues.)
- **Segments:** `below_threshold_segments` = segments below threshold; `charge_sensitive_segments`
  = segments flagged charge-sensitive; both alphabetical.
- **Top issue + gap:** `top_issue` = the worst below-threshold segment/CPT (or "none");
  `gap_to_120pct = 1.2 × total_cost − net_revenue` for that top below-threshold row (to cents).
