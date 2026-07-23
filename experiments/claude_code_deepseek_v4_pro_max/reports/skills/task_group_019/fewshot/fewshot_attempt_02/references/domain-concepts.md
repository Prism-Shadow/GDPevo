# Domain Concepts Glossary

This file catalogs every code value observed across the training distribution,
organized by semantic category.  When working on a new task, **always read the
template's `allowed_values` — the exact code strings vary between task instances,
even within the same task type.**  This glossary describes the *concept* behind
each code so you can map it to the right evidence.

---

## Deficiency Codes (Contractor Batch)

| Concept | What it means | Evidence source |
|---|---|---|
| Bond not active / cancelled | The applicant has no active bond on file, or the bond was cancelled. | `bonds` — check status and effective dates |
| Bond shortfall | Bond amount is below the required minimum for the license class. | `bonds` amount vs. `policies` minimum |
| Insurance not current / expired | Insurance policy has lapsed or expired as of the review date. | `insurance` — check expiry date against review date |
| Insurance shortfall | Insurance coverage is below the required minimum. | `insurance` amount vs. `policies` minimum |
| Insurance pending | Insurance has been applied for but not yet bound/confirmed. | `insurance` — check binding status |
| Endorsement not verified / missing / pending | A required specialty endorsement is absent, unverified, or still pending. | `applications` endorsements vs. `policies` requirements |
| Experience shortfall | Applicant does not meet the minimum experience threshold. | `applications` experience summary vs. `policies` threshold |
| Active suspension | The applicant has an active license suspension. | `license-history` — check for active suspension records |
| Open minor violation | An unresolved minor violation is on file. | `violations` — check severity and status |
| Open serious violation / unresolved serious complaint | An unresolved serious violation or complaint is on file. | `violations` — check severity and status |
| Inspection document gap | An inspection record is missing required documentation. | `inspections` — check document completeness |
| Inspection safety recheck | A safety re-inspection is required but not completed. | `inspections` — check recheck status |

---

## Required Actions (Contractor Batch)

Each deficiency maps to one or more corrective actions.  The mapping is:

| Deficiency concept | Corrective action concept |
|---|---|
| Bond not active / cancelled | File/obtain a current active bond |
| Bond shortfall | Increase the bond amount to meet the minimum |
| Insurance not current / expired | Provide/renew current insurance |
| Insurance shortfall | Increase insurance coverage |
| Insurance pending | Verify insurance binding |
| Endorsement not verified / missing / pending | Obtain/verify the required endorsement |
| Experience shortfall | Submit/document experience evidence |
| Active suspension | Clear the suspension; may need board review |
| Open minor violation | Resolve through minor violation review |
| Open serious violation / complaint | Resolve the serious violation; may need board review |
| Inspection document gap | Clear the document gap |
| Inspection safety recheck | Complete the safety recheck |

---

## Risk Codes (Liquor Staff Package)

| Code concept | What it means | Evidence source |
|---|---|---|
| AFTER_HOURS | Risk of after-hours service beyond permitted hours. | `incidents`, `privileges` operating hours |
| ASSAULT | Risk of assaults/violence at the premises. | `incidents` — violent incident reports |
| FOOD_SERVICE_GAP | Risk from insufficient food service (for food-service-required licenses). | `site-evidence` — food service documentation |
| MINOR_SALE / SALE_TO_MINOR | Risk of sales to minors. | `incidents` — minor-sale incident reports |
| NOISE | Risk of noise disturbances. | `incidents` — noise complaints |
| PUBLIC_SAFETY | General public safety risk at the premises. | `incidents` — safety-related reports |
| SAME_PREMISES | Risk arising from same-premises license history. | `applications` — premises linkage |
| TAX_HOLD | Risk from an outstanding tax hold. | `settlements` — tax hold status |
| PATIO_BOUNDARY | Risk from patio boundary encroachment or unmarked boundaries. | `site-evidence` — patio/boundary evidence |
| CAMERA_COVERAGE | Risk from insufficient camera coverage. | `site-evidence` — camera evidence |
| ID_CHECK | Risk from inadequate ID verification procedures. | `incidents`, `site-evidence` |

---

## Verification Gap Codes (Liquor Staff Package)

