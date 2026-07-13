---
name: clrp-regulatory-review
description: Use for Cascadia Licensing Review Portal (CLRP) tasks that require JSON-only contractor eligibility decisions, restricted alcohol license monitoring plans, or renewal manual-review queues from public CLRP APIs, exports, and task answer templates.
---

# CLRP Regulatory Review

Use this skill when a task references CLRP, Harbor State contractor batches, restricted alcohol licensing, premises monitoring, or renewal manual-review queues.

## Core Workflow

1. Read the task prompt and answer template first. Extract target IDs, batch/review month, cutoff or boundary dates, required top-level keys, enum values, sort order, and whether extra properties are forbidden.
2. Use only the CLRP base URL supplied by the task and public CLRP APIs/exports. Replace any placeholder with the supplied base URL. Do not rely on unprovided local artifacts or generated environment state.
3. Enumerate the universe of records before deciding: every application in a batch/month, every current renewal licensee in a release batch, or the target premises plus comparison records requested by the prompt.
4. Pull related evidence by stable IDs first, then by legal/principal names, premises IDs, cities, addresses, or roster names as the domain requires. URL-encode query values.
5. Treat API responses as data feeds, not guarantees that filters were applied. Check `count`, `data`, and `meta`; if an endpoint ignores a query parameter, filter client-side against the requested IDs/month/batch.
6. Build the JSON from the answer template, then validate: required keys only, controlled enum spelling/case, integer counts, booleans as booleans, dates in the requested format, and no narrative or Markdown.

## Useful Public Surfaces

Contractor review surfaces commonly include:

- `GET /api/contractors/applications?batch_id=<batch>`
- `GET /exports/contractor_batch_<batch>.csv`
- `GET /api/contractors/bulletins?effective_on=<YYYY-MM-DD>`
- `GET /api/contractors/bonds?name=<legal_or_principal_name>`
- `GET /api/contractors/insurance?name=<legal_name_or_policy>`
- `GET /api/contractors/violations?name=<legal_or_principal_name>`
- `GET /api/contractors/complaints?name=<legal_name>`
- `GET /api/contractors/field-notes?name=<legal_name>`
- `GET /api/contractors/correspondence?batch_id=<batch>`

Alcohol review surfaces commonly include:

- `GET /api/alcohol/applications?review_month=<YYYY-MM>`
- `GET /api/alcohol/premises?premises_id=<premises_id>`
- `GET /api/alcohol/incidents?premises_id=<premises_id>`
- `GET /api/alcohol/settlements?premises_id=<premises_id>`
- `GET /api/alcohol/restrictions?premises_id=<premises_id>`
- `GET /api/alcohol/standard-obligations?license_type=<license_type>`

Renewal queue surfaces commonly include:

- `GET /api/renewals/licensees?release_batch=<batch>`
- `GET /exports/renewal_roster_<batch>.csv`
- `GET /api/renewals/violations?city=<city>`
- Use any task-named address search endpoint only if the public API exposes it.

## Contractor Eligibility Rules

For each contractor application, compare application declarations with verified records and active bulletins as of the review cutoff date.

- `APPROVE` only when no verified deficiency remains; use `NO_DEFICIENCY`, empty bulletin/action lists where the template expects them, and no manual follow-up.
- `HOLD` for remediable or staff-review deficiencies: bond shortfall, cancelled/missing bond, insurance verification/replacement issue, unresolved penalty or complaint/violation ledger item, field note hold, experience/exam/financial shortfall, correspondence hold, or adverse prior registration needing file review.
- `DENY` when the evidence shows disqualifying conduct or an uncurable denial basis. A denial basis should not be diluted by routine hold actions unless the template explicitly asks for all issues.
- Bond shortfall is based on the active verified bond amount compared with the trade-specific minimum in effect on the cutoff date, not just the declared amount.
- Bond cancelled means the current bond record is cancelled, expired, or lacks a valid replacement as of the cutoff.
- Insurance verification applies when carrier/policy evidence is missing, expired, mismatched, below an active minimum, or requires carrier attestation.
- Unresolved penalties include unpaid, pending, blank-disposition, or otherwise unresolved violations/complaints/correspondence that block clearance.
- Field notes that request hold, clearance, inspection, or staff review create a field-note hold until affirmatively cleared.
- Prior adverse registration and non-clear background statuses require explicit prior-file/manual review when the template supports that reason.

Bulletin handling:

- `applicable_bulletin_ids` are all bulletins effective on or before the cutoff that apply to the batch/trades requested, sorted by bulletin ID.
- `primary_bulletin_ids` belong only on applications whose deficiency is driven by a current bulletin. Do not attach every applicable bulletin to every deficient application.
- For changed-by-bulletin summaries, compare the current 2026 rule to the bulletin's prior rule/threshold. Include only applications whose determination or reason would differ under the prior rule.
- Count bulletin impacts by rule type from deficiencies actually attributable to those bulletin rules.

Contractor follow-up mapping:

- `ADVERSE_PRIOR_REGISTRATION` -> `PRIOR_REGISTRATION_FILE_REVIEW`
- `BOND_CANCELLED` -> `BOND_REPLACEMENT_REQUIRED`
- `BOND_SHORTFALL` -> `BOND_INCREASE_REQUIRED`
- `INSURANCE_VERIFY` -> `CARRIER_VERIFICATION_REQUIRED` or `INSURANCE_REPLACEMENT_REQUIRED`, depending on whether the issue is verification/attestation or invalid replacement coverage.
- `FIELD_NOTE_HOLD` -> `INSPECTOR_CLEARANCE_REQUIRED`
- `UNRESOLVED_PENALTY` -> `PENALTY_LEDGER_REVIEW`
- `EXPERIENCE_VERIFY` -> `EXPERIENCE_DOCUMENTATION_REQUIRED`
- `FINANCIAL_STATEMENT_MISSING` -> `FINANCIAL_STATEMENT_REQUIRED`
- `CORRESPONDENCE_HOLD` -> `MATERIAL_CORRESPONDENCE_REVIEW`

