---
name: clrp-licensing-review
description: Solve Cascadia Licensing Review Portal (CLRP) licensing-review tasks using only the public CLRP API/exports and the task's answer template. Use for contractor eligibility batches, restricted alcohol premises reviews and monitoring plans, and renewal manual-review queues that require strict JSON outputs, controlled enums, cutoff dates, deficiency counts, bulletin impacts, premises controls, or record-matching/ranking.
---

# CLRP Licensing Review

## Operating Rules

- Read the task prompt, `environment_access.md`, and the provided answer template first. Replace `<TASK_ENV_BASE_URL>` with `GDPEVO_ENV_BASE_URL`.
- Use only public CLRP API endpoints and public CSV exports under that base URL. Do not use local databases, manifests, setup scripts, hidden files, or evaluator material.
- Treat API responses as wrapped objects: records usually live under `.data`, with `count`, `limit`, `meta`, and `table` alongside them.
- Use the answer template as the contract. Return one JSON object only, with required keys, controlled enum strings, booleans, integer counts, and no markdown or narrative.
- Preserve required ordering exactly: IDs ascending when requested, enum-order sorting for reason codes, rank order for queues, and ascending source/control/request codes where specified.
- Do not invent source IDs. Use IDs from CLRP records (`CA-*`, `AA-*`, `PM-*`, `CB-*`, `BND-*`, `INS-*`, `CV-*`, `FN-*`, `COR-*`, `AO-*`, `AR-*`, `AS-*`, `AI-*`, `RV-*`).

## API Habits

- Contractor tasks commonly use:
  - `GET /api/contractors/applications?batch_id=...`
  - `GET /exports/contractor_batch_<batch_id>.csv`
  - `GET /api/contractors/bulletins?effective_on=<YYYY-MM-DD>`
  - `GET /api/contractors/bonds?name=<legal_or_principal_name>`
  - `GET /api/contractors/insurance?name=<legal_name_or_policy>`
  - `GET /api/contractors/violations?name=<legal_or_principal_name>`
  - `GET /api/contractors/complaints?name=<legal_name>`
  - `GET /api/contractors/field-notes?name=<legal_name>`
  - `GET /api/contractors/correspondence?batch_id=...`
- Alcohol tasks commonly use:
  - `GET /api/alcohol/applications?review_month=...` or broader application queries, then filter by `application_id`.
  - `GET /api/alcohol/premises?premises_id=...`
  - `GET /api/alcohol/incidents?premises_id=...`
  - `GET /api/alcohol/settlements?premises_id=...`
  - `GET /api/alcohol/restrictions?premises_id=...`
  - `GET /api/alcohol/standard-obligations?license_type=...`
- Renewal tasks commonly use:
  - `GET /api/renewals/licensees?release_batch=...`
  - `GET /exports/renewal_roster_<release_batch>.csv`
  - `GET /api/renewals/violations?city=<city>`
- Some endpoints return broad result sets even when queried with an ID. Always filter client-side to the target `application_id`, `premises_id`, `batch_id`, `release_batch`, city, or name.
- URL-encode names and addresses. Query both legal name and principal/current or historical names when records may be under either.
- Cross-check API data against CSV exports when a task asks for full-batch coverage or a fixed queue size.

## Contractor Eligibility

- Build one application decision for every application in the batch and no extras.
- Apply active bulletins effective on or before the review cutoff. Match `trade_scope` to the application trade, with `ALL` applying universally.
- Use bulletin thresholds for exam, bond, insurance, and experience minimums. If a file would pass prior rules but fails an active 2026/Q1 bulletin, include that application in the rule-change/bulletin-impact summary.
- Prefer current, matching records. Ignore obvious distractors such as old cancelled bonds for the same name when a current bond is active and sufficient, unless cancellation or replacement is the issue.
- Common reason-code triggers:
  - `BOND_SHORTFALL`: active bond amount below the applicable bulletin minimum.
  - `BOND_CANCELLED`: current bond status/cancellation notice shows cancellation before clearance.
  - `INSURANCE_VERIFY`: insurance is expired, stale, pending, mismatched, missing, or otherwise not verified against required coverage.
  - `UNRESOLVED_PENALTY`: contractor violation has unresolved status and a penalty due or unresolved enforcement posture.
  - `FIELD_NOTE_HOLD`: field note recommends hold/inspector clearance or an open hold remains.
  - `DISQUALIFYING_CONDUCT`: adverse background/disqualifying conduct supports denial.
  - `ADVERSE_PRIOR_REGISTRATION`: prior registration or successor/adverse prior file requires review.
  - `EXPERIENCE_VERIFY`: experience years fall below the applicable requirement or supporting documentation is required.
  - `CORRESPONDENCE_HOLD`: material correspondence is new/needs review and affects the application.
  - `FINANCIAL_STATEMENT_MISSING`: required financial statement flag is missing/false.
  - `EXAM_SCORE_SHORTFALL`: exam score below active passing threshold.
  - `NO_DEFICIENCY`: only when no other reason applies.
