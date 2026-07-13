---
name: clrp-licensing-review
description: Prepare CLRP contractor, alcohol-license, and renewal-review JSON outputs from public CLRP APIs and exports while preserving schema enums, ordering, counts, and review cutoffs.
---

Use this skill when a task asks for a Cascadia Licensing Review Portal (CLRP) licensing review, eligibility screen, restricted alcohol review, monitoring plan, or renewal manual-review queue.

## Operating Habits

- Read the task prompt and `input/payloads/answer_template.json` first. Treat the template as the contract for required keys, enum spelling, list order, counts, and whether extra fields are allowed.
- Use only the CLRP base URL and public API/export surfaces named or implied by the task. Do not rely on local generated data, manifests, hidden files, setup scripts, or assumptions from prior tasks.
- Prefer API JSON for relational records and exports for roster/batch coverage checks. If an endpoint ignores a filter and returns all rows, filter client-side by the requested batch, review month, application, premises, city, or release batch.
- Keep a scratch table of each source record used: source ID, date, status/disposition, legal/facility name, address, and why it affects an output field.

## Contractor Reviews

- Common public surfaces: contractor applications by `batch_id`, batch CSV export, bulletins by effective date, correspondence by batch, and bonds, insurance, violations, complaints, and field notes by legal name, principal name, or policy number.
- Match the current applicant legal name first. Use principal/successor/related-entity records only when the task asks for related contractor records; avoid letting unrelated same-principal distractors override the current file.
- For cutoff reviews, use event dates that drive the legal effect: effective date, cancellation date, violation date, received date, inspection date. Do not discard an otherwise relevant cancellation or violation only because `last_update` is later, but do not use future received/event records when the task sets a strict cutoff.
- Bond rules: cancelled current bond means `BOND_CANCELLED`; active bond below the current trade bulletin threshold means `BOND_SHORTFALL`; use replacement vs increase follow-up accordingly.
- Insurance rules: pending verification or carrier mismatch means carrier verification; expired, stale, or inactive coverage means insurance replacement. Both usually map to `INSURANCE_VERIFY` in decision reason codes.
- Other holds: unresolved positive penalties map to `UNRESOLVED_PENALTY`; open inspector holds or hold-for-clearance field notes map to `FIELD_NOTE_HOLD`; `needs_review` or `new` material correspondence maps to `CORRESPONDENCE_HOLD`; missing filed flags map to `FINANCIAL_STATEMENT_MISSING`; adverse prior-registration indicators map to `ADVERSE_PRIOR_REGISTRATION`.
- Deny only when the records show explicit disqualifying conduct or an adverse prior-registration posture severe enough for denial; otherwise prefer `HOLD` with manual follow-up.
- For bulletin summaries, include the active bulletins requested by the task and count applications whose current deficiency is driven by those effective bulletin rules. Keep this separate from ordinary non-bulletin deficiencies.

## Alcohol Restricted Reviews

- Common public surfaces: alcohol applications by review month, premises by premises ID, incidents by premises ID, settlements by premises ID, restrictions by premises ID, and standard obligations by license type.
- Same-premises overlap, prior settlements, pending or blank incident dispositions, high-severity incidents, and missing location-specific controls drive risk. Count unresolved incidents from pending or blank dispositions.
- Standard obligations should include `ALL` obligations plus the target license type obligations. Deduplicate by control/obligation code, and keep evidence text exactly as the API provides it.
- Premises-specific restrictions come from current restrictions, settlement terms, and incident patterns. Missing controls for age checks, late-night service, security logs, patio limits, quarterly inspections, or police-call monitoring should become follow-up controls or monitoring checks using the template’s enum codes.
- Same-month comparison counts for restricted reviews should count restricted-issuance applications with location-specific controls; do not include standard-issuance comparison rows in a restricted-review control count.

## Renewal Queues

- Common public surfaces: renewal licensees by release batch, renewal roster export, and renewal violations by city. Use address search or address matching only when it is a public CLRP surface available for the task.
- Match renewal violations by exact facility name/address first, then successor hints or normalized close names, then address-only matches as `shared_address_manual`.
- Apply the release boundary to `violation_date`; count post-boundary matched records separately when the schema asks for exclusions.
- Do not spread shared-address or suite-level records across all licensees at the address. Treat shared-address records as manual matches only when the task calls for them.
- The rank is business-significant. Decide whether the task wants all matched history, unresolved/manual-action records, active statuses only, or all current roster rows before ranking; then rank consistently by the requested count/recency method.

## Output Conventions

- Return JSON only. Do not include markdown, comments, or narrative outside the object.
- Preserve controlled enum spelling and case. Sort reason-code lists, follow-up-code lists, gap/control/request/trigger lists, source IDs, bulletin IDs, and application IDs exactly as the template instructs.
- Use integers for counts and booleans for boolean fields. Recompute all summary counts from the final decision lists.
- Use `NO_DEFICIENCY` only for approved applications. Holds and denials should have concrete reason codes and manual follow-up entries when the schema asks for them.
- For monitoring plans, keep source IDs traceable: obligation IDs for standards, restriction IDs for controls, incident IDs for incident-derived controls, settlement IDs for settlement terms, and premises IDs for same-premises successor facts when no more specific record ID exists.

## Pitfalls

- Do not treat every API row returned by a broad endpoint as relevant; filter by the target batch, month, premises, city, status, and date boundary.
- Do not confuse proposed/current location-specific controls with standard license obligations. Standard obligations can overlap with settlement restrictions, but the output often requires them in separate sections.
- Do not count standard-issuance applications in restricted-review control counts.
- Do not use all historical violations for a renewal queue unless the task says to; many renewal tasks distinguish matched records, post-boundary exclusions, unresolved/manual-action records, and shared-address records.
- Do not let free-text summaries override structured fields such as status, disposition, finding type, verification status, or filed flags unless the task explicitly asks for narrative review.
