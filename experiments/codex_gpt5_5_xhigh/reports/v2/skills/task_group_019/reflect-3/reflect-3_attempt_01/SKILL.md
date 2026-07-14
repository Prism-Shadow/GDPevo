---
name: clrp-licensing-review
description: Review CLRP contractor, renewal, and restricted alcohol licensing records and produce schema-exact JSON decisions, queues, and monitoring plans.
---

# CLRP Licensing Review

Use this skill when a task asks for a Cascadia Licensing Review Portal (CLRP) eligibility review, renewal manual-review queue, restricted alcohol license review, or monitoring plan.

## General API Habits

- Use only the CLRP base URL and public API/export surfaces named or implied by the task. Replace any task placeholder base URL exactly as instructed.
- Read the task prompt and answer template first. Treat template enum values, required keys, ordering, boolean types, and count definitions as controlling.
- Pull the primary roster first: contractor batch applications/export, renewal roster, or alcohol application/premises record. Then gather related records by stable identifiers: batch_id, application_id, premises_id, city, address, legal name, principal name, or release batch as the task permits.
- Keep date boundaries strict. Exclude records after an explicit review cutoff or release boundary from eligibility/ranking calculations, but include them as timing gaps only when the output schema has a field for that issue.
- Return JSON only. Do not add prose, markdown, comments, unrequested evidence text, or extra fields.

## Contractor Eligibility Rules

- Include every application in the requested contractor batch, sorted by `application_id`, and no applications outside the batch.
- Match surety and insurance records to the current legal entity first. Use principal-name records only when the task asks for related principal history or successor/adverse-prior review; do not let unrelated future applications or distractor surety records clear or block the current file.
- Apply active bulletins effective on or before the review date. Use `trade_scope: ALL` for all trades and trade-specific bulletins only for matching trades.
- Bond deficiencies:
  - `BOND_CANCELLED` when the matched current bond is cancelled or has a cancellation notice that blocks clearance.
  - `BOND_SHORTFALL` when the active current bond amount is below the applicable bulletin minimum.
- Insurance deficiencies:
  - `INSURANCE_VERIFY` when coverage is pending, carrier-mismatched, stale, expired, below the applicable minimum, or otherwise not verified active coverage.
  - Use replacement-style follow-up for expired/stale insurance when the template distinguishes it; use carrier-verification follow-up for pending or mismatch records.
- Compliance deficiencies:
  - `UNRESOLVED_PENALTY` for unresolved violations or penalty balances tied to the relevant legal entity/principal scope.
  - `FIELD_NOTE_HOLD` for open field notes or inspector recommendations that require clearance.
  - `CORRESPONDENCE_HOLD` for material correspondence with `new` or `needs_review` status; do not treat closed/indexed notices or similar-name public inquiries as material holds unless the task says so.
  - `ADVERSE_PRIOR_REGISTRATION` for adverse or needs-review background/prior-registration files.
  - `FINANCIAL_STATEMENT_MISSING` when the application/export shows the financial statement was not filed, or when a material open correspondence item requests it.
- Determinations:
  - `APPROVE` only when no deficiencies remain; pair with `NO_DEFICIENCY`.
  - `HOLD` for remediable staff actions, missing documents, verification, penalties, bond/insurance, or field clearance.
  - `DENY` only when the schema and facts clearly support a disqualifying final action; otherwise use `HOLD`.
- Sort reason codes in the enum order from the template. Compute determination and reason counts directly from the decision list.
- For manual follow-up outputs, include only applications needing staff action and sort by `application_id`. Map reasons consistently: prior-registration file review, bond replacement/increase, carrier verification or insurance replacement, inspector clearance, penalty ledger review, experience/financial documentation, and material correspondence review.
- For rule-change summaries, list only applications whose deficiency exists because a Q1 2026 bulletin changed a threshold or verification requirement, not every deficient application.

## Renewal Manual-Review Queues