| Code concept | What it means | Evidence source |
|---|---|---|
| Camera evidence missing | No camera footage or camera-system evidence on file. | `site-evidence` — camera category |
| Food service evidence missing | No food service documentation (menus, kitchen photos, service area). | `site-evidence` — food service category |
| Floor plan conflicting / stale | Floor plan on file conflicts with other evidence or is outdated. | `site-evidence` — floor plan category |
| Late night monitoring needed | No evidence of after-hours monitoring controls. | `site-evidence`, `incidents` after-hours |
| Tax hold unresolved | Outstanding tax hold not cleared. | `settlements` — tax clearance |
| Control signage missing / conflicting | Required control signage is absent or conflicts with other records. | `site-evidence` — signage category |
| Police memo conflicting / identity note | Police memo has conflicting information or identity concerns. | `site-evidence` — police memo category |
| Neighbor notice missing | Required neighbor notification is not on file. | `site-evidence` — neighbor notice category |
| Site photo missing | No current site photos on file. | `site-evidence` — photos category |
| Open incident follow-up | An incident report requires follow-up that hasn't happened. | `incidents` — follow-up status |

---

## Standard Obligation Codes (Liquor Staff Package)

These are ordinary license-class obligations, not location-specific:

| Code | What it means |
|---|---|
| CCTV | Must maintain CCTV camera system. |
| DELIVERY | Delivery-only or delivery-hour restrictions. |
| FOOD_SERVICE | Must maintain food service operations. |
| HOURS | Operating-hour restrictions. |
| ID_CHECK | Must verify ID for all patrons. |
| NOISE | Noise-level restrictions. |
| PATIO | Patio-area restrictions. |
| SECURITY | Must provide security personnel. |

---

## Location-Specific Control Codes (Liquor Staff Package)

Same code set as standard obligations, but these are controls *actively tied to
the specific location* (not just class defaults).  Derived from `site-evidence`
and `privileges` for the target location.

---

## First-90-Day Plan Check Codes (Liquor Staff Package)

| Check code concept | When to use | Typical timing |
|---|---|---|
| Camera export test / security walkthrough | Camera evidence was missing or unverified. | `first_30_days` |
| Food service check | Food service evidence was missing. | `first_30_days` |
| Late-night closing visit / after-hours visit | After-hours risk or late-night monitoring needed. | `days_31_60` |
| Noise/patio boundary check | Noise risk or patio boundary concern. | `days_61_90` |
| ID check observation | ID-check risk or minor-sale incidents. | `first_30_days` |
| Control signage recheck / review | Signage was missing or conflicting. | `first_30_days` |
| Tax clearance review | Tax hold is unresolved. | `first_30_days` |
| Police memo follow-up | Police memo was conflicting. | `first_30_days` |
| Incident log review | General monitoring of incident patterns. | `days_61_90` |

**Timing logic:**
- `first_30_days` — urgent verification: missing evidence, conflicting records,
  unresolved holds.
- `days_31_60` — operational observation: after-hours, food service, ID checks
  in live operation.
- `days_61_90` — sustained monitoring: noise patterns, incident trends, ongoing
  compliance.

---

## Escalation Trigger Codes (Liquor Staff Package)

| Code concept | What triggers escalation |
|---|---|
| After-hours violation / service | Evidence of after-hours operation beyond permitted hours. |
| Missing camera coverage | Cameras not installed or not operational. |
| Footage not produced | Operator fails to produce requested camera footage. |
| Food service not available | Food service not being provided as required. |
| Noise or patio breach | Noise complaints or patio boundary violations. |
| Open tax hold uncleared | Tax hold remains unresolved. |
| Unreported violent incident | Violent incident occurred but was not reported. |
| Minor sale / ID check failure | Sale to a minor or ID check failure observed. |
| Board order conflict | Operation conflicts with a board order. |
| Control signage not verified | Required signage cannot be verified. |
| Major incident reported | A major incident has been reported. |
| Referred minor sale unresolved | A referred minor-sale case remains unresolved. |
| Security/CCTV control failure | Security or CCTV system failure. |
| Tax hold reopened | A previously resolved tax hold has been reopened. |

---

## Renewal Queue Concepts (Alcohol)

| Concept | What it means |
|---|---|
| `boundary_date` | The cutoff date; violations after this are excluded from scoring. |
| `match_confidence: exact` | Violation's license number matches the licensee exactly. |
| `match_confidence: close_address` | Match is on address or facility name, not license number. |
| `match_confidence: uncertain` | Match relies on partial or inferred linkage. |
| `manual_fine_check` | Next step: verify fine amounts and payment status. |
| `manual_ALERT_check` | Next step: cross-reference with ALERT system. |
| `board_review` | Next step: escalate to board for review. |
| `additional_record_check` | Next step: pull supplementary records. |
