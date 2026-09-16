---
name: investigation-review-hub-gap-analysis
description: Use this skill whenever a task asks for a structured JSON legal or eDiscovery analysis from an Investigation Review Hub, especially subpoena, grand jury, SEC, DOJ, production readiness, remediation dashboard, retention gap, privilege-log, QC, or custodian-source gap tasks with TASK_ENV_BASE_URL and input/payloads/answer_template.json. It guides Codex to query the hub as source of record, normalize stable IDs and category impacts, compute metrics, and return schema-valid JSON only.
---

# Investigation Review Hub Gap Analysis

Use this skill to produce a final JSON object for legal investigation review tasks where the evidence lives in a running Investigation Review Hub and the required shape is defined by `input/payloads/answer_template.json`.

The winning behavior is systematic evidence collection, schema-first normalization, and strict final validation. Do not rely on narrative summaries or partial endpoint browsing when the task asks for structured production, retention, privilege, QC, or remediation analysis.

## Source Boundary

Use only:

- The current task prompt.
- Files under the task input directory, especially `input/payloads/answer_template.json` and any local context payloads.
- The running Investigation Review Hub endpoints named in the prompt or context payloads.
- `environment_access.md`, when present, only to obtain the base URL or network access details for the running hub.

Do not inspect local environment source files, database files, seed files, generated manifests, hidden notes, answer files, evaluator files, or previous runs. Treat the hub as the source of record for business facts.

## One-Pass Workflow

1. Read the prompt, then read every file under `input/payloads/`.
2. Extract the matter ID, output schema, allowed enums, ordering rules, API key header if provided, and all context category labels.
3. Discover the hub before answering. Start with `/api/schema` if available, then collect all matter-scoped records from the relevant endpoints.
4. Build an evidence table covering categories, productions, custodian sources, documents, privilege-log records, QC findings, retention events, and remediation actions.
5. Select the material issues that affect production readiness, collection completeness, preservation, privilege exposure, responsiveness coding, or remediation.
6. Fill the exact JSON shape from `answer_template.json`.
7. Validate the candidate answer against the template and fix schema, enum, count, sorting, or reference errors.
8. Return exactly one JSON object and no prose outside it.

## Hub Collection

Use the task-provided base URL and API key only. If a SQL-style endpoint is useful, use the header and key from the prompt or payload, commonly `X-API-Key`.

You may use the bundled dump helper as a first pass:

```bash
python /path/to/this/skill/scripts/hub_dump.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --matter-id "$MATTER_ID" \
  --api-key "$API_KEY" \
  --out /tmp/hub_dump.json
```

If the helper misses records, query manually with `curl` or a short script. Useful endpoints commonly include:

- `GET /api/schema`
- `GET /api/matters`
- `GET /api/subpoena-categories`
- `GET /api/productions`
- `GET /api/custodian-sources`
- `GET /api/documents/search`
- `GET /api/privilege-log`
- `GET /api/qc-findings`
- `GET /api/retention-events`
- `GET /api/remediation-actions`
- `POST /api/query`

Cross-check counts with SQL when endpoints are nested, filtered, or ambiguous. Preserve every stable hub ID exactly as returned.

## Evidence Table

Before drafting JSON, create a working table or notes with one row per possible issue. Include:

- Stable anchor ID for the issue.
- Supporting source, event, document, QC, privilege, and action IDs.
- Affected request category codes.
- Current status, severity, source status, and production impact.
- Counts: documents, withheld, logged, unlogged, sources, boxes, days, months, emails, reports, or other template units.
- Recommended action, owner, priority, and due timing when the hub provides them.

This intermediate table prevents mixing category rollups, source records, document examples, and privilege metrics.

## Issue Mapping

Always use enum values from the current template. If the exact wording below is not available, choose the closest enum in that template.

