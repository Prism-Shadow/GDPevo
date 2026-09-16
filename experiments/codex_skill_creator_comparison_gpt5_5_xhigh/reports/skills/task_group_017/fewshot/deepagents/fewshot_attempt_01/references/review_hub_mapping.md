# Review Hub Mapping Reference

Use this reference after collecting matter-filtered Review Hub evidence and before writing the final JSON.

## Endpoint Evidence

- `/api/schema`: table and column names.
- `/api/matters`: matter metadata, including hold date and agency.
- `/api/subpoena-categories`: request category codes, titles, date ranges, and topic tags.
- `/api/productions`: production counts, withholding counts, zero-claim status, and production readiness notes by category or batch.
- `/api/custodian-sources`: source collection, personal device, archive, loss, and availability records.
- `/api/documents/search`: document-level responsiveness, privilege, production status, issue tags, and summaries.
- `/api/privilege-log`: privilege counts, log completeness, third-party indicators, and privilege issue notes.
- `/api/qc-findings`: QC defects such as miscoding, zero-claim contradictions, and privilege coding problems.
- `/api/retention-events`: destruction, purge, missing-record, hold-date, policy, and volume evidence.
- `/api/remediation-actions`: candidate actions and target refs; use as supporting evidence, not as a substitute for issue analysis.
- `/api/query`: read-only SQL access. Use it when the prompt provides the API key or when a GET endpoint appears capped; always filter by the prompted matter ID.

## Issue Classification

Prioritize material blockers. Routine sampling, load-file cleanup, or custodian follow-up rows are usually noise unless another table shows a material defect for the same target.

- Post-hold loss: retention or source record shows destruction/loss after the hold date. Use critical or high risk, `source_lost` production impact, and disclosure-oriented action if available in the template.
- Pre-hold policy loss: retention event shows policy-compliant destruction before the hold. Use low risk and no-remediation/no-action style only if the template asks to report policy losses.
- Auto-purge or active-system loss: communication system retention window, purge cutoff, deleted channel, or active system missing history. Report as communication gap or source loss depending on the template.
- Missing required record: retention/audit/compliance record should exist but is missing. Use missing-required-record status and a locate/escalate action.
- Personal source gap: personal email, phone, SMS, messaging, or device source is not collected or partially collected. Use collection action; classify as source missing unless an archive limits the loss.
- Archive available: source status or notes show an archive or retained source remains available. Put it in the retained/available source section and link the categories for which it limits loss.
- Responsiveness miscode: QC finding or document evidence contradicts nonresponsive coding, zero-production claims, or not-produced status. Use recode-and-produce action.
- Privilege log gap: privilege entry shows withheld greater than logged, incomplete log, or protocol noncompliance. `unlogged = withheld_count - logged_count`.
- Third-party waiver: privilege evidence names a third-party recipient or waiver issue. Use waiver assessment/disclosure action and carry the third-party field when the template has one.
- Privilege miscoding: QC or privilege evidence shows privileged material coded nonprivileged, over-designation, downgrade, or privilege recode need. Use the template's closest privilege correction action.

## Category Coverage

Build category objects from the union of material issues affecting each category. Include a category only when the template asks for non-ready, open-gap, affected, or coverage categories.

When multiple issues affect one category, use the strongest available status and impact:

1. preservation/source loss
2. mixed preservation plus missing record or multiple blockers
3. privilege exposure or underproduced privilege corrections
4. privilege-log gap or withheld-unlogged impact
5. responsiveness gap or recode-needed impact
6. personal/source collection gap
7. archive available/source available
8. missing required record
9. no open gap

For `open_issue_count`, count distinct material issue records summarized for that category, not every supporting document ID. Include supporting document IDs in refs only when they directly anchor a QC or responsiveness issue.

## Action Planning

Use remediation action rows as hints for targets, due windows, and operational urgency, then normalize to the template's enums.

Default priority order:

1. Disclose or assess preservation loss, post-hold destruction, or privilege waiver.
2. Supplement incomplete privilege logs and remediate privilege exposure.
3. Recode and produce confirmed responsive or miscoded documents.
4. Collect missing personal/device/source data.
5. Search or collect available archives.
6. Locate missing required records.
7. Document policy-compliant losses or monitor only.

Owner normalization is template-dependent. Map the work, not the raw hub owner string:

- preservation disclosure and certification risk: outside counsel or litigation counsel
- forensic recovery or personal device collection: forensics or e-discovery vendor
- source/archive collection: e-discovery vendor, records management, or client IT
- responsiveness and QC recoding: review QC, review vendor, or review operations
- privilege log, waiver, and privilege recode: privilege team or privilege counsel
- records retention and missing audits: records management, compliance audit, or client legal

If action IDs must be generated and the hub does not provide suitable IDs in the required enum/style, create stable sequential IDs within the answer. Do not reuse IDs from unrelated routine actions.

## Metric Rules

Compute from the output issue set unless the template explicitly asks for all matter rows.

- Count top risks, retention events, communication gaps, available archives, personal source gaps, and missing records by distinct selected records.
- Count affected categories from the union of category codes in selected material issues.
- Sum destroyed boxes only from retention/source loss records whose unit is boxes.
- Sum miscoded responsive documents from QC findings or selected document refs that require recoding and production.
- For privilege blockers, use selected privilege entries. Sum withheld, logged, unlogged, waived, third-party, and miscoded-privilege counts according to the metric field names.
- Set production-ready/readiness booleans to false if any selected material blocker remains open, not collected, incomplete, protocol-noncompliant, waived, or needs recode.

## Output Hygiene

Use the template field names exactly. Do not add narrative, citations, comments, or extra fields. Keep category codes uppercase and sorted. Sort hub ID reference arrays lexicographically unless the template says otherwise.
