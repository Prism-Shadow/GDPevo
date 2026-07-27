---
name: investigation-review-hub-json
description: Build structured JSON preservation, production-readiness, privilege, retention, QC, and remediation analyses from an Investigation Review Hub. Use when a task asks Codex to return a schema-conforming JSON object for a legal investigation matter using hub endpoints, task-local payloads, subpoena categories, productions, custodian sources, documents, privilege logs, QC findings, retention events, or remediation actions.
---

# Investigation Review Hub JSON

## Source Discipline

Use only the task prompt, task-local input payloads, and the running Review Hub endpoints named by the task. Do not inspect environment source files, database files, generated manifests, hidden notes, answer keys, or evaluation files. If a task provides `environment_access.md`, use it only to obtain the live base URL, API key, and allowed endpoint list.

Read every task-local payload before querying. Treat `answer_template.json` as the output contract: required keys, field names, enums, ordering rules, numeric precision, and JSON-only output requirements override all defaults here.

## Hub Access

Fetch the schema first, then retrieve matter-scoped evidence from every relevant endpoint:

```bash
BASE="<hub base url>"
KEY="<api key if supplied>"
curl -sS "$BASE/api/schema"
curl -sS "$BASE/api/matters?matter_id=<matter_id>"
curl -sS "$BASE/api/subpoena-categories?matter_id=<matter_id>"
curl -sS "$BASE/api/productions?matter_id=<matter_id>"
curl -sS "$BASE/api/custodian-sources?matter_id=<matter_id>"
curl -sS "$BASE/api/documents/search?matter_id=<matter_id>"
curl -sS "$BASE/api/privilege-log?matter_id=<matter_id>"
curl -sS "$BASE/api/qc-findings?matter_id=<matter_id>"
curl -sS "$BASE/api/retention-events?matter_id=<matter_id>"
curl -sS "$BASE/api/remediation-actions?matter_id=<matter_id>"
```

Use SQL only for cross-checks or compact aggregation. The query endpoint expects a JSON body with `sql` and the task-provided API key header:

```bash
curl -sS -H "Content-Type: application/json" -H "X-API-Key: $KEY" \
  --data "{\"sql\":\"select * from retention_events where matter_id = '<matter_id>'\"}" \
  "$BASE/api/query"
```

If available, run `scripts/fetch_hub_snapshot.py` to collect all standard endpoint rows into one JSON object:

```bash
python3 skill/scripts/fetch_hub_snapshot.py --base-url "$BASE" --matter-id "<matter_id>" --api-key "$KEY"
```

## Evidence Model

Build a matter-only evidence ledger from these sources:

- `matters`: hold date, agency, investigation type, and matter metadata.
- `subpoena-categories`: category codes, labels, date ranges, and topic tags.
- `productions`: category production counts, withheld counts, zero-claim statements, status, and notes.
- `custodian-sources`: source status, source type, post-hold flag, affected categories, issue tags, and remediation-source availability.
- `documents/search`: specific document IDs supporting responsiveness miscoding, zero-claim contradictions, privilege exposure, or QC source references.
- `privilege-log`: incomplete logs, waived third-party communications, over-designation, family mismatch, withheld/logged counts, and affected categories.
- `qc-findings`: responsiveness miscoding, zero-claim contradictions, miscoded privilege, family breaks, source references, severity, and document counts.
- `retention-events`: post-hold losses, pre-hold policy destruction, auto-purge/system windows, missing required records, available records, volume units, and policy periods.
- `remediation-actions`: target IDs, owners, priorities, due days, and action descriptions. Use them to confirm priority and ownership, but map labels to the enums in the answer template.

Filter aggressively to the requested matter. Ignore routine noise, remediated items, metadata-only issues, and records whose notes say they have no unresolved production impact unless the prompt or template explicitly asks for them. Prefer records that are named in the prompt, targeted by remediation actions, carry high or critical severity, have production-impacting issue tags, contradict a production position, or directly support another selected issue.

## Classification

Map evidence to the closest enums allowed by the active template:

- Post-hold destruction or loss: preservation/post-hold-loss issue, critical or high risk, destroyed/lost source status, source-lost production impact, disclosure action.
- Policy-compliant pre-hold destruction: low risk retention event, pre-hold policy status, usually no remedial production action beyond documenting the loss.
- Auto-purge or active system retention window: communication/system gap; use a cutoff date or purge window when provided; document the gap unless an available archive makes collection the better action.
- Required record that should exist but is missing: missing-required-record issue, high risk when retention policy still applies, locate or escalate action.
- Uncollected personal or side-channel source: personal-source or collection-gap issue, source-missing impact, collection action by forensics, client IT, or eDiscovery owner as the template permits.
- Available retained source or archive: retained/available source entry, source-available impact, search or collect archive action; include it even when it limits but does not erase an underlying gap if the template has an available-sources section.
- Responsiveness miscoding or zero-claim contradiction: recode-needed/not-produced/underproduced impact; use QC findings and supporting document IDs as references; count only the confirmed affected documents.
- Incomplete privilege log: privilege-log gap with withheld-unlogged impact; compute unlogged as withheld minus logged for the selected blocker.
- Third-party privilege waiver: privilege exposure/waiver issue; preserve the third-party label if the template has a field for it; action goes to privilege counsel when available.
- Privilege miscoding or over-designation: privilege correction or QC issue; use re-review, recode-and-log, downgrade, or QC remediation according to the template enums.

When multiple issues affect one category, choose the category status that best reflects the dominant blocker. Use a mixed or multiple-blockers status only when the template provides one and the category has independent material blockers.

## Metrics

Compute metrics from the selected material evidence, not from every noisy row in the hub. Common rules:

- Counts are whole integers.
- `top_risk_count`, issue counts, non-ready category counts, and available archive counts equal the number of selected objects of that kind.
- Category counts and category lists use the unique affected categories from selected open risks or gaps.
- Privilege withheld/logged/unlogged metrics come from selected incomplete-log blockers unless the template says to include all privilege issues.
- Third-party waiver counts come from selected waiver records.
- Miscoded responsive or privileged counts come from selected QC or document evidence.
- Destroyed box counts include only selected retention/source losses measured in boxes.
- Production-ready booleans are false when any selected material blocker remains open.

Reconcile metrics back to the object lists before finalizing; every metric should be explainable by one or more selected records.

## Output Assembly

Use stable hub IDs exactly as they appear. Sort category-code lists ascending, sort reference lists ascending unless operational priority is required, and follow the template's top-level ordering rules. Use `null` for genuinely unavailable nullable fields and `0` for non-applicable counts when the template requires an integer.

Build action plans from the material blockers, then rank them by operational urgency:

1. Preservation loss requiring disclosure.
2. Privilege waiver assessment or disclosure.
3. Responsiveness recoding and production.
4. Privilege log supplementation or privilege recoding.
5. Personal-source or archive collection.
6. Missing-record follow-up, system-gap documentation, monitoring, or no-action policy loss.

Prefer hub remediation-action owners, priorities, and due days when they map cleanly to the template. Otherwise choose the closest allowed owner/action enum based on the issue type and keep the rationale grounded in the selected evidence.

Before returning, validate the JSON against the template:

- All required top-level keys and item keys are present.
- All enum values are from the active template, not from hub labels unless they match.
- Lists follow the specified ordering.
- Numeric values are integers where required.
- No prose appears outside the JSON when the prompt asks for JSON only.
