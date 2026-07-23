# Policy Baseline & Field Mappings

## Contractor policy lookup

Key by `(trade, requested_class)`. Thresholds live in `policies.details_json`:
`minimum_bond`, `minimum_insurance`, `minimum_years_experience`, `required_endorsement`
(may be `null` ⇒ no endorsement required), `serious_open_violation_blocks`.

| trade | requested_class | rule_code | endorsement |
|---|---|---|---|
| Electrical | Class A | CON-ELE-ClassA | required |
| Plumbing | Class B | CON-PLU-ClassB | required |
| HVAC | Class B | CON-HVA-ClassB | required |
| General Building | Class A | CON-GEN-ClassA | required |
| Roofing | Limited | CON-ROO-Limited | `null` (not required) |
| Solar | Specialty | CON-SOL-Specialty | required (specialty) |

The **prior baseline** (`CON-LEGACY`) differs in exactly two ways:
`endorsement_required_for_specialty = false`, and bond minimum reduced by
`minimum_bond_reduction`. These two differences are the **only** sources of
`policy_impacted = true` (see SKILL.md §4).

## `policy_impacted` decision table (contractor)

| Condition | policy_impacted |
|---|---|
| Specialty trade endorsement deficiency (e.g. Solar) — endorsement not required under baseline | **true** |
| Bond shortfall with amount `∈ [min − reduction, min)` (would have passed under baseline) | **true** |
| Bond fails both baselines (no active bond, or amount `< min − reduction`) | false |
| Non-specialty endorsement deficiency (EE-1/PH-2/MECH-H/GB-A) | false |
| Insurance shortfall / expired / not-current | false |
| Experience shortfall | false |

## Deficiency ↔ remediation action (use the task's own enum!)

The contractor tasks use **different** vocabularies. Pick the pair that exists in the
current task's `answer_template.json`. Typical pairings:

| Observation | "current-bond" vocabulary (task A) | "legacy-bond" vocabulary (task B) |
|---|---|---|
| no active bond | `bond_cancelled` → `obtain_current_bond` | `no_active_bond` → `file_active_bond` |
| bond amount below min | `bond_shortfall` → `increase_bond_amount` | `bond_shortfall` → `increase_bond` |
| insurance status pending/expired | `insurance_pending`/`insurance_expired` → `verify_insurance_binding`/`provide_current_insurance` | `insurance_not_current`/`insurance_expired` → `provide_current_insurance`/`renew_insurance` |
| insurance amount below min | `insurance_shortfall` → `increase_insurance_amount` | `insurance_shortfall` → `increase_insurance` |
| endorsement missing/pending | `endorsement_missing`/`endorsement_pending` → `obtain_required_endorsement`/`verify_pending_endorsement` | `endorsement_not_verified` → `verify_endorsement` |
| experience below min | `experience_shortfall` → `submit_experience_evidence` | `experience_shortfall` → `document_experience` |
| active suspension | `active_suspension` → `board_review_suspension` | `active_suspension` → `clear_suspension` / `board_review` |
| open serious violation | `open_serious_violation` → `resolve_serious_violation` | `unresolved_serious_complaint` → `resolve_complaint` / `board_review` |
| open minor violation | `open_minor_violation` → `resolve_minor_violation_review` | *(no direct code — handle via hold)* |
| inspection finding | `inspection_doc_gap`/`inspection_safety_recheck` (only if in enum) | *(often no inspection code in enum)* |

## Determination (contractor)

- **DENY** — blocking: serious open violation when `serious_open_violation_blocks`, or an
  active suspension that blocks issuance outright.
- **APPROVE** — no deficiencies under the task's enum (a non-coded inspection flag does
  not block).
- **HOLD** — everything else (curable shortfalls, missing/pending endorsement, expired
  insurance, no active bond, open minor violation).

## Renewal rule flags (from `renewal_rules.details_json`)

- `use_violations_on_or_before` / `release_boundary` — only violations dated `<=` boundary
  count; later rows (the `*-LATE` distractors) are excluded.
- `late_rows_are_distractors` — confirms `*-LATE` rows are noise.
- `unpaid_fines_require_hold` — `fine_balance > 0` ⇒ `manual_fine_check`.
- `alert_flag_requires_manual_review` — `alert_flag = 1` ⇒ manual review.
- `POL-REN-001`: `exact_license_match_preferred`, `successor_match_mark_uncertain`,
  `known_on_or_before_boundary_only`.

## Liquor settlement parsing

Each `liquor_settlements.controls_json` = `{active: bool, controls: [obligation_codes],
expires: YYYY-MM-DD, review_required: bool}`. Per location there is exactly one **active**
settlement (`active: true`, future `expires`) carrying the current controls; the rest are
historical. Derive `location_specific_control_codes` from the active settlement's
`controls` only. `same_premises_basis_applies` requires an **active** `SAME_PREMISES`
settlement.
