# Task Archetypes

Every Northstar work item maps to one archetype. Identify it from the
`requester_role` + `service_domain` + requested output in `prompt.txt` /
`task_context.json`. The archetype fixes the business logic and the
`source_precedence` value (see `basis_audit.md`). Enum vocabularies (recommendation,
route, disposition, letter type, etc.) are defined in the task's
`answer_template.json` — use those exact choices; do not invent values.

## A. UM prior-authorization determination

- **Trigger:** UM nurse reviewer; prior-authorization case; service domains such
  as physical/speech/occupational therapy; output is a determination summary.
- **Review:** case, member, plan, provider, `request_lines`, `policies`,
  `policy_criteria`, `case_criteria`, `documents`, `document_facts`,
  `authorizations`.
- **Logic:** evaluate each applicable policy criterion via `case_criteria`/
  `policy_criteria`. Current clinical documents (`documents.is_current = 1`)
  control the result; a stale/legacy export (`is_current = 0`) is **excluded**.
  Map criteria results to a recommendation/final_status/route per the template
  enums; pull authorized units, start/end dates, CPT list, and modifier from
  `authorizations` when approving. `evidence_documents` = current documents
  relied on (ascending `document_id`); `excluded_documents` = stale/non-relevant
  documents (ascending `document_id`).
- **`source_precedence`:** `current_clinical_records_over_stale_export`.

## B. Pharmacy appeal & manufacturer-assistance intake disposition

- **Trigger:** pharmacy appeals coordinator; coverage appeal for a drug; output
  is an appeal + assistance intake summary.
- **Review:** `appeals`, `drug_trials`, `assistance_screen`, `policies`,
  `policy_criteria`, `case_criteria`, `documents`.
- **Logic:** determine `appeal_path`, `owner`, `expedited`, and
  `appeal_deadline` from `appeals`. Classify prior medication failures from
  `drug_trials`: `documented = 1` → `documented_failures`;
  `documented = 0` (or insufficient) → `undocumented_or_insufficient_failures`
  (both alphabetical by medication). Build `required_packet_items` (payer appeal
  items before assistance items) and `missing_packet_items` (appeal evidence gaps
  before assistance information gaps). Screen assistance from
  `assistance_screen` (`missing_fields`, `denial_required`/`denial_on_file`,
  `income_percent_fpl`). The **payer appeal is resolved before** the
  manufacturer-assistance screen; assistance information gaps are exceptions.
- **`source_precedence`:** `payer_appeal_before_manufacturer_assistance`.

## C. Payment-integrity claim repricing

- **Trigger:** payment integrity analyst; paid claim flagged for benchmark
  validation; output is a correction packet.
- **Review:** `claims`, `claim_lines`, `cases`, `policies`, `payment_benchmarks`,
  `authorizations`.
- **Logic:** select the effective benchmark by `plan_type`, `modifier`,
  `cpt_code`, and service date from `payment_benchmarks`; reject the stale/
  legacy `source_name` as `stale_source_rejected`. For each `claim_line`
  (in `line_number` order): `correct_allowed_amount` = effective benchmark
  `allowed_amount` × `units` (rounded to cents); `recovery_amount` =
  `correct_allowed_amount` − `paid_amount` (use the underpayment amount when
  corrected > paid). `paid_total` from `claims`; `correct_allowed_total` and
  `recovery_amount` are the sum across lines. `modifier` is `null` when absent.
- **`source_precedence`:** `effective_benchmark_by_plan_modifier_and_date`.

## D. Peer-to-peer (P2P) summary

- **Trigger:** peer-to-peer coordinator; completed P2P for an authorization
  case; output is the final P2P file summary.
- **Review:** `p2p_events`, `cases`, `request_lines`, `policies`,
  `policy_criteria`, `case_criteria`, `documents`, `authorizations`.
- **Logic:** record `p2p_outcome` and `final_status` from the P2P event. Set
  `new_information_changed_review` based on whether the event's
  `new_information` materially changed the review. Map applicable criteria
  (e.g. PET-MPI criteria) to results; list `unresolved_criteria` (ascending
  criterion ID) and any remaining factor gaps in template order. If the final
  determination is **adverse**, compute `internal_appeal_deadline` as the final
  adverse determination date plus the plan's internal appeal window given in
  `task_context` (e.g. a 180-day window); otherwise use `null`. Recommend an
  alternative modality when applicable.
- **`source_precedence`:** `new_patient_specific_p2p_information`.

## E. UM-finance margin-queue analysis

- **Trigger:** UM-finance operations analyst; therapy margin queue for a
  reporting period; output is a margin summary.
- **Review:** `service_margin` rows for the period (use **only** the queue row
  IDs listed in `task_context`).
- **Logic:** `total_cost` per the `task_context` definition (e.g.
  `variable_cost + fixed_cost_allocated`); `margin` = `net_revenue − total_cost`;
  `revenue_to_cost_ratio` = `net_revenue / total_cost` (precision per template).
  `below_threshold` when ratio < the `task_context` threshold;
  `charge_sensitive` from the row flag. Separate below-threshold payer-service
  issues (controlling) from charge-sensitive rows (monitored). `top_issue` is the
  lowest-ratio below-threshold row; `gap_to_120pct` = `(threshold × total_cost) −
  net_revenue` for that row. Rows follow the `task_context` queue-row order;
  segment lists are alphabetical.
- **`source_precedence`:** `margin_threshold_then_charge_sensitivity`.

## F. Combined appeal-deadline routing (reserved)

- **Trigger:** a routing/escalation task whose ordering is by appeal deadline,
  then clinical status, then payment-integrity status (not separately represented
  in the train set).
- **`source_precedence`:** `appeal_deadline_then_clinical_then_payment_integrity`.
- Apply the same evidence-gathering and `basis_audit` rules; order the
  precedence trail by deadline first, then clinical, then payment-integrity.
