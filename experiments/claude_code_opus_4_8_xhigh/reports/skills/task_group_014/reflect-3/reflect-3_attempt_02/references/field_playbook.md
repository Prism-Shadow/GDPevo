# Field derivation playbook (reference)

Identify the task type from the target id / requester role / output template, then apply the
matching rules. Every type also fills `basis_audit` (see SKILL.md §4) and obeys the output
discipline (see `output_checklist.md`). None of these values are hardcoded — derive each
from the records for the specific target.

## Cross-cutting building blocks

- **criteria_results** — for each criterion key the template requires, copy that case's
  `result` from `case_criteria`. Keep values in the template's enum (`met` / `not_met` /
  `partial` / `unclear` / `not_applicable`). If a required criterion has no case row, fall
  back to the intent of `policy_criteria.result_if_missing`. Do not re-derive results the
  environment already recorded.
- **Overall disposition** — aggregate the criteria against the authoritative decision
  record:
  - All required criteria `met` and the decision record shows an approval → approve /
    approved / nurse-approval route / approval letter / issue-approval action.
  - A required, approval-gating criterion is `not_met` with a deny-if-missing fallback →
    deny / denied / denial letter / issue-denial (or route to MD / P2P if the stage record
    says so).
  - Gaps that are `pend`/`partial`/missing information → pend / request-more-information.
  - When a decision record (authorization/appeal/P2P) exists, its `status`/`outcome`/
    `final_status` is authoritative for the final-status field.
- **evidence vs. excluded documents** — evidence/relied-on = `documents.is_current = 1`;
  excluded = `is_current = 0` (stale exports, superseded/out-of-scope). Emit ids per the
  template's ordering (typically ascending `document_id`).
- **enumerated codes/segments/modifiers** — take strings verbatim from the records; split
  comma-joined fields (e.g. `approved_cpt`) into a list and sort per the template.

## Prior-authorization nurse determination

- `authorization` block ← the `authorizations` row: `auth_number`, `approved_units`,
  `approved_start/end`, `approved_cpt` (split + sort ascending), `modifier` from
  `approved_modifier`.
- recommendation / final_status / route / determination_letter / next_action ← overall
  disposition above.
- evidence_documents / excluded_documents ← current vs. stale split.
- `basis_audit.source_precedence` = current-clinical-records-over-stale-export when the
  case hinges on trusting current documents over a stale export; controlling = current
  docs, exception = the stale doc.

## Pharmacy coverage appeal + manufacturer-assistance intake

- appeal_path / expedited / appeal_deadline / owner ← the `appeals` row (`expedited` is
  true only if an expedited attestation was actually requested/affirmed).
- documented_failures ← `drug_trials` with `documented = 1`; undocumented_or_insufficient
  ← `documented = 0`. Emit lowercase medication names, sorted as the template says.
- required_packet_items ← the packet list stated in the appeal `notes` / policy summary,
  in the operational order the template names (payer-appeal items before assistance items).
- missing_packet_items ← the **concrete missing artifacts**, not the coarse parent
  criterion. A partial criterion means a specific artifact is absent (e.g. a specific fill
  record for an undocumented failure); name that fine-grained item plus any assistance gap.
  Order appeal-evidence gaps before assistance-information gaps.
- assistance ← `assistance_screen`: `program_name`; `status` = `eligible_missing_information`
  when the required denial is on file but other fields (e.g. income proof) are still
  missing, `eligible_ready` when nothing is missing, else `not_eligible`/`not_applicable`;
  `missing_fields` ← the screen's missing fields, sorted as specified.
- next_action ← request-more-information when the packet is incomplete and not expedited;
  otherwise the action the state implies.
- `basis_audit.source_precedence` = payer-appeal-before-manufacturer-assistance.

## Claim repricing / benchmark validation

