---
name: clrp-licensing-reviews
description: Conduct Cascadia Licensing Review Portal (CLRP) licensing reviews and produce strict JSON outputs for contractor eligibility batches, restricted alcohol license reviews or monitoring plans, and renewal manual-review queues. Use when tasks reference CLRP public APIs/exports, cutoff or review dates, active bulletins, premises-specific controls, renewal release boundaries, controlled enums, or answer_template.json schemas.
---

# CLRP Licensing Reviews

## Operating Pattern

1. Read the prompt and `answer_template.json` first. Treat the template as the output contract: exact top-level keys, enum spelling, ordering rules, required constants, booleans, integer counts, and `additional_properties_allowed`.
2. Replace `<TASK_ENV_BASE_URL>` with the task-provided base URL. Use only public CLRP API endpoints and public exports named or implied by the task. Do not inspect local implementation files, generated databases, manifests, or hidden files.
3. Fetch authoritative records from APIs before deciding. CLRP JSON usually has `{count, data, limit, meta, table}`; always inspect `data` and verify `count`. Some endpoints ignore unsupported filters or return broad sets, so client-filter by IDs, batch, review month, premises, city, and dates.
4. Normalize blank strings as missing, `0/1` as booleans, cents as cents, and dates as ISO strings. Keep a working evidence table keyed by stable IDs and source IDs so counts and `source_ids` reconcile.
5. Apply cutoff/review-boundary dates consistently. Use records effective on or before the cutoff unless the task says otherwise. Exclude post-boundary renewal violations from ranking and count excluded matched records when the schema asks.
6. Return one JSON object only. Before finalizing, validate with `jq`, verify all required keys exist, no extra keys appear where forbidden, list ordering matches the template, and all summary counts equal the detailed rows.

## API Habits

Contractor reviews commonly use:

- `GET /api/contractors/applications?batch_id=<batch_id>`
- `GET /exports/contractor_batch_<batch_id>.csv`
- `GET /api/contractors/bulletins?effective_on=<YYYY-MM-DD>`
- `GET /api/contractors/bonds?name=<legal_or_principal_name>`
- `GET /api/contractors/insurance?name=<legal_name_or_policy>`
- `GET /api/contractors/violations?name=<legal_or_principal_name>`
- `GET /api/contractors/complaints?name=<legal_name>`
- `GET /api/contractors/field-notes?name=<legal_name>`
- `GET /api/contractors/correspondence?batch_id=<batch_id>`

Query related contractor endpoints by legal name and principal name when relevant, URL-encode values, and de-duplicate by record ID. Treat bond and insurance endpoints as authoritative over declared application values.

Alcohol restricted-license reviews commonly use:

- `GET /api/alcohol/applications?review_month=<YYYY-MM>`
- `GET /api/alcohol/premises?premises_id=<premises_id>`
- `GET /api/alcohol/incidents?premises_id=<premises_id>`
- `GET /api/alcohol/settlements?premises_id=<premises_id>`
- `GET /api/alcohol/restrictions?premises_id=<premises_id>`
- `GET /api/alcohol/standard-obligations?license_type=<license_type>`

Filter alcohol applications to the target application/premises and use same-month applications for comparison counts. Keep `standard-obligation` restrictions separate from `premises-specific` restrictions.

Renewal queue reviews commonly use:

- `GET /api/renewals/licensees?release_batch=<batch_id>`
- `GET /exports/renewal_roster_<batch_id>.csv`
- `GET /api/renewals/violations?city=<city>`

Pull renewal violations for every city represented in the roster. If an address-search endpoint is provided by the task, use it only to resolve ambiguous address matches; otherwise rely on roster address, facility/legal names, successor hints, and city-scoped violations.

## Contractor Business Rules

- Apply active bulletins with `effective_date <= review_cutoff_date` and `trade_scope` equal to the application trade or `ALL`. Use `threshold_value` for exam, bond, insurance, and experience requirements.
- `NO_DEFICIENCY` is valid only when no other reason code applies. Otherwise choose the highest determination severity: `DENY` over `HOLD` over `APPROVE`.
- Use `DENY` for disqualifying background/conduct, adverse prior registrations that bar eligibility, and non-curable exam failures when the template has no hold path. Use `HOLD` for curable or staff-verification issues.
- Map common contractor deficiencies as follows:
  - exam score below active minimum: `EXAM_SCORE_SHORTFALL`
  - active bond missing, cancelled by cutoff, or replacement required: `BOND_CANCELLED`
  - active bond amount below active trade minimum: `BOND_SHORTFALL`
  - insurance missing, expired, inactive, unverified, carrier/policy mismatch, or below active coverage minimum: `INSURANCE_VERIFY`
  - unresolved violations, unpaid penalties, AG referrals, or penalty ledger issues: `UNRESOLVED_PENALTY`
  - open field notes or inspector clearance requests: `FIELD_NOTE_HOLD`
  - material correspondence with `needs_review` or unresolved status: `CORRESPONDENCE_HOLD`
  - adverse prior registration requiring staff file review: `ADVERSE_PRIOR_REGISTRATION`
  - experience below active minimum or documentation gap: `EXPERIENCE_VERIFY`
  - missing required financial statement: `FINANCIAL_STATEMENT_MISSING`
