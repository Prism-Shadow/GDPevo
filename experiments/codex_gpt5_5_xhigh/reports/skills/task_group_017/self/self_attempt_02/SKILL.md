---
name: legal-investigation-api-json-review
description: SOP for solving legal investigation API tasks that require JSON-only production, collection, retention, privilege, and QC reviews from staged prompts and templates.
---

## Scope

Use this skill when a task asks for a structured legal investigation review using a shared JSON API. The goal is to reconcile matter metadata, subpoena categories, productions, collections, retention/destruction records, custodians, documents, privilege logs, QC events, and any task-local factual memo, then return only the JSON shape required by the task template.

## Inputs First

1. Read the task prompt, the task's `answer_template.json`, and any task-local factual payload named by the prompt.
2. Read the staged environment access note and set the API base URL from it wherever the prompt shows `<TASK_ENV_BASE_URL>`.
3. Treat the answer template as controlling: top-level keys, key order, enum spelling, required booleans, count fields, sort rules, and whether empty/zero values are allowed all come from the template.
4. Do not solve from the prompt alone. The prompt usually names the matter, target custodian or category focus, and the relevant endpoint families, but the defects and counts are in API records.

## API Habits

Fetch the canonical records directly, then use search only as a cross-check:

```bash
BASE_URL="<TASK_ENV_BASE_URL>"
MATTER_ID="<matter id>"
curl -fsS "$BASE_URL/api/matters/$MATTER_ID" | jq .
curl -fsS "$BASE_URL/api/subpoena_categories?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/production_logs?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/collection_events?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/retention_rules?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/destruction_events?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/custodians?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/documents?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/privilege_logs?matter_id=$MATTER_ID" | jq '.items'
curl -fsS "$BASE_URL/api/qc_events?matter_id=$MATTER_ID" | jq '.items'
```

List endpoints return wrapper objects with `count` and `items`; do not forget `.items`. The matter endpoint returns a direct object. Search returns a `results` object grouped by collection, so inspect its shape before piping it like a normal list endpoint.

## Join Map

Use these fields to build one evidence table before drafting JSON:

- `matter_id`: scope every endpoint to the target matter.
- `category_id` / `related_category_ids` / `category_ids`: join subpoena categories to production, collection, destruction, privilege, document, and action rows.
- `custodian_id`: filter for target custodians and confirm role, status, sources, and known gaps.
- `event_id`, `log_id`, `item_id`, `document_id`: cite source events and document markers exactly as emitted.
- `source_type`, `source_name`, `record_class`: normalize the source affected by a gap, archive, device, or retention rule.

## Evidence Reading

Matter records give hold date, subpoena date, deadline, regulator flags, and the high-level issue status.

Subpoena categories define the real request scope. Compare their labels, requested sources, topic tags, and date ranges against review coding and production trackers.

Production logs provide category-level counts and status. Prefer current or explicitly operative batches. Use `produced_count`, `withheld_privileged_count`, `privilege_logged_count`, `review_status`, and `notes`; translate raw statuses into the template's allowed enums.

Collection events show source readiness. Key fields are `status`, `missing_count`, `collected_count`, `hold_relation`, `reason`, `source_type`, `source_name`, `custodian_id`, and `related_category_ids`.

Retention rules explain whether missing material was within a policy period, covered by an archive override, or expected to remain available through a vendor or archive.

Destruction events drive timing analysis. Compare `pre_or_post_hold`, `event_date`, `quantity`, `record_class`, `recoverability`, and `policy_basis` to the matter hold date and local memo facts.

Custodians identify former or active status, relevant sources, role-specific scope, duplicate aliases, and known gaps.

Documents are often marker records for miscoding or privilege problems. Use `review_coding`, `privilege_coding`, `production_status`, `tags`, `summary`, and `category_ids` to confirm whether documents were incorrectly excluded, produced, withheld, or need review.

Privilege logs provide `logged_status`, `privilege_status`, `production_status`, `record_count`, `overdesignation_flag`, `waiver_risk`, and notes. Compare these with production log counts instead of assuming all privilege rows are material.

QC events usually give the cleanest defect counts. Use `issue_type`, `affected_count`, `failed_count`, `recovered_count`, `related_document_ids`, and `review_note` to confirm miscoding, attachment failures, deletion recovery, privilege miscoding, stale coding, and source reconciliation.

