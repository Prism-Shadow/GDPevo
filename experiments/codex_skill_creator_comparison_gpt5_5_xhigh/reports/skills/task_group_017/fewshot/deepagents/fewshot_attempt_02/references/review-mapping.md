# Investigation Review Mapping

Use this reference after collecting hub data and reading the task's answer template. Treat the
template as the output contract; these rules help choose and normalize the evidence.

## Evidence Selection

- Use hub records as the source of record for business facts. Task-local payloads can provide matter
  context, category labels, endpoint hints, and the answer schema.
- Include material open blockers and remediation paths. Exclude categories and records that are
  complete, ready, closed, or have no current gap unless the template explicitly asks for them.
- Keep stable hub IDs exactly as returned. Sort ID lists and category-code lists ascending unless the
  template provides a different rule.
- Anchor each issue to the strongest stable record: a retention event for destroyed or missing
  records, a source record for uncollected personal devices or available archives, a privilege-log
  record for log/waiver issues, and a QC/document record for responsiveness or coding defects.
- Include supporting document IDs when they prove a QC or zero-claim issue, but count the QC issue as
  one issue for category rollups unless the template asks for document-level issue counts.

## Issue Normalization

- Post-hold destroyed or lost data: classify as `post_hold_loss` or the closest preservation-loss
  enum; use critical/high severity, `source_lost`, and disclosure/escalation action.
- Pre-hold destruction that followed an ordinary retention policy: classify as a policy loss with low
  risk and no remediation action, while still counting it in retention-focused schemas.
- Required record that should exist but is missing: classify as `missing_required_record` or
  `should_exist_missing`; action is locate/follow up with the responsible record owner.
- Uncollected personal email, phone, SMS, Signal, or similar source: classify as
  `personal_source_gap` or collection gap; action is forensic/personal-device collection.
- Available archive or retained source: include in retained/available source sections; it can limit
  loss for the affected categories even when an active system is unavailable.
- Responsiveness miscode, zero-claim contradiction, or nonresponsive coding for responsive documents:
  classify as responsiveness gap/miscode; action is recode and produce. Use the supporting document
  IDs and QC finding IDs as refs.
- Privilege log gap: classify as protocol noncompliance or incomplete log; action is supplement log.
  `unlogged_count` is withheld minus logged for that specific blocker.
- Third-party privilege disclosure: classify as waiver or privilege exposure; action is waiver
  assessment and disclosure. Keep the third-party name/string when the hub provides one.
- Privileged documents coded nonprivileged or nonprivileged documents coded privileged: classify as
  privilege miscoding, over-designation, downgrade, or QC remediation using the closest template enum.

## Category Rollups

- Emit only non-ready or gap categories unless the schema requires all categories.
- For each category, collect all selected issues and remediation sources touching that category.
- Choose the category status by highest material impact: preservation/source loss, missing required
  record, personal source gap, archive available, privilege/log/waiver correction, responsiveness
  gap, then no gap.
- Use `multiple_blockers` or mixed-status enums when distinct issue families affect the same category
  and the template provides such an enum. If all blockers are privilege-correction variants, a
  privilege-log or privilege-correction status can be more precise than a generic multiple-blocker
  status.
- `open_issue_count` counts selected issue/source records summarized for the category, not every
  supporting document reference.

## Metrics

- Compute metrics from the same selected evidence used in the output sections.
- Whole-number counts only. Use `0` for non-applicable numeric fields, and `null` only where the
  template allows null strings/dates/counts.
- Privilege metrics for incomplete-log blockers should use only incomplete-log records. Count waiver
  documents and miscoded privilege documents in their dedicated metrics, not as unlogged log-gap docs.
- Affected-category metrics are the unique sorted categories represented in selected issues and
  retained/available remediation sources when those sources are part of the required output.
- Readiness booleans are false when any selected material blocker makes production not ready.

## Action Planning

- Prefer existing hub remediation action records, including their owner, priority, rank, and due-day
  data, when available.
- If constructing actions, rank by materiality and immediacy: preservation disclosure, waiver
  assessment, recode/produce, supplement log, collect missing personal/source data, search available
  archives, locate missing records, document policy losses.
- Group compatible actions with the same action type, owner, priority, and due timing when the schema
  supports multiple target refs. Keep separate actions when the schema is target-per-record or the
  operational owners differ.
