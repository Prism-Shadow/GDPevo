---
name: investigation-review-hub-remediation
description: Solve Investigation Review Hub legal production, preservation, privilege, QC, retention, and remediation dashboard tasks. Use when a prompt asks Codex to query a running review hub at TASK_ENV_BASE_URL and return a strict JSON object conforming to an answer_template.json schema.
---

# Investigation Review Hub Remediation

Produce a schema-conformant JSON answer from the running Investigation Review Hub. Treat the hub and task-local payloads as the only business evidence.

## Source Rules

1. Read the prompt, every task-local payload, and the answer template before querying.
2. Identify the matter ID, base URL, allowed endpoints, and any required API key/header from the prompt or payloads.
3. Use only the running hub endpoints and task-local payloads. Do not inspect local environment source, database files, seed files, generated manifests, hidden notes, evaluator code, prior answers, or non-task paths.
4. Prefer hub stable IDs for matters, request categories, sources, documents, privilege records, QC findings, retention events, productions, and remediation actions. Do not invent evidence IDs.
5. Return exactly one JSON object. Do not include prose outside the JSON.

Optional helper: `scripts/hub_snapshot.py` can collect the common read-only endpoints into one JSON snapshot:

```bash
python3 skill/scripts/hub_snapshot.py --base-url "$TASK_ENV_BASE_URL" --matter-id "$MATTER_ID" --api-key "$API_KEY" > /tmp/hub_snapshot.json
```

Use the helper only as a convenience. If it misses data, query the endpoints or SQL API directly.

## Hub Discovery

Start with `/api/schema` when available. Then collect every relevant matter-filtered endpoint named by the task, commonly:

- `/api/matters`
- `/api/subpoena-categories`
- `/api/productions`
- `/api/custodian-sources`
- `/api/documents/search`
- `/api/privilege-log`
- `/api/qc-findings`
- `/api/retention-events`
- `/api/remediation-actions`
- `/api/query`

For SQL-style access, use only the task-provided API header. Use SQL to join records by `matter_id`, category codes, source IDs, document IDs, privilege IDs, QC IDs, retention event IDs, and action IDs when endpoint responses are fragmented.

## Working Method

Build an evidence ledger before drafting the answer:

1. Matter and request categories: category code, label, production or readiness state, and scoped matter ID.
2. Custodian/source evidence: collection status, destroyed or lost status, personal or off-platform sources, active-system purge issues, retained or available archives, retention periods, volume counts, and category impacts.
3. Retention events: event date, hold date, pre-hold versus post-hold timing, policy section, retention period, volume, cutoff dates, and affected categories.
4. Document/QC evidence: responsive documents miscoded nonresponsive, zero-claim contradictions, documents needing recode, not-produced documents, missing required records, QA/QC issue IDs, and supporting document IDs.
5. Privilege evidence: withheld counts, logged counts, unlogged counts, third-party recipients, waived privilege, over-designation, miscoded privileged or nonprivileged records, and protocol compliance.
6. Remediation actions: action type, owner, priority/rank, target refs, due dates or due-day offsets, and impacted categories.

Resolve conflicts in favor of more specific hub records over rollups. Use rollups only after verifying they match the underlying records, or when the template explicitly asks for rollup-only metrics.

## Issue Normalization

Classify only material non-ready, open, remediation-relevant, or disclosure-relevant items unless the template asks for complete or no-gap records.

Preservation and retention:

- Post-hold destruction, lost devices, destroyed archives, and unavailable active systems are high or critical preservation losses. They usually affect production as `source_lost` and require disclosure or forensic recovery if those enum values exist.
- Pre-hold policy-compliant destruction is a low-risk policy loss. Include it only when the template asks for retention events or policy losses; place no-action items after active remediation.
- Missing records that should exist are `missing_required_record` or `should_exist_missing` and require locating or escalation.
- Uncollected personal phones, personal email, messaging apps, board sources, or other off-platform sources are source collection gaps.
- Available archives are remediation paths. List them in retained or available source sections and connect them to the categories for which they limit loss.

Privilege:

- Incomplete logs are based on withheld minus logged counts. Use explicit unlogged counts if the hub provides them; otherwise compute `unlogged = withheld - logged`.
- Third-party recipients or non-privileged outsiders on withheld/logged documents indicate waiver risk or privilege exposure.
- Privileged documents coded nonprivileged, or nonprivileged/business-only material coded privileged, are privilege QC issues. Map them to the closest enum available in the template.
- For metrics that say "selected incomplete-log blockers only," count only the incomplete-log blocker records, not all privilege records.

Responsiveness and production QC:

- Responsive documents coded nonresponsive, zero-claim contradictions with responsive documents, and records marked not produced are responsiveness gaps requiring recode and production.
- Include supporting document IDs with the QC finding ID when the template asks for `source_refs`, `issue_refs`, `record_refs`, or `target_refs`.

Category aggregation:

- A category is non-ready or open if any selected issue affects it.
- Combine all supporting issue/source/document refs for the category and sort them ascending.
- Choose the category status and production impact by the most consequential blocker: preservation/source lost, missing required record, personal source/source missing, privilege waiver/exposure, privilege log/withheld unlogged, responsiveness/not produced or underproduced, available archive/source available, then no open gap.
- `open_issue_count` counts the distinct selected issue records summarized for that category, not every supporting document.

## Metrics

Compute metrics from the selected evidence used in the answer, following each field description exactly.

- Count events as distinct hub event or issue records.
- Count sources as distinct source records.
- Count categories as unique affected category codes across included open or gap records.
- Count boxes, days, months, documents, emails, reports, and sources using the unit requested by the template.
- Use zero for not-applicable numeric fields unless the template requires `null`.
- Use `null` for missing dates, third parties, policy sections, retention periods, and other nullable string/date fields.
- Set readiness booleans to false when any material blocker remains open, noncompliant, missing, uncollected, unrecovered, unlogged, or needing recode.

## Action Ranking

Prefer existing hub remediation action IDs and ranks. If the hub provides no action plan but the template requires one, derive a deterministic plan from the selected issues without inventing supporting evidence IDs.

Rank actions by operational urgency:

1. P0 disclosure or readiness hold for critical post-hold loss, source lost, or unrecoverable preservation issues.
2. P1 waiver assessment and disclosure for third-party privilege exposure.
3. P1 recode and produce for responsive miscoding or not-produced responsive documents.
4. P1 supplement privilege logs for withheld-unlogged blockers.
5. P1 collect personal devices, personal email, messaging sources, board sources, or other uncollected sources.
6. P1 search or collect available archives that limit loss.
7. P1/P2 privilege recode, QC remediation, over-designation review, missing-record follow-up, or monitoring.
8. Low-risk pre-hold policy destruction receives no action or documentation last when included.

Use owner values allowed by the template. Typical mappings are outside counsel for disclosure/readiness holds, privilege counsel for waiver, privilege team for log supplementation and over-designation, review QC for recoding/QC defects, forensics or client IT for personal-device collection, ediscovery vendor for archive searches, and records/compliance teams for retention or missing-record follow-up.

## JSON Assembly

Follow the answer template over any generic rule in this skill:

- Include exactly the required top-level keys unless optional keys are explicitly requested.
- Use only enum values present in the template.
- Preserve field names, scalar types, booleans, integers, arrays, and nullable fields exactly.
- Apply every ordering rule in the template. Sort category-code arrays and ID/ref arrays ascending unless action priority order is explicitly required.
- Keep IDs exactly as the hub spells them.
- Do not include categories with `ready`, `complete`, `no_current_gap`, or `no_open_gap` unless the template asks for them.
- Validate the final response as parseable JSON before returning it.