- Attach `primary_bulletin_ids` only for deficiencies driven by active bulletins; sort bulletin IDs ascending. Rule-change summaries should count applications whose result changed because a current bulletin introduced or increased a requirement relative to the prior rule.
- When a template has `manual_followup`, include every non-clear application needing staff action and map follow-up reason codes directly from the underlying deficiency. Sort application rows and manual follow-up rows by `application_id`; sort reason codes in the enum order from the template.
- If a template has a single `next_action`, use the most specific action for one deficiency and `COMBINED_HOLD_REVIEW` when multiple hold reasons require staff coordination.

## Alcohol Review Rules

- Count all incident records for the target premises. Treat `disposition` of `pending` or blank as unresolved. Count `severity == "high"` separately.
- Derive same-premises risk from premises records and address overlap. Use prior settlements and overlapping service areas as successor-risk evidence even when the applicant is new.
- Map settlement posture by `prior_or_current` and `original_posture`: warning terms imply prior warning controls; restricted issue or denial terms imply restricted/denial posture; current settlements or settlements dated after the review period usually create verification gaps.
- Separate controls:
  - Standard obligations come from `standard-obligations` for `ALL` plus the license type and from standard-obligation restrictions.
  - Location-specific controls come only from `premises-specific` restrictions or settlement terms tied to the premises.
- A restricted issuance is appropriate when premises-specific controls cover the premises risks and remaining gaps are monitorable. Request follow-up or records before issue when settlement terms, pending dispositions, ownership/service-area separation, or control evidence is missing. Deny only for severe unresolved risk or disqualifying settlement posture.
- Common alcohol gap mappings:
  - pending or blank incident dispositions: pending-disposition gap and records request
  - minor-service or age-control risk without current `AGE_CHECK`: age-verification gap/request
  - late-night disorder/noise risk without service/security controls: late-night/security gap/request
  - security plan lapse without verified control: security-plan lapse gap/request
  - prior-licensee overlap not separated from the new applicant: successor-control separation gap/request
  - settlement after the review month/cutoff: post-review settlement timing gap
- Map premises-specific controls to monitoring checks by evidence: `AGE_CHECK` -> device audit, `NO_AFTER_MIDNIGHT_SERVICE` -> service log review, `PATIO_LIMIT` -> patio closure log review, `SECURITY_LOG` or security-lapse controls -> security log review, late-night disorder controls -> patrol or police-call review, quarterly inspection conditions -> site inspection.
- For comparison summaries, count all applications in the review month, then count applications with at least one current location-specific control. Do not count standard obligations as location-specific controls.

## Renewal Queue Rules

- Build the candidate set from the current release roster. Preserve `license_id`, `facility_name`, address, city, status, and `successor_hint`.
- Fetch violations by each roster city and match to roster licensees by exact facility/legal/historical name, close successor-hint name, or same address. Use `match_confidence` values conservatively:
  - `exact` for exact name or unique exact address/name alignment
  - `close` for successor-hint or clear near-name matches
  - `shared_address_manual` for address-only matches that need human confirmation
- Do not spread a shared-address violation to every licensee at that address. Assign only when the record can be tied to one licensee, or mark a single manual shared-address match if the template supports it. Set `shared_address_records_not_spread` to true when this safeguard is applied.
- Exclude matched violations after the release boundary from ranking. Count them in `excluded_post_boundary_count` and set `post_boundary_exclusion_applied` when any were excluded.
- Rank exactly the requested queue size by `violation_count_used` descending, then `most_recent_date_used` descending, then higher severity/fine/ALERT concern, then stable `license_id` as a tie-breaker unless the prompt specifies another ranking rule.
- Choose `next_step_label` from evidence: unpaid fine or positive `fine_cents` -> `manual fine check`; `alert_related` or `ALERT` code/theme -> `manual ALERT check`; suspension, board sanction, high severity, or serious unresolved posture -> `board review`; ambiguous or lower-risk matched records -> `additional record check`.

## Output Conventions And Pitfalls

- Use only enum values from the active template; enum case and spaces are significant.
- Respect template ordering: application IDs ascending, reason codes in enum order, source IDs ascending, rank ascending, and code lists by requested code order.
- Include empty lists only when the template permits them; otherwise use the required no-gap enum such as `NO_VERIFICATION_GAPS`.
- Keep summary counts auditable: reviewed applications equal decision rows, determination counts equal decisions, reason-code counts count applications carrying each code, and queue size equals requested length.
- Do not rely on declared application bond or insurance values when authoritative records disagree.
- Do not treat resolved violations, resolved field notes, standard obligations, or post-boundary renewal violations as active deficiencies unless the task explicitly says to.
- Do not include narrative, markdown fences, evidence excerpts, or unrequested fields in the final JSON.
