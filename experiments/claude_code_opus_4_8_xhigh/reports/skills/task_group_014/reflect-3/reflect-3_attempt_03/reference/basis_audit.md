# Filling `basis_audit`

Most answer templates require a `basis_audit` object with four keys. Fill all four; they document
*why* the result holds and which records drove it. Keep the whole object present and well-formed.

Required keys:

- **`source_precedence`** — the single rule (from the template's enum) that governs how competing
  records were prioritized. Choose it by task family:

  | Task family | `source_precedence` value |
  |---|---|
  | Prior-auth / UM determination (current clinical vs. stale export) | `current_clinical_records_over_stale_export` |
  | Coverage appeal + manufacturer assistance | `payer_appeal_before_manufacturer_assistance` |
  | Claim repricing against a rate schedule | `effective_benchmark_by_plan_modifier_and_date` |
  | Peer-to-peer closure | `new_patient_specific_p2p_information` |
  | Margin-queue analysis | `margin_threshold_then_charge_sensitivity` |
  | Appeal triage weighing deadline, then clinical evidence, then payment integrity | `appeal_deadline_then_clinical_then_payment_integrity` |

- **`controlling_record_ids`** — the environment record IDs that directly control the result,
  in operational evidence order. These are the current/effective records you relied on: the
  current supporting documents, the adjudicated authorization/appeal/P2P record, the effective
  benchmark rows, or the queue rows that produced the finding.

- **`exception_record_ids`** — the gap/exception records that explain exclusions, denials,
  missing information, or route priority: stale/superseded documents, expired or distractor
  benchmark rows, undocumented failures, missing-information screens, or the criterion that is
  not met. Order gap/criteria records before stale/excluded records when both appear.

- **`precedence_record_order`** — the union of the controlling and exception records, listed in
  `source_precedence` order (highest-priority records first — current/effective/controlling
  records ahead of stale/excluded/exception records).

Use real IDs from records you retrieved (document_id, auth_id, appeal_id, benchmark_id, p2p_id,
month_id, trial_id, etc.). Keep the object internally consistent with the substantive fields:
whatever you called evidence/current in the answer should appear as controlling, and whatever you
excluded or flagged as a gap should appear as an exception.
