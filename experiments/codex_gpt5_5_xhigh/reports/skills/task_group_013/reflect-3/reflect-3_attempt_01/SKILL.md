---
name: cedar-ridge-intake-reconciliation
description: Reconcile Cedar Ridge-style healthcare intake tasks into strict JSON outputs. Use when Codex must audit patient access, referral readiness, dialysis transfer packets, chronic-care program enrollment, or referral-to-chart activation from structured patient, insurance, pharmacy, clinical, document, capacity, ICD, referral, transfer, program, and chart-artifact records.
---

# Cedar Ridge Intake Reconciliation

## Core Workflow

1. Read the user prompt and answer template first. Treat the template as authoritative for required keys, enum values, nullability, list ordering, and summary count keys.
2. Build a focused working set for only the requested roster, batch, program, or cohort. Join each target row to the relevant patient profile, clinical history, coverage, PBM, pharmacy, lifestyle, ICD metadata, documents, capacity rows, program-candidate rows, and chart artifacts.
3. Normalize every output value to the template enums. Use empty arrays for no issues, `null` only where the template allows it, and compute all summaries from the final normalized patient/referral/transfer rows.
4. Sort rows exactly as requested. Treat issue-code arrays as sets unless the template says otherwise.
5. Before returning, verify totals and cross-field consistency: status counts must match row statuses, blocker sets must match per-row blocker codes, ready lists must contain only rows with no unresolved readiness blocker, and artifact/action lists must match the final disposition.

## Access And Insurance Intake

Classify insurance as valid only when coverage is active on the requested service date, in network, and includes the requested service line. Mark expired, pending, excluded-service-line, or absent coverage with the corresponding controlled blocker code.

Classify prescription benefit as valid only when the PBM record is active/approved, the formulary is covered, and payer/policy match the medical coverage. Use PBM invalid, missing, or policy-mismatch blockers for the specific failure.

Classify preferred pharmacy from the top-ranked pharmacy network status. Use out-of-network or unknown blockers when applicable.

Treat missing address, missing emergency contact, and unavailable preferred contact channel as administrative blockers. A preferred phone or SMS route requires a phone number; a preferred email route requires an email address.

Use lifestyle factors to assign lifestyle risk: current smoking, heavy alcohol use, no exercise, missing exercise, and short sleep increase risk. Escalate overall risk for high lifestyle risk, recent hospital or ED flags, complex risk flags, or high medication burden. High overall risk should route to clinical review unless a stronger rejection rule applies.

Use disposition precedence consistently:

- Reject for expired coverage, excluded service line, wrong target condition, or declined consent when those are terminal for the task.
- Hold for pending or missing administrative items that can be repaired.
- Clinical review for high clinical risk or stale clinical material when administrative eligibility is otherwise plausible.
- Approve or accept only when there are no unresolved blockers.

## Referral Readiness

For each referral, compare ICD metadata to the requested service line and referral narrative:

- Use a clinical-code discrepancy when the ICD service family conflicts with the service line.
- Use chapter mismatch when the task expects a narrower clinical chapter than the observed ICD chapter.
- Use narrative mismatch when the referral reason or diagnosis narrative describes a different clinical intent than the ICD.
- Use laterality mismatch when a laterality-specific code conflicts with, or is unsupported by, the narrative.

Apply operational blockers directly from referral and document evidence:

- Missing records or imaging block readiness.
- Authorization statuses of denied, pending, or not submitted block readiness when authorization is required.
- Already scheduled referrals need administrative follow-up if clearance is not complete.
- Duplicate referrals are same-patient or same-clinical-request repeats; choose a primary/kept referral and route duplicates for consolidation.
- Shared insurance IDs across distinct patients require verification; the same insurance ID on a true same-patient duplicate can be legitimate but still belongs in duplicate handling if the template asks for it.

Use readiness precedence:

- `blocked` for missing records, missing imaging, or authorization blockers.
- `under_review` for clinical-code, narrative, laterality, or distinct-patient insurance anomalies without hard document/auth blockers.
- `admin_followup` for duplicate consolidation or already-scheduled review.
- `ready` only when no blocker or review issue remains.

Map action plans and correspondence from the same normalized issue set. Do not invent free-text reasons when the template gives controlled codes.

## Dialysis Transfer Packets

Treat only finalized packet documents as present. Draft or non-final documents count as missing. A missing transportation value counts as a missing required packet item when transportation is listed in the template.

For freshness checks, compare the document `received_date` to the requested start date or task as-of date, using the limit implied by the task/template. Report stale documents separately from missing documents; a complete packet can still be stale.

Capacity is date- and modality-specific. Sum open chairs across locations for the requested start. If no capacity row exists for the requested date/modality, treat open chairs as zero and capacity as unavailable.

Set feasibility from packet readiness and capacity:

- Complete, fresh, and capacity available: ready on requested start.
- Packet not ready and capacity available: packet-not-ready/capacity-available.
- Packet not ready and capacity unavailable: packet-not-ready/capacity-unavailable.
- Packet ready but capacity unavailable: capacity-unavailable.

Use intake coordination for missing administrative packet items, clinical nursing for stale clinical packet review, scheduling coordination for pure capacity constraints, and `none` only for fully ready/accepted transfers.

## Chronic-Care Program Panels

Separate clinical eligibility from enrollment disposition. A candidate can meet program clinical criteria yet be held or rejected because of consent, chart state, or missing artifacts.

For DM/HTN-style panels:

- Eligible candidates should have the target condition and active diabetes plus hypertension evidence.
- Wrong target condition or missing active DM/HTN diagnosis makes the candidate ineligible.
- Declined consent is terminal; missing consent is a hold when clinical eligibility remains plausible.
- Inactive chart status and stale or absent chart artifacts should produce the corresponding chart reason codes and missing artifact list.

Choose cadence by highest-touch need:

- Weekly for recent hospitalization, recent ED, or low adherence.
- Biweekly for CKD monitoring when no weekly trigger overrides it.
- Monthly for standard enrolled candidates.
- Deferred for held candidates awaiting consent or chart repair.
- None for rejected candidates.

Use high-touch packages for weekly patients, standard packages for routine enrolled patients, deferred packages for held patients, and not-applicable packages for rejected patients. Include consent packets and chart-update requests only when they correspond to the disposition.

## Chart Activation

For referral-to-chart activation, determine whether each ready referral needs chart creation, chart update, or no chart action:

- Create a chart when no active chart exists.
- Update the chart when required artifacts are stale or missing.
- No chart action only when an active chart has current required artifacts.

Build artifact lists from missing or stale chart artifacts, using only the artifact enum strings allowed by the template. Keep chart work aligned with readiness: ready referrals may still need activation artifacts, while blocked referrals should remain in the blocker/correspondence workflow until cleared.
