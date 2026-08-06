# basis_audit reference

Every Northstar payer-operations determination ends with a `basis_audit` object.
It is the auditable trail of which records controlled the result and which
explain gaps or exclusions. The exact required keys are defined in each task's
`answer_template.json`; the structure below is invariant across work types.

## Required keys

- `source_precedence` — the rule that governed which source wins when records
  conflict.
- `controlling_record_ids` — environment record IDs that directly control the
  result, in operational evidence order.
- `exception_record_ids` — record IDs that explain an exclusion, denial,
  missing-information gap, or route priority. Order: criteria / route gaps
  before stale / excluded records when both appear.
- `precedence_record_order` — the controlling and exception records together,
  listed in source-precedence order, highest priority first.

## source_precedence catalog

The catalog of allowed values is defined identically in every `answer_template`.
Pick the one that matches the work type and the conflict at hand:

1. `current_clinical_records_over_stale_export` — current clinical records
   supersede a stale data export.
2. `payer_appeal_before_manufacturer_assistance` — the payer appeal is resolved
   before any manufacturer-assistance path.
3. `effective_benchmark_by_plan_modifier_and_date` — the effective rate schedule
   is selected by plan modifier and date.
4. `new_patient_specific_p2p_information` — new patient-specific information
   supplied during a peer-to-peer discussion governs the review.
5. `margin_threshold_then_charge_sensitivity` — the revenue-to-cost margin
   threshold is applied first, then charge sensitivity.
6. `appeal_deadline_then_clinical_then_payment_integrity` — appeal deadline
   dominates, then clinical status, then payment integrity.

## Choosing the rule

Match the rule to the work type and the conflict at hand, not to a memorized
case:

- A fresh clinical authorization determination where a current clinical record
  supersedes an older export → `current_clinical_records_over_stale_export`.
- A pharmacy coverage appeal with a parallel manufacturer-assistance screen →
  `payer_appeal_before_manufacturer_assistance`.
- Claim repricing where the rate schedule must be the one effective for the plan
  modifier and date → `effective_benchmark_by_plan_modifier_and_date`.
- A peer-to-peer final summary where the discussion introduced new
  patient-specific information → `new_patient_specific_p2p_information`.
- A finance margin queue where you separate below-threshold issues from
  charge-sensitive rows → `margin_threshold_then_charge_sensitivity`.
- A work item that blends appeal-deadline urgency, clinical status, and
  payment-integrity concerns →
  `appeal_deadline_then_clinical_then_payment_integrity`.

Always confirm the chosen value is present in the task's own `answer_template`
`choices` before using it.

## Classifying records

- **Controlling:** a record whose content directly sets a value in the output —
  the authorization line that sets approved units; the rate-schedule row that
  sets the allowed amount; the P2P event that sets the outcome; the margin row
  that sets the ratio; the appeal record that sets the deadline.
- **Exception:** a record that explains why something was excluded, denied,
  pended, missing, or routed a particular way — a stale export rejected as
  superseded; a missing packet item; an unresolved criterion; a charge-sensitive
  flag.
- A record can be controlling for one part of the answer and an exception for
  another. Place it in the list that reflects its primary audit role, and do not
  duplicate it across lists unless the template's ordering rules require it.

## Ordering the lists

- `controlling_record_ids`: operational evidence order — the order in which the
  controlling records were weighed.
- `exception_record_ids`: gap / exception order — criteria or route gaps first,
  then stale or excluded records.
- `precedence_record_order`: source-precedence order, highest-priority source
  first, with controlling records before their related exceptions within the same
  source.

When an entry is a logical gap rather than an environment record ID (e.g. a
missing packet item or an unresolved criterion ID), the Northstar convention is
to use the gap identifier itself in `exception_record_ids` — match whatever
identifier style the work type's records use, and confirm the style against the
records you actually pulled.
