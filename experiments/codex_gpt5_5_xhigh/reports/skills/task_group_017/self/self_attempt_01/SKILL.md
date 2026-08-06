---
name: investigation-review-hub-analysis
description: Use for Investigation Review Hub legal review tasks that require matter-scoped production, preservation, retention, privilege, QC, source-collection, or remediation analysis returned as strict schema-conforming JSON.
---

# Investigation Review Hub Analysis

## Core Rule

Produce the requested JSON from the task-local prompt/payloads and the running Investigation Review Hub only. Do not inspect local environment source files, database files, generated data files, hidden manifests, evaluation files, or prior answer files. Do not include narrative outside the final JSON when the prompt requires JSON-only output.

## Required Inputs

1. Read the task prompt first.
2. Read every file in the task's `input/payloads/` directory.
3. Treat `answer_template.json` as the output contract: required keys, enum choices, field types, numeric precision, and ordering rules.
4. Treat other task-local payloads as client/request context only unless they explicitly provide evidence. The hub remains the source of record for business facts.
5. If network credentials/endpoints are provided in an `environment_access.md`-style file, use only those values and only the allowed endpoints.

## Hub Access

Use the task-provided base URL, not local files. Start with:

- `GET /api/schema` to confirm table/field names.
- `GET /api/matters` to confirm the matter metadata and hold date.
- Matter-scoped reads or SQL through `POST /api/query` for:
  - `subpoena_categories`
  - `production_stats`
  - `custodian_sources`
  - `review_documents`
  - `privilege_entries`
  - `qc_findings`
  - `retention_events`
  - `remediation_actions`

Always filter by the requested `matter_id`. Similar issue labels and noisy records may exist for other matters.

Useful query pattern:

```sql
select * from TABLE
where matter_id = 'REQUESTED_MATTER_ID'
order by STABLE_ID_OR_CATEGORY;
```

## Evidence Triage

Build a matter evidence map before drafting the answer:

- Categories: stable category codes, titles, request topics, and date ranges.
- Productions: category-level status, produced/withheld/responsive/nonresponsive counts, zero-claim reasons, and production notes.
- Sources: source ID, status, source type, post-hold flag, category impacts, issue tags, and notes.
- Retention: event ID, event date, hold date, status, policy section, period, volume, affected categories, source ref, and notes.
- Privilege: entry ID, issue type, category, withheld/logged/doc counts, third-party flag, and notes.
- QC: finding ID, issue type, document count, affected category, source refs, severity, and notes.
- Remediation: action ID, action type, priority, severity, owner, target ref, due days, and description.
- Documents: use document searches to corroborate specific QC/source refs, zero-claim contradictions, miscoding, privilege status, and production status.

Prioritize records that are explicitly action-linked, high/critical severity, post-hold, not collected/lost, incomplete-log, waiver, miscoding, zero-claim contradiction, should-exist-missing, or available-remediation-source records. Treat routine metadata gaps, sampling notes, corrected overlays, and "ordinary review variance" as noise unless the prompt/template asks for all records of that type.

## Classification Heuristics

Use the output template's enum names exactly. Map hub evidence to the closest allowed enum:

- Post-hold destroyed/lost retention or source records: preservation loss, post-hold loss, source lost, disclose preservation issue, forensic recovery/restore where available.
- Pre-hold policy destruction: policy-compliant/pre-hold loss, usually lower risk and no disclosure action unless the template asks for all retention events.
- `system_loss`, `auto_purged`, deleted channels, missing active-system windows: communication or active-system loss; check for available archives before calling the loss irretrievable.
- `not_collected` or partial personal sources: personal/source collection gap; count sources, not documents.
- Available archives or retained sources: remediation path, not loss; identify which categories the source can limit/remediate.
- `zero_claim_contradicted` production or QC zero-claim findings: responsiveness miscode/zero-claim contradiction, recode and produce.
- Privilege `incomplete_log`: withheld minus logged equals unlogged; action is supplement privilege log.
- Privilege `third_party_waiver`: waiver assessment/disclosure; count the affected documents/emails from the privilege entry.
- Privilege `over_designated` or QC `miscoded_privilege`: privilege recode/downgrade/re-review, depending on template choices.
- `should_exist_missing`: missing required record; action is locate missing record or counsel escalation.

When an enum set differs by template, choose from that template only; do not invent enum values.

## Metrics

Compute metrics from the same selected evidence used in the answer:

- Counts are whole integers.
- Unlogged privilege documents = `withheld_count - logged_count` for selected incomplete-log entries.
- Withheld/logged metrics should follow the template wording. Some templates want only selected incomplete-log blockers, not every privilege entry.
- Source counts count source records, not affected categories.
- Event counts count event records, not categories or volume.
- Volume metrics use the specified unit in the template; do not combine boxes with files/reports/exports unless the template asks for all volumes.
- Category counts are unique category codes with selected open gaps/risks.
- Readiness booleans are false when any material blocker remains open, unremediated, or production-impacting.

## Output Assembly

1. Anchor each finding/risk/action to stable hub IDs whenever possible.
2. Use category codes exactly as shown by the hub.
3. Include only categories requested by the template: all non-ready categories, all categories with material gaps, or all categories if explicitly required.
4. Populate every required field. Use `0`, `null`, empty lists, or the template's "not applicable" enum where appropriate.
5. Sort arrays exactly as specified by `answer_template.json`; sort category-code lists and record-reference lists ascending unless the template says otherwise.
6. Keep owner/action labels within template enums. If hub owner/action names differ from template enums, normalize to the nearest operational role/action.
7. Return exactly one valid JSON object with no comments, markdown, or explanatory text when the prompt asks for JSON only.

## Final Validation

Before finalizing:

- Confirm every top-level key required by the template is present.
- Confirm every enum value appears in the template.
- Confirm all required item fields are present in every array item.
- Recalculate metrics from the selected records.
- Check sort order for arrays, category sets, and reference lists.
- Ensure no task-specific final answers from examples have been reused.