When a template has a single `next_action`, use the specific action for a single hold reason and the combined-review action for multiple remediable hold reasons. When it has `manual_followup`, include only applications that require staff action and sort by application ID.

## Restricted Alcohol License Rules

Center target-application work on the target premises, then use same-month applications only for comparison fields or to distinguish standard obligations from premises-specific restrictions.

- Same-premises risk comes from premises records, same address/service-area overlap, prior licensee evidence, prior/current settlements, and incidents tied to the premises.
- Count incidents from the relevant premises feed. Treat `pending` and blank dispositions as unresolved. Count high severity from the `severity` field.
- Prior incident level is driven by severity, unresolved count, and total incident history. Multiple incidents with pending items or any serious/high-severity item generally push risk above low.
- Settlement posture reflects actual settlement records: none, prior warning with controls, prior restricted/denial posture, or current settlement.
- Control coverage is `ADEQUATE_LOCATION_SPECIFIC` only when current/proposed premises-specific controls cover the premises risks. Use `STANDARD_ONLY` when the file has only all-license, license-type, or proposed standard obligations. Use `NO_CONTROLS` when neither standard nor premises controls exist.
- Verification gaps should identify missing age-verification controls, missing late-night/security controls, pending police-call dispositions, security-plan lapse disposition gaps, missing settlement terms, successor-control separation gaps, and standard-control overlap when relevant. Use the template's exact enum values.
- Recommendations should follow risk and control posture: request follow-up when material controls or records are missing before issue; issue restricted with monitoring when controls and first-90-day monitoring can mitigate the risk; deny only for severe, unmitigated, or disqualifying evidence.

Controls and obligations:

- Standard obligations come from all-license obligations, license-type obligations, and restriction records whose category is standard-obligation. Keep them separate from premises-specific restrictions.
- Premises-specific controls come from premises-specific restrictions, settlement terms, and incident-driven monitoring needs. Attach stable source IDs from restrictions, incidents, settlements, or premises records.
- For first-90-day monitoring, map age checks to device audits, late-night disorder to police-call/service-log review, security plan lapses to security-log review, and inspection/settlement conditions to site inspection or inspection calendar checks.
- Records requests should ask for the evidence needed to close gaps: device audits, standard-obligation evidence, first-90-day inspection calendars, pending incident disposition packets, prior-licensee settlement packets, police call histories, and successor ownership/service-area statements.
- Escalation triggers should correspond to failed or missing age checks, missed first-90-day checks, new/confirmed high-severity incidents, pending incidents confirmed as violations, or confirmed successor links to a problematic prior licensee.

## Renewal Queue Rules

Use the current release roster as the population. The output queue must contain only current roster licensees for the requested release batch.

- Pull the roster from the licensee API and verify with the CSV export when available.
- Collect violation records by each roster city, then match to roster licensees by exact facility/legal name and address first. Use successor hints, normalized abbreviations, and close historical names for close matches.
- `match_confidence` is `exact` for stable name/address matches, `close` for normalized name or successor-hint matches, and `shared_address_manual` only when the address overlaps but the name evidence is not strong enough.
- Do not spread shared-address violations across unrelated current licensees. Shared-address evidence requires manual confidence and should not inflate unrelated counts.
- Exclude violation records with `violation_date` after the release boundary from ranking evidence, and count those exclusions. Records on or before the boundary can be used.
- Rank the top manual-review candidates by pre-boundary risk evidence: count of matched violations, high severity, unresolved/pending or blank dispositions, board sanctions, unpaid fines, ALERT-related records, and recency. The final rank is business-significant and must be consecutive starting at 1.
- `next_step_label` should reflect the dominant manual work: unpaid or fine-collection evidence -> `manual fine check`; ALERT pattern/alert-related evidence -> `manual ALERT check`; serious sanctions, high-severity safety/minor-service history, or repeated violations -> `board review`; weak/ambiguous evidence -> `additional record check`.

## Output Conventions

- Return exactly one JSON object. No prose, comments, Markdown fences, or explanatory fields.
- Preserve required constants from the template: task ID, batch ID, target application/premises ID, review month, cutoff date, release batch, and boundary date.
- Use the template's enum order for `reason_codes` and follow-up codes when specified. Do not reuse enum order from a different template.
- Sort by the template's requested key: application IDs ascending, bulletin IDs ascending, gap/control/request/trigger codes ascending, source IDs ascending, or rank ascending.
- Include zero-valued enum counts when the template requires a full count object.
- Use empty lists for no applicable IDs/gaps only when the template permits them; otherwise use the template's explicit no-gap enum.
- Use source IDs, not narrative evidence, in `source_ids` fields.
- Counts must reconcile with arrays: reviewed applications, determination counts, reason-code counts, queue size, manual-followup count, changed-by-bulletin count, and post-boundary exclusion count.

## Pitfalls

- Do not clear an application from declarations alone; verify bonds, insurance, penalties, notes, correspondence, and prior records.
- Do not treat standard alcohol obligations as premises-specific restrictions.
- Do not ignore pending or blank incident/violation dispositions.
- Do not attach all bulletins to every contractor deficiency; separate applicable bulletins from decision-driving bulletins.
- Do not include post-boundary renewal violations in ranking, even if they are severe.
- Do not let an API's broad response leak unrelated applications, months, batches, cities, or licensees into the answer.
- Do not add fields from one schema version to another similar-looking task.