## Materiality Filter

Most task environments include noisy or stale records. Include a category, source, or custodian only when it is corroborated by the prompt focus, current production logs, non-noise collection/destruction records, target custodian records, explicit QC events, task-local memo facts, or clearly relevant document markers.

Be skeptical of rows marked as noise, older reconciliation batches, unrelated privilege entries, duplicate alias artifacts, stale review-guide coding, or categories that appear only in generated-looking noise families. Do not aggregate every row that shares a category ID if a current record or QC event gives the operative count.

When a collection or QC event says it overrides tracker completeness, let that event control readiness even if a production log looks superficially complete.

## Issue Classification

Classify post-hold destruction or source loss when records show destruction, wipe, unavailable source, or missing material after the hold/subpoena. These usually drive critical severity, blocked status, forensic/recovery steps, declarations, and possible notice.

Classify pre-hold policy destruction separately from preservation failure. If the destruction predates the hold and follows a retention rule, it is generally a policy or completeness gap, not post-hold spoliation. If an archive, vendor portal, backup, or retained source exists, identify retrieval or validation actions.

Classify uncollected sources when a relevant source is `not collected`, `not noticed`, `pending`, `partial`, or has missing counts. Pair the source with the affected categories and custodian.

Classify hold-notice defects when the memo or collection records show a source, device, vendor, personal channel, or off-site custodian was omitted from the hold distribution.

Classify review miscoding when document summaries/tags or QC notes show responsive material coded non-responsive, stale, family-only, or outside an overly narrow review guide. Required actions often include coding correction, reprocess/QC, and supplemental production.

Classify privilege-log gaps when privileged material was withheld but not fully logged. The unlogged count is usually:

```text
withheld_privileged_count - privilege_logged_count
```

Classify overdesignation when business-only or broad counsel-communication sets were withheld as privileged, especially with zero production, `overdesignation_flag`, or QC notes.

Classify privilege waiver or clawback risk when privileged material was produced, coded non-privileged, or forwarded externally. Use the template's distinct waiver, clawback, privilege-review, or business-only production actions.

Classify processing failures from QC issue types and notes, especially password-protected, corrupt, missing attachment text, duplicate family suppression, or archive validation failures.

## Counts And IDs

Use API count fields rather than counting displayed marker documents when a QC event, production log, destruction event, or privilege row gives a total. `related_document_ids` may contain representative first/last markers while `affected_count` or `failed_count` carries the real count.

Use `missing_count` for source units missing from collection events, `quantity` for destroyed records, `record_count` for privilege rows, and production log counts for produced/withheld/logged totals. Use `0` only when the template calls for a numeric value and no count applies or no count is available.

Source event IDs should come from the relevant API records, commonly collection `event_id`, destruction `event_id`, QC `event_id`, production `log_id`, or privilege `item_id` depending on the template's wording. Keep exact ID spelling.

## Output Construction

1. Draft the JSON object in the exact top-level order required by the template.
2. Use only template-approved keys and enums. Do not include schema metadata, comments, markdown, or explanatory text.
3. Build stable issue, finding, source, and action IDs in the format requested by the template. Keep them deterministic and sorted.
4. Sort category IDs, custodian IDs, document IDs, action enums, issue lists, and rows exactly as instructed. Ranks must be consecutive integers starting at 1.
5. Set overall readiness, blocked status, disclosure/notice flags, and severity from the most serious material defect, not from noisy background rows.
6. Validate before finalizing:

```bash
jq . answer.json >/dev/null
```

If validation fails, fix JSON syntax first, then re-check enum spelling, missing required keys, integer counts, booleans, and sort order.

## Common Pitfalls

- Forgetting that list endpoints are wrapped in `{count, items}`.
- Treating search results as canonical instead of fetching endpoint records.
- Including categories that only have noisy, stale, or unrelated records.
- Double-counting current and noise production rows for the same category.
- Counting marker document IDs instead of QC or production totals.
- Mapping raw API status strings directly to output enums when the template requires different enum names.
- Missing local memo facts that rename an archive, explain hold distribution, or clarify whether a source should still exist.
- Treating every pre-hold loss as notice-worthy spoliation; distinguish policy destruction from post-hold preservation defects.
- Omitting privilege consequences when produced material is privileged-coded or when withheld material is not fully logged.
- Returning a memo or markdown when the prompt requires JSON only.
