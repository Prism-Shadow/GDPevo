# Northstar Decision Rules

Per-archetype decision logic and derived-value formulas. These rules generalize across
train/test instances of each archetype; apply them to the records you gather for the target
business ID. **Never copy a specific value from this file — it contains formulas and enums
only.** All enum choices come from the task's `answer_template.json`; if the template
disagrees, follow the template.

## Shared criteria logic

Every criteria-driven archetype (UM, appeal, P2P) uses the same pattern:

- Read `case_criteria` for the target case. Its `result` per `criterion_id` is the
  authoritative criteria result (met / not_met / unclear / not_applicable / partial).
- Cross-check `policy_criteria`: a criterion with `approval_required=1` must be satisfied.
  `result_if_missing` tells you the fallback action when it is not met/unclear:
  - `pend` → the case pends for information (do not auto-deny on this criterion alone).
  - `deny` → an unmet criterion supports a denial.
  - `uphold` → an unmet/absent criterion means a prior adverse decision is upheld.
- `gap_description` (non-empty) signals an exception/gap record for `basis_audit` and often a
  missing packet item or unresolved criterion.
- Optional criteria (`approval_required=0`) inform flags like
  `new_information_changed_review` but do not block approval.

---

## Archetype 1 — UM nurse prior-authorization determination

**Target:** `CASE-*`, therapy service domain, `request_type=prior_authorization`.
**Precedence rule:** `current_clinical_records_over_stale_export`.

Gather: `cases`, `members`, `plans`, `providers`, `request_lines`, `policies`,
`policy_criteria`, `case_criteria`, `documents`, `document_facts`, `authorizations`.

### Decision
- **criteria_results:** map each required criterion ID (e.g. `PT-ACTIVE`, `PT-DEFICIT`,
  `PT-DX`, `PT-POC`, `PT-UNITS`) to its `case_criteria.result`.
- **recommendation / final_status / route / determination_letter / next_action:**
  - All `approval_required` criteria **met** and an authorization record exists with a
    recommending/approved status → `approve` / `approved` / `nurse_approval` /
    `approval` / `issue_approval`.
  - Any `approval_required` criterion **unclear** or `pend`-fallback unmet, with no
    `deny`-level gap → `pend_for_information` / `pended` / `pending_information` /
    `information_request` / `request_more_information`.
  - Any `approval_required` criterion `not_met` whose `result_if_missing=deny` → `deny` /
    `denied` / (`issue_denial`), or `escalate_to_md` / `medical_director_review` when
    policy/urgency requires physician sign-off on a clinical denial.
  - Some requested lines approvable, others not → `partial_approval` /
    `partially_approved` / `partial_approval` (letter) / `partial_approval` (route per
    policy).
- **authorization block:** copy `auth_number`, `approved_units`, `approved_start`,
  `approved_end`, `approved_modifier` from the `authorizations` row. Convert
  `approved_cpt` (comma string) into a list **sorted ascending by CPT code**. For a denial,
  `auth_number` may be null and `approved_units` 0.
- **evidence_documents:** `document_id`s of current (`is_current=1`) documents that carry
  `document_facts` with non-null `supports_criteria` — i.e. documents actually relied on.
  Ascending `document_id`.
- **excluded_documents:** `document_id`s not relied on — stale exports (`is_current=0`),
  irrelevant document types, or documents whose facts support no criterion. Ascending
  `document_id`.

### Source-precedence application
Current clinical documents (eval, plan of care) and their facts override stale exports. The
stale export is the exception record; the current clinical records + authorization are the
controlling records.

---

## Archetype 2 — Pharmacy coverage appeal + manufacturer assistance

**Target:** `APPEAL-*` / `APL-*`, specialty drug, `request_type=coverage_exception`.
**Precedence rule:** `payer_appeal_before_manufacturer_assistance`.

Gather: `appeals`, `assistance_screen`, `drug_trials`, `cases`, `policies`,
`policy_criteria`, `case_criteria`, `documents`, `document_facts`.

### Decision
- **appeal_path / owner / appeal_deadline:** from `appeals`. **expedited:** true when
  `expedited_attestation` indicates a risk attestation was made **or** `appeal_path` is
  `expedited_internal`; otherwise false.
- **documented_failures:** `drug_trials.medication` (lowercase) where `documented=1`,
  sorted alphabetically.
- **undocumented_or_insufficient_failures:** `drug_trials.medication` (lowercase) where
  `documented=0`, sorted alphabetically.
- **criteria_results:** `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES` →
  `case_criteria.result` (note `partial` is possible, e.g. one formulary failure documented,
  a second only referenced without a fill record).
- **required_packet_items:** the packet the policy/appeal requires, ordered **payer appeal
  items before assistance items** (e.g. `denial_notice`, `member_authorization`,
  `prescriber_rationale`, `formulary_failure_evidence`, then `household_income_proof` and
  other assistance items).