- Determination precedence: deny for disqualifying conduct; otherwise hold for any deficiency or staff follow-up; approve only with `NO_DEFICIENCY`.
- For manual follow-up outputs, map deficiencies to staff actions: adverse prior registration -> prior file review; cancelled bond -> bond replacement; bond shortfall -> bond increase/rider; insurance pending/mismatch -> carrier verification; expired insurance -> insurance replacement; field hold -> inspector clearance; unresolved penalty -> penalty ledger review; experience -> experience documentation; missing financial statement -> financial statement request; material correspondence -> correspondence review.
- Count determinations and reason codes from the emitted decisions, not from raw records. Count every reason-code occurrence once per affected application.

## Alcohol Restricted Reviews And Monitoring

- Center the target application and premises, then use same-month comparison records only when the output asks for comparison counts or context.
- Same-premises risk comes from matching `premises_id`, same address/service area, prior licensee, settlements, and incidents. Classify basis from the template enums rather than free text.
- Incident counts include incidents tied to the target premises. Pending or blank dispositions are unresolved. High severity count uses `severity == "high"`.
- Prior/current settlements inform settlement posture. Prior warning/restricted/denial/current settlement values should follow the template enum wording.
- Standard obligations come from `standard-obligations` rows for `license_type` plus `ALL`, and from standard-obligation restrictions when the template asks to show proposed/current obligations. Keep standard obligations separate from premises-specific controls.
- Premises-specific controls come from restriction rows with `category == "premises-specific"` plus incident/settlement evidence that implies controls. Typical mappings:
  - age/minor-sales control -> `AGE_CHECK`, evidence/check `device audit` or `DEVICE_AUDIT`.
  - after-midnight or late-night service concern -> `NO_AFTER_MIDNIGHT_SERVICE` or `LATE_NIGHT_DISORDER_MONITORING`.
  - patio limitation -> `PATIO_LIMIT`.
  - security logs/plans/lapses -> `SECURITY_LOG` or `SECURITY_PLAN_LAPSE_REVIEW`.
  - settlement inspection condition -> `QUARTERLY_INSPECTION_CONDITION`.
- Verification gaps should reflect missing or unresolved proof: pending incident dispositions, settlement terms/timing not found or post-review, controls expected from prior risk but absent from current restrictions, standard-control overlap, and successor separation.
- Monitoring plans should convert gaps and controls into records requests and escalation triggers. Use direct source IDs: incidents for incident packets and high-severity triggers, restrictions for device audits, settlements for inspection calendar/settlement timing, obligations for standard evidence, and premises for successor statements.
- Recommendation pattern: issue standard only for low risk with no gaps; request records/follow-up when critical verification is missing before issue; issue restricted with monitoring when controls can manage elevated successor/premises risk; deny only for severe unmanageable risk per template.

## Renewal Manual-Review Queues

- Start with the current renewal roster for the release batch. Include only current licensees requested by the template, often active or pending-renewal rows in that batch.
- Fetch violation records by each roster city. Exclude violations after the release boundary date and count exclusions in `excluded_post_boundary_count`.
- Match violations conservatively:
  - `exact`: normalized facility/historical name matches the roster facility name.
  - `close`: abbreviation, successor hint, or minor spelling variation matches the same business identity, especially when the numeric suffix and address agree.
  - `shared_address_manual`: address matches but name identity does not; use only when the task asks for shared-address context.
- Do not spread shared-address records to every licensee at an address. Keep `shared_address_records_not_spread` true when the method avoids that over-counting.
- Avoid fuzzy over-matches where only a brand word matches but the numeric suffix or address differs.
- Rank the queue by the task’s risk posture using matched pre-boundary violations: higher violation counts, high severity, suspension/minor-sale/disorder themes, unresolved/pending dispositions, large unpaid fines, ALERT-related records, and recency all increase priority. Break ties consistently and emit exactly the requested queue size.
- Set `most_recent_date_used` to the newest matched pre-boundary violation date included for that licensee.
- Next-step labels usually follow the dominant issue: severe/high or board-facing patterns -> `board review`; unpaid fine or unresolved fine pattern -> `manual fine check`; ALERT-related pattern -> `manual ALERT check`; ambiguous/shared-address or low-confidence cases -> `additional record check`.

## Final Checks

- Validate JSON syntax before returning.
- Confirm coverage: every required batch application, target ID, or exact queue length.
- Recompute counts from the final output.
- Ensure enum casing and date formats match the template exactly.
- Remove helper evidence text unless the schema explicitly includes evidence fields.
