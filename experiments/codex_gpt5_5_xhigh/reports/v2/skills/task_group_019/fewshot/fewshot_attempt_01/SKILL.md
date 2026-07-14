---
name: clrp-licensing-review
description: Produce schema-valid CLRP licensing review outputs for contractor eligibility, alcohol restricted-license reviews, renewal manual-review queues, and monitoring plans using public API/export evidence.
---

Use this skill when a task asks for a Cascadia Licensing Review Portal (CLRP) licensing decision, review queue, or monitoring plan.

## Operating Procedure

1. Read the prompt, `environment_access.md`, and the provided answer template before querying data. Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`.
2. Use only the CLRP public API and public exports exposed through that base URL. Do not rely on local databases, generated files, manifests, or setup artifacts.
3. Start from the authoritative roster or application endpoint/export for the requested batch, release, target application, review month, or premises. Use that source to establish exact coverage and stable IDs.
4. Pull related evidence by the identifiers and matching keys the task implies: application/license ID, premises ID, legal or facility name, principal name, address, city, batch ID, review month, and effective date.
5. Treat dates as business boundaries. Apply review cutoffs, release boundaries, review months, and bulletin effective dates exactly. Exclude post-boundary records when the template asks for pre-boundary ranking or counts, and report the exclusion count if requested.
6. Build a working table of every relevant record, decision reason, source ID, and output enum before writing JSON. Recompute all summary counts from the final output arrays.

## API and Export Habits

- Prefer JSON APIs for detail records and CSV exports for complete rosters. Parse CSV structurally rather than with ad hoc text splitting.
- For contractor reviews, gather applications, bonds, insurance, violations, complaints, field notes, correspondence, and effective bulletins. Query by legal/principal names where the endpoint is name-based, then verify matches against application IDs, principals, or addresses.
- For alcohol restricted-license work, gather the target application, premises/address history, incidents, settlements, restrictions, standard obligations, and same-month comparison applications when the prompt asks for comparison context.
- For renewal queues, gather the current release roster, renewal violations, address search results, and city-level violation feeds. Match current licensees to violations by exact name first, close name second, and shared address only when the task/template allows a manual shared-address confidence.
- Do not spread a shared-address violation record across unrelated licensees. If a shared-address match is used, label it with the template's shared-address confidence enum and keep the source-to-license rationale narrow.
- Cross-check exports against APIs when counts or coverage matter. The final output should include every required roster/application record exactly once unless the template specifies a fixed queue size.

## Business Rules

### Contractor Eligibility

- Return one decision per batch application, sorted by `application_id`.
- `APPROVE` is only for applications with no deficiencies; use `NO_DEFICIENCY` as the sole reason code.
- Use `HOLD` for remediable or verification issues: bond shortfall, cancelled bond, insurance verification/replacement issue, unresolved penalty, field/inspector hold, experience verification, financial statement missing, material correspondence hold, or adverse prior registration requiring staff review.
- Use `DENY` for disqualifying conduct or other non-remediable adverse findings supported by the records.
- Sort `reason_codes` and follow-up reason lists in the enum order defined by the template, not by discovery order.
- Map manual follow-up to the operational remedy: bond replacement or increase, carrier/insurance verification, inspector clearance, penalty ledger review, prior registration file review, experience documents, financial statement, or material correspondence review.
- Attribute `primary_bulletin_ids` only to bulletins that actually drive the deficiency or changed outcome. Bulletin impact summaries count only applications whose outcome or deficiency exists because of a newly applicable bulletin.
- Counts must reconcile with the decision list: total reviewed, determination counts, reason-code counts, bulletin-changed IDs, and manual-followup count.

### Alcohol Restricted Licenses and Monitoring

- Separate ordinary license-type or all-license standard obligations from premises-specific restrictions. Do not count standard obligations as location-specific controls.
- Assess same-premises successor risk from address overlap, prior premises settlements, incidents, restrictions, and address history. A successor risk finding should be tied to the premises/address record, not merely a similar business name.
- Count incidents using the prompt's review scope. Pending or blank dispositions are unresolved; high-severity incidents drive elevated risk and escalation.
- Prior settlements or warnings with controls should raise the settlement posture and can require restricted issuance, records before final issue, first-90-day monitoring, or denial depending on severity and unresolved gaps.
- If current restrictions lack controls that prior incidents or settlements require, list verification gaps and records requests instead of treating the controls as already satisfied.
- Standard obligations should carry the license-type/all-license/proposed source and the evidence the inspector can verify, such as logs, rosters, sales audits, menus, records binders, floor plans, sample logs, or permits.
- Premises-specific controls should identify control code, source IDs, check code, and whether the check belongs in the first 90 days. Typical controls include age checks, late-night service limits, patio limits, security logs, police-call review, and site inspections.
- Escalation triggers should be concrete and source-backed: failed/missing age audit, missed first-90-day check, new or confirmed high-severity incident, pending incident confirmed as a violation, or confirmed successor link to a prior licensee.

### Renewal Manual-Review Queues

- Restrict candidates to the current release roster and the requested release batch.
- Include exactly the queue size required by the template. Ranks are business-significant and must be sequential.
- Use only matched violations dated on or before the release boundary for ranking. Count and flag excluded post-boundary matches when requested.
- `match_confidence` should reflect the match method: exact current roster identity, close/fuzzy name match, or shared-address manual match.
- Ranking should favor stronger manual-review need: more matched violations, severe or board-review indicators, fine or ALERT follow-up needs, and recency within the allowed boundary. Use stable IDs as final tie-breakers.
- `next_step_label` must come from the template. Use board review for the highest-risk or repeated serious histories, manual fine check for fine-led issues, manual ALERT check for ALERT-led issues, and additional record check for weaker unresolved matches.

## Output Conventions

- Return exactly one JSON object and no Markdown or narrative.
- Match the template's top-level keys, required nested keys, enum values, date formats, booleans, and integer counts exactly. Do not add extra properties when the template disallows them.
- Preserve required literal IDs and dates from the prompt/template.
- Follow every ordering instruction: application IDs ascending, source IDs ascending, enum-order reason lists, rank ascending, or the template's stated order.
- Use empty lists when allowed and no items apply; use `NO_DEFICIENCY` or `NO_VERIFICATION_GAPS` only when the template's enum expects that explicit clean value.
- Before finalizing, validate that all counts are integers and match the arrays they summarize.

## Common Pitfalls

- Omitting clean applications from batch outputs.
- Including post-boundary violations in renewal rankings while also claiming boundary exclusion.
- Applying one shared-address record to multiple licensees without support.
- Mixing premises-specific controls with standard license obligations.
- Reporting a bulletin as applicable when it did not change a decision.
- Sorting reason codes alphabetically instead of in template enum order.
- Producing explanatory prose, Markdown fences, lowercase enums, or extra fields outside the output contract.
