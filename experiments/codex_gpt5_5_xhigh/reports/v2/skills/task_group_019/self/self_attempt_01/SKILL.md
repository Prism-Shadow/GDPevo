---
name: clrp-public-record-review
description: Use for Cascadia Licensing Review Portal (CLRP) public-record licensing reviews that require strict JSON outputs from task prompts, answer templates, public APIs, and public exports.
---

# CLRP Public-Record Review

## Operating Procedure

1. Read the task prompt, environment access instructions, and answer template first. Treat the template as the contract for required keys, enum values, ordering, required constants, date formats, and whether additional fields are allowed.
2. Replace `<TASK_ENV_BASE_URL>` only with the supplied CLRP base URL. Use only CLRP public API endpoints and public exports; do not rely on local generated data, hidden files, manifests, setup scripts, or inferred database state.
3. Build an evidence table before deciding: target IDs, review batch/month, cutoff or boundary date, relevant application/license/premises records, related bonds, insurance, violations, complaints, incidents, settlements, restrictions, obligations, correspondence, field notes, address history, bulletins, and exports.
4. Use roster or batch exports to confirm coverage. Include every required current application/license from the relevant batch or review set, and no unrelated records.
5. Normalize matching keys conservatively: compare exact IDs first, then legal/principal/facility names, premises IDs, addresses, cities, policy/bond identifiers, and source record IDs. Do not spread shared-address or name-similar records across entities unless the task's confidence category supports a manual shared-address match.
6. Apply cutoff dates exactly. Exclude records after a release boundary or review cutoff when the task says to use pre-boundary evidence, and count excluded post-boundary matched records when the schema asks for a method flag.
7. Recompute all summary counts from the final arrays immediately before returning JSON.

## Business Rules

### Contractor Eligibility

- Review every application in the requested contractor batch.
- `APPROVE` normally requires `NO_DEFICIENCY` and no staff action.
- Use `HOLD` for remediable or verification issues such as bond shortfall, cancelled or missing bond replacement, insurance verification, unresolved penalties, field-note holds, correspondence holds, experience verification, missing financial statements, or exam/rule shortfalls.
- Use `DENY` for disqualifying conduct or adverse prior registration when the public record supports denial under the active rules.
- Attach only the reason codes supported by the template, sorted in template enum order. Do not pair `NO_DEFICIENCY` with deficiency codes.
- Select next actions and manual followups from the controlled enums. If multiple independent hold reasons require staff work, use the template's combined/manual review option when available.
- For bulletins or rule changes, use bulletins active for the review cutoff or quarter. Mark an application as changed only when the active bulletin changes its outcome or adds/removes a scored deficiency compared with the prior rule.
- Count deficiency codes by application occurrence, not by the number of raw supporting records, unless the template explicitly asks for record counts.

### Restricted Alcohol Licensing

- Center the review on the target application and premises. Use same-month comparison records only to distinguish standard obligations from premises-specific restrictions and to compute requested comparison counts.
- Separate license-type or all-license standard obligations from location/premises-specific controls. Standard obligations are not evidence of premises-specific restriction unless the record explicitly ties them to the site.
- For successor or same-premises risk, look for same premises ID, same address overlap, prior settlements at the address, prior licensee history, unresolved or high-severity incidents, and pending or blank dispositions.
- Current proposed restrictions, settlement terms, and active premises controls drive monitoring controls, first-90-day checks, records requests, and escalation triggers.
- Verification gaps should reflect missing or unverified evidence, unresolved incident dispositions, settlement timing issues, standard-control overlap, or unclear successor separation. Use the exact gap/status enums in the template.

### Renewal Manual-Review Queues

- Start from the current renewal roster for the specified release batch. Queue only current licensees from that roster.
- Match violations by license ID when available, then facility name and address. Use city violation APIs and address search as supporting evidence.
- Exclude post-boundary violation records from ranking when the task requests pre-boundary review, and populate boundary-exclusion method flags.
- Rank the required queue size using the task's business signal, usually violation count first and most recent included violation date as a tiebreaker. Keep ranks contiguous and ascending.
- Use `exact`, `close`, or `shared_address_manual` confidence only when supported by the matching evidence. Set shared-address method flags truthfully and do not duplicate a shared-address violation onto every nearby licensee.

## Output Conventions

- Return exactly one JSON object. Do not wrap it in Markdown and do not add narrative outside the object.
- Preserve required constants from the template such as batch IDs, task IDs, application IDs, premises IDs, review months, boundary dates, and queue sizes.
- Use controlled enum values exactly as written, including case and spaces.
- Use `YYYY-MM-DD` for dates and `YYYY-MM` for review months. Counts are integers.
- Respect ordering rules:
  - application decisions and manual followups: ascending `application_id`
  - reason and followup codes: template enum order
  - source IDs and bulletin IDs: ascending ID
  - obligation/control/gap/request/trigger lists: ascending code when specified
  - ranked queues: `rank` 1 through the required queue size
- Use empty lists only when allowed. If the template provides a sentinel such as `NO_DEFICIENCY` or `NO_VERIFICATION_GAPS`, use it according to the template rather than inventing prose.
- Do not add evidence text, explanations, confidence notes, or extra properties unless the schema explicitly requests them.

## Pitfalls

- Do not hard-code train task IDs or prior outcomes; read identifiers and required values from the current prompt/template.
- Do not let public exports and JSON APIs drift: reconcile IDs and counts before finalizing.
- Do not include applications outside the target batch/month just because their related records matched by name or address.
- Do not treat a record with a date after the cutoff as supporting a cutoff decision.
- Do not count raw incidents, violations, or deficiencies in summaries when the schema asks for affected applications.
- Do not confuse standard license obligations with premises-specific restrictions.
- Do not use approximate name matches as exact matches; lower the confidence or require manual followup when the schema supports it.