- Use the release roster/export as the universe. Preserve facility names and license IDs exactly from the current roster.
- Pull renewal violations by roster city. Match pre-boundary violations to roster licensees by normalized same address plus exact or close facility/historical names. Use shared-address matches only as manual-review evidence and do not spread one shared-address record across multiple roster entities.
- Exclude matched violations after the release boundary from ranking and count them in the boundary-exclusion flag/count when the schema asks.
- Rank queues by matched pre-boundary violation count, then most recent matched violation date, unless the task gives a different priority rule.
- Use `match_confidence` as:
  - `exact` for exact facility/historical name at the same address.
  - `close` for obvious aliases or abbreviations such as Grille/Grill, Mkt/Market, Rm/Room, Haus/House, or successor hints.
  - `shared_address_manual` when the address matches but the name does not clearly match.
- Choose `next_step_label` from the dominant review concern: board sanction/suspension -> `board review`; ALERT-related records -> `manual ALERT check`; unpaid fines or fine collection -> `manual fine check`; otherwise `additional record check`.

## Restricted Alcohol Reviews

- Gather the target application, premises, incidents, settlements, current restrictions, standard obligations, and same-month comparison applications.
- Separate license-type/all-license standards from premises-specific restrictions:
  - Standard obligations come from `ALL` plus the target license type, identified by obligation/control code and evidence requirement.
  - Premises-specific controls come from restriction records and settlement/incidents that require location-specific monitoring.
- Same-premises risk:
  - Use `SAME_ADDRESS_OVERLAP` when the premises record states same address/service-area overlap.
  - Use prior settlement posture when settlement records exist; distinguish prior warning, restricted/denial, and current settlement.
  - Count pending or blank incident dispositions as unresolved. Count high severity incidents separately.
- Control coverage:
  - `ADEQUATE_LOCATION_SPECIFIC` when current proposed restrictions address the location-specific risk.
  - `STANDARD_ONLY` when only ordinary standards or standard-obligation restrictions exist.
  - `NO_CONTROLS` when no relevant controls are present.
- Verification gaps should be controlled enum values only. Use pending police-call dispositions, missing settlement terms/timing, missing age/late-night/security controls, and standard-control overlap as separate gaps when the template supports them.
- For review-month comparisons, count applications in the requested review month and count restricted-issuance reviews with current premises-specific controls. List matching application IDs in ascending order.

## Monitoring Plan Outputs

- Use source IDs from the records, sorted ascending inside each `source_ids` list.
- Standard obligations for a license type should reference `source_obligation_id` from the standard-obligation API, not restriction IDs.
- Keep standard-control overlap separate from premises-specific controls; for example, a premises `TRAINING_STANDARD` restriction can overlap with a BREWPUB training standard and should be tracked as an overlap rather than duplicated as a premises-specific control if the schema does not allow that control code.
- Premises-specific controls should map risks to allowed control/check codes:
  - Age verification -> `AGE_CHECK` / `DEVICE_AUDIT`.
  - Late-night incidents -> `LATE_NIGHT_DISORDER_MONITORING`, `NO_AFTER_MIDNIGHT_SERVICE`, `POLICE_CALL_LOG_REVIEW`, or `PATROL_OBSERVATION` as the facts support.
  - Security-plan lapse -> `SECURITY_PLAN_LAPSE_REVIEW` or `SECURITY_LOG`.
  - Settlement inspection terms -> `QUARTERLY_INSPECTION_CONDITION` / `SITE_INSPECTION`.
- Use records requests for documents that must be obtained: age-device audit, pending incident disposition packet, police call history, prior settlement packet, first-90-day inspection calendar, successor ownership/service-area statement, and license-type standard obligation evidence.
- Escalation triggers should correspond to the plan: missed first-90-day checks, missing/failed age audit, confirmed pending violations, new or confirmed high-severity incidents, and confirmed successor links.

## Common Pitfalls

- Do not count post-boundary or post-cutoff records as current deficiencies unless the task explicitly asks for current-state review or timing gaps.
- Do not count duplicate restrictions with the same control code twice unless the schema asks for record-level entries.
- Do not invent source IDs. Use IDs exactly as returned by CLRP.
- Do not mix application IDs, premises IDs, settlement IDs, restriction IDs, obligation IDs, and incident IDs in fields that require a specific source type unless the schema allows generic `source_ids`.
- Keep all lists in the ordering required by the template, especially ascending IDs, ascending code names, enum order, and rank order.