- **missing_packet_items:** case-specific gaps, ordered **appeal evidence gaps before
  assistance information gaps**. Map an undocumented drug trial whose fill is missing to the
  fill-record item (e.g. `lurasidone_fill_record`); map a `partial` formulary-failure
  criterion to `formulary_failure_evidence`; map `assistance_screen.missing_fields` to the
  assistance items (e.g. `household_income_proof`).
- **assistance:** `program_name` and `status` (map `assistance_screen.assistance_status` to
  `eligible_ready` / `eligible_missing_information` / `not_eligible` / `not_applicable`);
  `missing_fields` from `assistance_screen.missing_fields` split and sorted alphabetically.
- **next_action:**
  - expedited and the appeal can be completed now while assistance info is still missing →
    `complete_expedited_appeal_and_request_income_proof`;
  - appeal packet incomplete (evidence gap) → `request_more_information`;
  - appeal complete and assistance `eligible_ready` → `submit_assistance_application`;
  - assistance `not_eligible` → `close_not_eligible`;
  - a `deny`-level criterion unmet → `issue_denial`.

### Source-precedence application
The payer appeal (and its evidence gaps) is resolved before manufacturer assistance. The
appeal record + documented failure + met criteria are controlling; the undocumented drug
trial and the assistance missing-fields are exceptions.

---

## Archetype 3 — Claim repricing / payment integrity

**Target:** `CLAIM-*`, imaging/surgery, `request_type=claim_payment_review`.
**Precedence rule:** `effective_benchmark_by_plan_modifier_and_date`.

Gather: `claims`, `claim_lines`, `cases`, `members` (for `plan_type`), `policies`,
`payment_benchmarks`, `authorizations` (for `auth_number` on the claim).

### Decision
- For **each claim line** (in `line_number` order): select the benchmark row matching
  `payer` + `members.plan_type` + `claim_lines.cpt_code` + `claim_lines.modifier` (null
  matches null) whose `[effective_start, effective_end]` **contains** the line's
  `service_date`. Dedup identical rows sharing that natural key.
- **correct_allowed_amount (line)** = `payment_benchmarks.allowed_amount × claim_lines.units`
  (round to 2 decimals after applying units).
- **paid_amount (line)** = `claim_lines.paid_amount`.
- **recovery_amount (line)** = `correct_allowed_amount − paid_amount`.
  - `> 0` → underpayment → disposition `correct_upward`.
  - `< 0` → overpayment → `correct_downward`.
  - `= 0` → `no_change`.
  - A line that should not be paid at all → `deny_line`.
- **modifier:** the line's modifier, or `null` (not `""`) when absent.
- **paid_total** = `claims.paid_total` (== sum of line `paid_amount`).
- **correct_allowed_total** = sum of line `correct_allowed_amount` (2 decimals).
- **recovery_amount (top-level)** = `correct_allowed_total − paid_total`; the template
  specifies using the underpayment amount when the corrected total exceeds the paid total.
- **benchmark_source** = `source_name` of the chosen current schedule;
  **benchmark_version** = its `source_version`.
- **stale_source_rejected** = the `source_name` whose effective window does **not** cover the
  service date (typically a Legacy export that ended before the service date). Use `"none"`
  if no source is rejected.
- **resubmission_route:** `payment_integrity_correction` for normal corrections;
  `provider_adjustment` / `appeal_reopen` / `no_resubmission` where the disposition warrants.
- **priority:** follow the case's operational queue/urgency (`standard` / `expedited` /
  `urgent`); use `monitor_only` when every line is `no_change`.

### Source-precedence application
The effective benchmark — selected by plan type, modifier, and the service date — controls
repricing. The current schedule rows + claim lines are controlling; the stale-source
benchmark row(s) and any non-matching distractor schedule rows are exceptions (rejected).

### Watch-outs
- Duplicate benchmark rows for the same natural key exist in the environment — pick one by
  the effective window, do not double-count.
- "Distractor Schedule" rows carry CPTs/modifiers that match no claim line — ignore them.
- A stale source may coincidentally equal the paid amount (the claim was paid against it);
  that is exactly the signal to reject it.

---

## Archetype 4 — Peer-to-peer final summary

**Target:** `P2P-*`, imaging, `request_type=peer_to_peer`.
**Precedence rule:** `new_patient_specific_p2p_information`.

Gather: `p2p_events`, `cases`, `request_lines`, `policies`, `policy_criteria`,
`case_criteria`, `documents`, `document_facts`, `authorizations`.

### Decision
- **p2p_id:** from `p2p_events`. **requested_cpt:** the CPT from the case's `request_lines`.
- **p2p_outcome:** from `p2p_events.outcome` (`not_applicable` /
  `overturn_to_approval` / `uphold_intended_adverse_decision`).
- **final_status:** from `p2p_events.final_status` / `authorizations.status`
  (`approved` / `denied` / `partially_approved` / …).
- **criteria_results:** map the required criteria (e.g. `PET-IND`, `PET-FACTOR`) to
  `case_criteria.result`.
- **unresolved_criteria:** criterion IDs (approval_required) whose result is `not_met` or
  `unclear`, in ascending criterion-ID order. Empty list if none remain.