- Choose the benchmark row per line by matching payer + plan type + service domain +
  CPT + modifier, **effective on the line's service date**. That current row is
  `benchmark_source`/`benchmark_version`; the expired/wrong row is `stale_source_rejected`
  (`none` if nothing to reject). Ignore same-value duplicates and distractor schedules.
- Per line: `correct_allowed_amount` = benchmark allowed amount × units;
  `recovery_amount` = correct_allowed − paid; `disposition` = correct_upward if
  allowed > paid, correct_downward if allowed < paid, no_change if equal (deny_line only
  if the line is not payable). `modifier` = null when the line has none.
- Totals: `paid_total` and `correct_allowed_total` are the line sums; top-level
  `recovery_amount` = correct_allowed_total − paid_total (a positive value is the
  underpayment/recovery). Lines stay in claim-line order.
- resubmission_route / priority ← the operational context (e.g. a payment-integrity
  correction at standard priority for a routine underpayment).
- `basis_audit.source_precedence` = effective-benchmark-by-plan-modifier-and-date;
  controlling = the chosen current benchmark rows, exception = the rejected stale row.

## Peer-to-peer (P2P) final summary

- p2p_id / p2p_outcome / final_status ← the `p2p_events` row; requested_cpt ←
  request line / authorization.
- criteria_results ← `case_criteria` for the required criterion keys.
- unresolved_criteria ← the required criteria whose result is not `met` (the blocking
  ones), ascending by id; empty only if none remain unresolved.
- new_information_changed_review ← whether the P2P `new_information` materially changed the
  review (false when no qualifying new information was supplied).
- missing_pet-style factor list ← each named factor that remains undocumented, in the
  template's choice order.
- letter_type follows final_status (adverse → denial / partial_denial); recommended
  alternative modality is the fallback modality when the requested one is denied for a
  missing specialty factor (else `none`).
- If the final determination is adverse, compute the internal appeal deadline = the **final
  adverse determination date** (the P2P event's date) **+ the plan's internal appeal window
  stated in the task** (e.g. a 180-day window), formatted `YYYY-MM-DD`; use `null` when no
  appeal deadline applies. Anchor the date math on the determination date, not the
  reporting date.
- `basis_audit.source_precedence` = new-patient-specific-P2P-information.

## Finance margin-queue analysis

- Use exactly the `service_margin` rows the memo lists, in the memo's order. Per row:
  `total_cost` = variable_cost + fixed_cost_allocated (per the memo's cost definition);
  `margin` = net_revenue − total_cost; `revenue_to_cost_ratio` = net_revenue / total_cost
  (round to the stated precision); `below_threshold` = ratio < the memo's threshold;
  `charge_sensitive` from the row flag.
- recommended_action: a charge-sensitive row → monitor_charge_sensitive; else a
  below-threshold row → payer_contract_review; else monitor_no_action. (Threshold is
  evaluated first, then charge-sensitivity separates the monitor-only rows — see the
  source-precedence value.)
- below_threshold_segments / charge_sensitive_segments ← the payer segments meeting each
  condition, alphabetical.
- top_issue ← the worst (lowest-ratio) below-threshold row, keyed as `<segment>_<cpt>`;
  `none` if nothing is below threshold. gap_to_120pct (or the stated threshold percent) =
  threshold × total_cost − actual net_revenue for that top issue — a **positive** dollar
  shortfall.
- `basis_audit.source_precedence` = margin-threshold-then-charge-sensitivity; controlling =
  the below-threshold issue row(s), exception = the charge-sensitive rows.

## Choosing `source_precedence`

Match the enum to the decision lever that actually governed the task:
current-clinical-records-over-stale-export · payer-appeal-before-manufacturer-assistance ·
effective-benchmark-by-plan-modifier-and-date · new-patient-specific-P2P-information ·
margin-threshold-then-charge-sensitivity ·
appeal-deadline-then-clinical-then-payment-integrity (for appeal/claim work where an appeal
deadline is the top precedence, then clinical evidence, then payment-integrity).
