---
name: clrp-licensing-review
description: Prepare Cascadia Licensing Review Portal (CLRP) licensing review JSON for contractor eligibility, alcohol restricted-license monitoring, and renewal manual-review queue tasks. Use when prompts reference CLRP public APIs/exports, batch or review-month licensing decisions, bulletin impacts, premises restrictions, incidents, settlements, or renewal violation queues with strict answer templates.
---

# CLRP Licensing Review

## Operating Rules

- Use only the CLRP base URL and public API/export surfaces named or implied by the prompt. Do not inspect local generated data, hidden files, manifests, setup scripts, or non-public artifacts.
- Read the prompt and answer template first. Treat enum spelling, required keys, list ordering, integer counts, booleans, and `additional_properties_allowed` as binding.
- Return JSON only. Do not add markdown, explanations, evidence prose, or extra fields.
- Build from target records outward: fetch the target application/batch/roster first, then related public records by the IDs, names, premises, cities, dates, and batch/review-month values in the prompt.
- Apply cutoff, release-boundary, or review-month dates before ranking or deciding. If a template asks for post-boundary exclusions, count excluded matched records separately rather than using them in decisions.

## Contractor Reviews

- Fetch applications by `batch_id`; use the batch export as a cross-check, not as a substitute for related records.
- Fetch active bulletins with the prompt's effective date when given. If the summary asks for active/applicable bulletin IDs and the endpoint is already date-filtered, preserve the returned bulletin set unless the template explicitly asks for trade-filtered IDs.
- Match bonds, insurance, violations, complaints, field notes, and correspondence primarily by exact `legal_name` and `application_id`. Use principal, DBA, or similar names only when the prompt or a record explicitly establishes a successor/prior-registration relationship. Do not spread distractor records from same principals or near names.
- Prefer actual bond and insurance records over declared application fields. Bond deficiencies come from cancellation, reduced/active amount below the current threshold, or missing replacement evidence. Insurance deficiencies come from expired/stale, pending, carrier mismatch, unverified, or below-threshold coverage.
- Use `NO_DEFICIENCY` only when no other reason code applies. Sort reason codes in the template's enum order.
- Treat unresolved penalties, open inspector holds, missing financial statements, adverse/prior registration indicators, and material correspondence requiring review as separate reasons when the template provides those enums.
- For correspondence, distinguish status and timing. `needs_review` and material `new` items before the relevant boundary can drive a correspondence hold; `indexed` or `closed` items usually serve as evidence for another deficiency.
- For bulletin-change summaries, list applications whose deficiency depends on a 2026 rule change or verification requirement, not every deficient application.
- Map manual follow-up reasons consistently:
  - adverse/prior registration -> prior-registration file review
  - cancelled bond -> bond replacement
  - bond shortfall -> bond increase/rider
  - insurance pending/mismatch -> carrier verification
  - insurance expired/stale -> insurance replacement
  - field hold -> inspector clearance
  - unresolved penalty -> penalty ledger review
  - experience shortfall -> experience documentation
  - missing financial statement -> financial statement request
  - correspondence hold -> material correspondence review

## Alcohol Restricted-License Reviews

- Common endpoints are organized by applications, premises, incidents, settlements, restrictions, and standard obligations. Join records by `premises_id`; do not assume restrictions are scoped by `application_id` unless the response confirms it.
- For review-month comparison fields, count all applications for `review_month_application_count`, but lists/counts about restricted-review controls should use the restricted/follow-up review population when the field wording says restricted reviews.
- Use the premises record for same-premises basis. When it says same address and overlapping service area, prefer `SAME_ADDRESS_OVERLAP`; reserve prior-settlement enums for records that make settlement-at-address the stated basis.
- Count pending or blank incident dispositions as unresolved. Derive prior incident level from the most severe relevant incident.
- Standard obligations come from `ALL` plus the target license type. Keep evidence strings exactly as returned. Include proposed/settlement standard obligations only when the template has a source enum for them.
- Separate standard obligations from premises-specific controls. Existing restrictions are current controls; missing but required controls are follow-up-required controls when the template supports that status.
- For monitoring plans, use source IDs from incidents, settlements, restrictions, obligations, and premises records. Sort source IDs ascending. Post-review settlements usually create monitoring/timing gaps and records requests; they are not automatic denials.
- Use first-90-day checks for controls tied to age verification, late-night disorder, police-call history, quarterly inspections, or security-plan lapse monitoring.

## Renewal Manual-Review Queues

- Start with the release-batch roster. Query renewal violations by each roster city, then join back to current roster licensees.
- Match exact facility names first. Use normalized close matches for documented aliases such as `Mkt`/`Market`, `Rm`/`Room`, `Haus`/`House`, or `Grille`/`Grill`, especially when `successor_hint` supports the alias.
- Do not spread violations merely because they share an address. Use `shared_address_manual` only when the template expects manual shared-address matching and the evidence supports it.
- Exclude matched violations after the release boundary from ranking, and count them in the method flags when requested.
- Do not assume a lifetime city-wide count or pure recency ranking. Determine from the prompt/template whether ranking is driven by release-window count, most recent pre-boundary date, ALERT patterns, unpaid fines, board sanctions, pending dispositions, or a combination.
- Choose `next_step_label` from the dominant review need: fine status, ALERT pattern, board/suspension review, or additional record check.

## Output Conventions

- Preserve all required top-level keys and omit unapproved keys.
- Sort application decisions, manual follow-ups, IDs, source IDs, controls, obligations, requests, triggers, and reason-code lists exactly as the template says.
- Recompute all summary counts from the emitted decision lists.
- Use integers for counts and JSON booleans for boolean fields.
- Keep enum casing exact. A semantically correct value with different casing is wrong.

## Common Pitfalls

- Treating declared bond/insurance values as verified records.
- Including post-boundary correspondence or violations in decisions instead of exclusions.
- Trade-filtering a date-filtered bulletin list when the summary expects the endpoint-returned active bulletin set.
- Spreading contractor records across same principals or similar names without a direct successor/prior-registration basis.
- Counting standard issuance applications in restricted-review control ID lists.
- Turning every incident into a premises-specific control; only map incidents to controls when the template has a matching control code and the record supports monitoring.
- Adding narrative fields or evidence text to scored JSON objects.