- Post-hold destruction, lost source, or preservation failure: map to `post_hold_loss` or preservation loss, `source_lost`, and disclosure/escalation action. Count distinct loss events separately from affected categories.
- Policy-compliant pre-hold destruction: include only when the task asks for retention or preservation review; mark low risk and use the no-action/document-policy-loss option when available.
- Active-system loss, auto-purge, deleted collaboration channels, or unavailable historical messages: map to system/communication gap fields and document the cutoff or purge window.
- Uncollected personal email, phone, messaging, laptop, board, or custodian source: map to collection or personal-source gap, `source_missing`, and collect/forensic action. Source-count metrics count distinct sources.
- Available archive or retained source: include in the retained/available source section, not as a top risk unless the template asks for archive risks. Record which categories the archive can mitigate.
- Responsive documents coded nonresponsive, zero-production claims contradicted by documents, or QC findings showing responsive misses: map to responsiveness miscoding, `not_produced` or `underproduced`, and recode-and-produce action. Include both QC IDs and document IDs as supporting refs.
- Privilege log gap: calculate `unlogged = withheld - logged` for the selected incomplete-log blocker. Use supplement-log action and protocol-noncompliant/incomplete-log status.
- Third-party privilege exposure or waiver: capture the third party exactly if the hub provides it; count waiver documents separately from incomplete-log documents.
- Privileged documents coded nonprivileged, over-designation, downgrade, or privilege QC issues: use the template's privilege miscoding, downgrade, or QC remediation enum. Do not merge these counts into incomplete-log metrics unless the template explicitly says to.
- Missing required record, required report, audit, certification, or file that should exist: map to missing-required-record or should-exist-missing and locate/escalate action.

## Category Rollups

For category sections such as `category_statuses`, `category_coverage`, or `readiness_statuses`:

- Include categories with material open gaps, losses, blockers, or remediation paths. Omit complete/no-gap categories unless the template asks for all categories.
- Aggregate every supporting record ID for that category, including anchor IDs and document or QC support IDs when they explain the status.
- Sort category codes ascending inside each category list and sort the category section by `category_code`.
- `open_issue_count` counts distinct issue/risk/source records summarized for the category, not every supporting document ID.
- Choose the category status and recommended action based on the strongest current blocker for that category, while respecting the template enum set. Privilege exposure and post-hold source loss usually outrank ordinary collection gaps; recode-and-produce usually outranks monitoring.
- If a source gap is partly mitigated by an available archive and the template has a combined status such as `source_gap_with_archive_available`, use it.
- If a category has multiple operational blockers and the readiness template has a multiple-blocker enum, use it and list required actions in operational priority order.

## Metrics

Compute metrics from the selected material issue set, not from all possible hub records unless the template says otherwise.

Use these conventions:

- Whole integers only for counts and days.
- `unlogged` privilege count is withheld minus logged for the selected incomplete-log blocker.
- Do not add waiver counts, over-designation counts, or privilege-miscoding counts to incomplete-log metrics unless the template field description explicitly includes them.
- Post-hold loss event counts are distinct destruction/loss events, not documents or categories.
- Personal source gap counts are distinct uncollected personal sources.
- Available archive counts are distinct retained or archive sources that remain a remediation path.
- Destroyed box metrics count only destroyed source volume where the relevant event is measured in boxes; use 0 for destroyed events measured in documents, emails, reports, or sources.
- Affected/nonready category counts are unique category codes in the final open-gap or nonready category list.
- Boolean readiness fields are false whenever any material blocker remains open.

When a metric name and description disagree, prefer the detailed field description in `answer_template.json`, then the prompt, then the field name.

## Priority Actions

Use hub remediation candidates when present. Otherwise derive action plan items from the material issue table.

Typical priority order:

1. P0 critical post-hold loss or preservation issue requiring outside-counsel disclosure.
2. P0/P1 recode-and-produce items that directly underproduce responsive documents.
3. P1 privilege waiver assessment or privilege-log supplementation.
4. P1 privilege recode/QC remediation.
5. P1 collection of personal or missing sources.
6. P1/P2 archive searches or retained-source remediation.
7. P2/P3 policy-compliant losses, monitoring, documentation, or no action.

Combine targets only when the action type, owner, priority, due timing, and affected categories are logically the same. Keep `target_refs` and `category_impacts` sorted.

## Final Validation

Save a draft answer to a temporary file, then run:

```bash
python /path/to/this/skill/scripts/validate_template_answer.py \
  --template input/payloads/answer_template.json \
  --answer /tmp/candidate_answer.json
```

Fix every reported error before final output. Also manually verify:

- The top-level keys match the template and are in the expected logical order.
- All enum strings are exact template values.
- Required object keys are present, using `0` for non-applicable numeric counts and `null` for unknown or not-applicable strings/dates.
- Lists are sorted by the template ordering rules.
- Stable IDs and category codes come from the hub, not from invention or examples.
- The final response is raw JSON only.
