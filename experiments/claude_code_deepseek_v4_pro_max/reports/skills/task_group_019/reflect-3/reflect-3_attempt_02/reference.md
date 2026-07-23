# Policy Mapping Reference

## Contractor Policy → Trade/Class Mapping

Match applications to policies by combining trade and requested class:

| Trade | Requested Class | Policy Rule Code | Min Bond | Min Insurance | Min Exp | Endorsement |
|---|---|---|---|---|---|---|
| Electrical | Class A | CON-ELE-ClassA | 50,000 | 1,000,000 | 5 | EE-1 |
| Plumbing | Class B | CON-PLU-ClassB | 30,000 | 750,000 | 4 | PH-2 |
| HVAC | Class B | CON-HVA-ClassB | 25,000 | 500,000 | 3 | MECH-H |
| General Building | Class A | CON-GEN-ClassA | 75,000 | 1,000,000 | 5 | GB-A |
| Roofing | Limited | CON-ROO-Limited | 20,000 | 500,000 | 2 | (none) |
| Solar | Specialty | CON-SOL-Specialty | 30,000 | 750,000 | 3 | SOL-PLUS |

All contractor policies set `serious_open_violation_blocks: true`.

## Legacy Baseline Comparison

The legacy policy (`CON-LEGACY`) provides:
- `endorsement_required_for_specialty: false` — specialty trades did not require endorsements under prior rules.
- `minimum_bond_reduction: 10,000` — subtract from the current policy's minimum bond to get the legacy threshold.
- Only bond amounts and specialty endorsements differ between legacy and current policies. Insurance minimums, experience requirements, and serious-violation blocking rules remain the same.

## Deficiency Code → Condition Mapping

| When... | Deficiency Code |
|---|---|
| No active bond exists (cancelled or all expired) | `no_active_bond` / `bond_cancelled` |
| Active bond amount < policy minimum | `bond_shortfall` |
| Insurance status is "pending" | `insurance_not_current` / `insurance_pending` |
| Insurance expiration date < review date | `insurance_expired` |
| Insurance amount < policy minimum | `insurance_shortfall` |
| Endorsement status is "missing" | `endorsement_missing` / `endorsement_not_verified` |
| Endorsement status is "pending" | `endorsement_pending` / `endorsement_not_verified` |
| Years experience < policy minimum | `experience_shortfall` |
| Prior license status is "suspended" | `active_suspension` |
| Open violation, severity "serious" | `open_serious_violation` / `unresolved_serious_complaint` |
| Open violation, severity "minor" | `open_minor_violation` |
| Inspection finding "DOC_GAP" | `inspection_doc_gap` |
| Inspection finding "SAFETY_RECHECK" | `inspection_safety_recheck` |

## Control → Risk Coverage Mapping (Liquor)

| Active Control | Risk Covered |
|---|---|
| `ID_CHECK` | `MINOR_SALE`, `SALE_TO_MINOR` |
| `HOURS` | `AFTER_HOURS` |
| `SECURITY` | `ASSAULT`, `PUBLIC_SAFETY` |
| `CCTV` | `CAMERA_COVERAGE` |
| `FOOD_SERVICE` | `FOOD_SERVICE_GAP` |
| `NOISE` | `NOISE` |
| `PATIO` | `PATIO_BOUNDARY` |

## Evidence Status → Verification Gap Mapping (Liquor)

| Evidence Status | Gap Code |
|---|---|
| `conflicting` (FLOOR_PLAN) | `floor_plan_conflicting` |
| `conflicting` (CONTROL_SIGNAGE) | `control_signage_conflicting` |
| `conflicting` (POLICE_MEMO) | `police_memo_conflicting` |
| `missing` (CONTROL_SIGNAGE) | `control_signage_missing` |
| `missing` (SITE_PHOTO) | `site_photo_missing` |
| `missing` (NEIGHBOR_NOTICE) | `neighbor_notice_missing` |
| `stale` (FLOOR_PLAN) | `floor_plan_stale` |
| `stale` (any) | `floor_plan_stale` or task-specific stale code |

## Data Interpretation Heuristics

1. **Trust explicit status fields over computed conditions.** If insurance has `status: "active"`, treat it as active even if the expiration date appears to have passed. The data source's status field is authoritative.

2. **Violation dates vs resolved dates.** When `resolved_date` precedes `violation_date`, the data contains a temporal inconsistency. Default to the explicit `status` field (`"resolved"` means resolved), but note the anomaly.

3. **Self-disclosed issues are not deficiencies by themselves.** An applicant disclosing "prior complaint" or "late bond certificate" is informational. Only verified data from bonds, insurance, violations, and license history endpoints creates deficiencies.

4. **Inspections with result "pass" but concerning finding codes.** A "pass" result with finding code `SAFETY_RECHECK` or `UNVERIFIED_SITE` still passes. Only use finding codes that directly map to template deficiency codes.

5. **Correspondence staleness.** Two independent signals: `verified_by_agency: 0` (unverified) and `notes` containing "Stale attachment predates application" (stale). Either qualifies.
