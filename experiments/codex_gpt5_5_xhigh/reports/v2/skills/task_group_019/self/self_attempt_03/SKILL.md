---
name: clrp-licensing-review
description: Conduct Cascadia Licensing Review Portal (CLRP) licensing, renewal, contractor eligibility, restricted-license, and monitoring reviews using public CLRP APIs/exports, then return strict schema-conforming JSON. Use when a task gives a CLRP base URL, target batch/application/premises/review date, controlled enums, and an answer template requiring eligibility decisions, manual-review queues, risk assessments, monitoring plans, deficiency counts, or rule-change summaries.
---

# CLRP Licensing Review

## Workflow

1. Read the task prompt, base URL instructions, and answer template first. Treat fixed IDs, dates, enum values, ordering rules, required counts, and "JSON only" requirements as binding.
2. Replace `<TASK_ENV_BASE_URL>` with the provided CLRP base URL. Use public CLRP API endpoints and public exports named in the task; do not derive decisions from assumptions when a public record can be queried.
3. Build a complete evidence set for the requested scope:
   - Batch contractor reviews: applications/roster export, active bulletins, bonds, insurance, violations, complaints, field notes, correspondence, and prior registration or related records by legal/principal name.
   - Renewal queues: current renewal roster/export, licensee records, violation records, address search results, and release boundary filtering.
   - Alcohol restricted-license reviews and monitoring plans: target application, premises, incidents, settlements, restrictions, standard obligations, address history, and same-premises predecessor/successor context.
4. Normalize names, addresses, IDs, and dates for matching, but emit the stable portal IDs and exact template enum strings. URL-encode query parameters.
5. Apply the review cutoff, release boundary, or review month exactly as stated. Exclude records after the boundary from decision/ranking inputs unless the template asks to report them separately.
6. Reconcile API JSON with public CSV exports when both exist. Use exports to detect missing applications/licensees and APIs for detailed evidence.
7. Before returning, validate coverage, ordering, enum spelling, counts, required keys, and absence of extra prose.

## Business Rules

- Include every in-scope application/licensee exactly once when the template requires full batch or queue coverage. Do not include records outside the target batch, release, review month, application, or premises.
- For contractor eligibility, classify each application as `APPROVE`, `HOLD`, or `DENY` based on unresolved deficiencies. Use `NO_DEFICIENCY` only when no other reason code applies.
- Treat bond shortfalls, cancelled bonds, insurance mismatches or verification gaps, unresolved penalties, adverse prior registrations, field-note holds, correspondence holds, missing financial statements, exam shortfalls, and experience gaps as distinct deficiencies when supported by records or active bulletins.
- Apply bulletins effective on the review date to minimums such as bond, insurance, exam, and experience requirements. Track applications whose outcome or deficiency status changes because of those bulletins when the schema asks for bulletin impact or rule-change summaries.
- Prefer `HOLD` for remediable or staff-verification issues and `DENY` for disqualifying conduct or non-remediable adverse findings, unless the task template or records define a different decision mapping.
- For renewal manual-review queues, rank only current release-batch licensees and use matched pre-boundary violations. Count excluded post-boundary matched violations when requested. Do not spread a shared-address violation to all co-located licensees without name, license, or other record evidence.
- For restricted alcohol reviews, separate standard license obligations from premises-specific restrictions. Standard obligations come from license type or all-license rules; premises-specific controls come from settlements, restrictions, same-address incident history, or predecessor/successor risk.
- Treat blank or pending incident dispositions as unresolved. Same-premises risk depends on address/history overlap, prior settlements, incident severity, and whether proposed controls cover the location-specific risk.
- First-90-day monitoring should focus on controls that require early verification, such as age checks, late-night service limits, security logs, patio limits, police-call reviews, or site inspections.

## API Habits

- Start with the broad roster/export endpoint, then query detail endpoints by batch ID, application ID, premises ID, legal name, principal name, facility name, city, policy, or address as appropriate.
- Query alternate names and principals when contractor records may be stored under either the business or principal name.
- Preserve raw source IDs for `source_ids`, `primary_bulletin_ids`, obligation IDs, control IDs, and similar evidence references. Sort IDs where the template says ascending.
- Use date comparisons on parsed dates, not string fragments. Keep output dates in the exact requested format (`YYYY-MM-DD` or `YYYY-MM`).
- If an endpoint returns an empty result, check whether the task provides another public surface for the same evidence before concluding there is no record.
- Use deterministic tooling (`curl`, `jq`, CSV parsing, small scripts) for large exports, joins, ranking, and counts; avoid manual arithmetic for scored count fields.

## Output Conventions

- Return exactly one JSON object and no markdown, comments, citations, or narrative outside the object.
- Include all required top-level keys and required nested keys. Omit extra keys when the template disallows additional properties.
- Use controlled enum values exactly as written, including case and spaces.
- Follow template ordering rules: ranks ascending, applications ascending by application ID, reason codes in template enum order, IDs/codes ascending where specified, and fixed queue lengths when required.
- Emit integer counts, booleans as JSON booleans, empty lists for no items, and zeroes for no counts. Keep count totals internally consistent with the emitted decision lists.
- Do not include free-form evidence text unless the schema explicitly has a field for it. Prefer concise IDs, codes, and requested labels.
- For manual follow-up fields, include only applications requiring staff action and sort by application ID. Reason lists should use the follow-up enum order from the template.

## Pitfalls

- Applying records after the stated cutoff or release boundary to decisions or ranking.
- Missing applications that appear only in the export, or including comparison-context records in the target output.
- Confusing standard alcohol obligations with location-specific controls.
- Treating shared-address, close-name, or predecessor records as exact matches without documenting the lower confidence field the template provides.
- Counting deficiencies by unique code only when the schema expects per-application occurrences.
- Emitting `NO_DEFICIENCY` alongside another reason code.
- Returning fewer or more queue rows than the fixed length, or leaving ranks non-contiguous.
- Adding explanatory prose, unsupported enum values, unsorted lists, or extra JSON fields.
