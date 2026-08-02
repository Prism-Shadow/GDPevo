# Family B — Restricted liquor-license staff package

Goal: one JSON object for the target `L-…` application at its `LOC-…` location:
`recommended_posture`, `same_premises_basis_applies`, `covered_risk_codes`,
`verification_gap_codes`, `standard_obligation_codes`,
`location_specific_control_codes`, `first_90_day_plan`,
`escalation_trigger_codes`.

**Bind to the current template's vocabulary.** Sibling tasks differ: one uses
uppercase gap codes (`FLOOR_PLAN_STALE`, `TAX_CLEARANCE_MISSING`) and risk codes
like `SAME_PREMISES`; another uses lowercase (`camera_evidence_missing`,
`tax_hold_unresolved`) and risk codes like `CAMERA_COVERAGE`, `PATIO_BOUNDARY`.
Read `answer_template.json` and only emit codes it lists.

## Gather

- The application row (for `license_class`).
- Settlements, incidents, and site-evidence for the `location_id`.
- Privileges for the `license_class`.
- Liquor policies (`LIQ-SETTLEMENT-CONTROLS`, `LIQ-RISK-MATRIX`) — read
  `details_json` toggles.

## Field logic

1. **same_premises_basis_applies** — `true` when an active `SAME_PREMISES`-basis
   settlement exists for the location and `same_premises_history_matters` is set,
   i.e. the restricted issuance rests on same-premises history. Otherwise `false`.

2. **standard_obligation_codes** — the ordinary obligations for the license
   class: privileges with `standard_required = 1` for that `license_class`. These
   are class-wide requirements, kept **separate** from location controls
   (`standard_privileges_separate_from_controls`).

3. **location_specific_control_codes** — the controls tied to *this location* by
   its **active** settlements: parse `controls_json`, take entries where
   `active = true`, and collect their `controls`. Exclude expired/inactive
   settlements.

4. **covered_risk_codes** — location risks that are actually addressed by a
   current active control. Derive candidate risks from incidents (`risk_code`)
   and settlement `basis_code`; keep a risk as "covered" when an active
   location control maps to it (e.g. AFTER_HOURS↔HOURS, NOISE↔NOISE,
   SALE_TO_MINOR/MINOR_SALE↔ID_CHECK, ASSAULT/PUBLIC_SAFETY↔SECURITY/CCTV,
   FOOD_SERVICE_GAP↔FOOD_SERVICE, patio issues↔PATIO). Map into the template's
   risk vocabulary; include the same-premises risk code when the template
   provides one and the basis applies.

5. **verification_gap_codes** — evidence and follow-up shortfalls:
   - `liquor_site_evidence` with `status` in {missing, stale, conflicting}, mapped
     by `evidence_code`+status to the template gap (e.g. FLOOR_PLAN+stale →
     floor-plan-stale/conflicting; SITE_PHOTO+missing → site-photo-missing;
     CONTROL_SIGNAGE missing/conflicting; POLICE_MEMO conflicting/identity note;
     NEIGHBOR_NOTICE missing; TAX_CLEARANCE missing).
   - Open incidents needing follow-up → the open-incident-follow-up code.
   - An unresolved TAX_HOLD → the tax-hold/tax-clearance gap code.
   - Any risk without a current active control → its "not verified / needed"
     gap (e.g. late-night monitoring needed, camera evidence missing).

6. **first_90_day_plan** — one `{check_code, timing}` object per gap/risk that
   needs verification, using the template's `check_code` and `timing`
   (`first_30_days` / `days_31_60` / `days_61_90`) vocabularies. Front-load the
   highest-risk / hard-blocking checks into `first_30_days`. Follow the template's
   ordering (sort by `check_code`, or "operational sequence") and dedupe
   check/timing pairs.

7. **escalation_trigger_codes** — the conditions that send field staff back to
   the board: unresolved major/serious incidents
   (`major_incidents_trigger_board_review`), an uncleared tax hold, control/CCTV
   failure, after-hours service, unresolved minor-sale referral, etc. — mapped to
   the template's escalation vocabulary.

8. **recommended_posture**
   - **issue_restricted** — required controls are in place and only routine
     monitoring/minor gaps remain.
   - **request_follow_up** — material verification gaps remain (missing/stale
     evidence, unverified controls) that must be closed before issuance.
   - **deny** — a serious unresolved problem (major incident, control failure the
     applicant cannot cure, disqualifying history).

## Consistency checks

- A risk cannot be in both `covered_risk_codes` and left as an uncovered gap for
  the same control unless the evidence genuinely conflicts.
- Every code appears at most once per array; sort/dedupe per the template
  (some templates say "any order," others "sort ascending").
- The `first_90_day_plan` should cover the gaps you listed and the risks you
  flagged for monitoring.