- **new_information_changed_review:** true only if the P2P supplied new patient-specific
  information that materially changed the original review (see `p2p_events.new_information`
  and any `*-NEWINFO` criterion). Absence of new factors → false.
- **missing_pet_factors** (and the general "missing factor" pattern): list the policy's
  factor enums that remain unsupported, in the order shown in the template's `choices`
  (e.g. `prior_equivocal_spect`, `bmi_limitation`, `attenuation_artifact`). Include each
  unsupported factor; omit factors that were documented.
- **letter_type:** `approval` / `denial` / `partial_denial` / `no_letter` from final_status.
- **recommended_alternative:** when the requested higher-acuity modality is denied and a
  covered lower-acuity alternative exists (e.g. SPECT MPI when PET MPI is denied), return
  that alternative; otherwise `none`.
- **internal_appeal_deadline:** if the final result is adverse, compute
  `final_adverse_determination_date + <plan internal appeal window>` (the plan window, e.g.
  180 days) → `YYYY-MM-DD`. The final adverse determination date is the P2P/final-status
  date (use `p2p_events.scheduled_at`'s calendar date when no explicit determination date
  exists). Use `null` when no internal appeal deadline applies (e.g. approval).

### Source-precedence application
The controlling question is whether the P2P introduced new patient-specific information that
changes the review. The P2P event + case_criteria + authorization are controlling; the
absent/missing factor facts and unresolved criteria are exceptions.

---

## Archetype 5 — Therapy margin queue

**Target:** `QUEUE-*`, margin rows. **Precedence rule:** `margin_threshold_then_charge_sensitivity`.

Gather: `service_margin` filtered to **only** `task_context.finance_memo.queue_row_ids`
(ignore all `SM-D-*` distractors). Finance definitions come from `task_context.finance_memo`
(`total_cost_definition`, `revenue_to_cost_threshold`, `review_scope`).

### Decision
For each queue row, in the order of `queue_row_ids`:
- **total_cost** = `variable_cost + fixed_cost_allocated` (per `total_cost_definition`).
- **margin** = `net_revenue − total_cost` (2 decimals).
- **revenue_to_cost_ratio** = `net_revenue / total_cost` (4 decimals).
- **below_threshold** = `revenue_to_cost_ratio < threshold` (threshold from
  `revenue_to_cost_threshold`, e.g. 1.2).
- **charge_sensitive** = bool of the `charge_sensitive` column.
- **recommended_action:**
  - `below_threshold` → `payer_contract_review` (margin threshold takes precedence);
  - else `charge_sensitive` → `monitor_charge_sensitive`;
  - else → `monitor_no_action`.
- Row fields: `month_id`, `payer_segment`, `service_domain`, `cpt_code` copied verbatim.

Roll-ups:
- **threshold_revenue_to_cost_ratio** = the threshold (4 decimals).
- **period** = reporting period (`YYYY-MM`) from `task_context`. **case_id** = the queue
  business ID (e.g. `QUEUE-*`).
- **below_threshold_segments:** `payer_segment`s of below-threshold rows, alphabetical.
- **charge_sensitive_segments:** `payer_segment`s of charge-sensitive rows, alphabetical.
- **top_issue:** among below-threshold rows, the one with the **largest dollar shortfall to
  the threshold** (`threshold × total_cost − net_revenue`); format
  `{payer_segment}_{cpt_code}`. If no below-threshold rows, `"none"`. Tiebreak by
  `payer_segment` then `cpt_code`.
- **gap_to_120pct** (or `gap_to_<threshold>pct`): for the top below-threshold row,
  `threshold × total_cost − net_revenue` (2 decimals) — the dollar gap to the threshold.

### Source-precedence application
Margin-threshold classification is applied first (below-threshold rows drive
`payer_contract_review`), then charge sensitivity (charge-sensitive rows drive
`monitor_charge_sensitive`). The queue rows are controlling; the below-threshold shortfall
and charge-sensitive flags are the exceptions that drive recommended actions.

---

## Source-precedence taxonomy (all six rules)

Pick exactly one `source_precedence` per task based on archetype (or, for cross-cutting
tasks, on the controlling factor):

| Rule | When it applies |
|---|---|
| `current_clinical_records_over_stale_export` | UM prior-auth: current clinical/POC documents override stale export documents. |
| `payer_appeal_before_manufacturer_assistance` | Pharmacy appeal: resolve the payer appeal and its evidence gaps before manufacturer assistance. |
| `effective_benchmark_by_plan_modifier_and_date` | Claim repricing: the benchmark effective for the plan type, modifier, and service date overrides stale schedules. |
| `new_patient_specific_p2p_information` | P2P: new patient-specific information from the P2P can change the original review; absence upholds the adverse decision. |
| `margin_threshold_then_charge_sensitivity` | Margin queue: classify by the margin/revenue-to-cost threshold first, then by charge sensitivity. |
| `appeal_deadline_then_clinical_then_payment_integrity` | Cross-cutting tasks where the appeal deadline governs routing priority: deadline → clinical urgency → payment integrity. |
