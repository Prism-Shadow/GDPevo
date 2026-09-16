---
name: harborcrm-reconciliation
description: Solve HarborCRM API-backed CRM handoff, trade-show prospecting, and import-batch cleanup tasks that require exact JSON output from an answer template.
---

Use this skill when a task asks for a HarborCRM JSON handoff or prospecting summary using a runner-provided API base URL and an `input/payloads/answer_template.json` file.

## Core Procedure

1. Read the prompt and answer template before fetching data. Treat the template as the output contract: required top-level keys, nested keys, enum values, null-vs-empty-string expectations, ordering rules, and integer/date precision all come from the template.
2. Determine the API base URL supplied by the runner. Query only public business endpoints described by the prompt or exposed by the task environment.
3. Fetch every relevant collection before deciding. For event tasks this usually means event details, sponsor orders or sponsor packages, badges, finance invoices, CRM accounts, CRM contacts, opportunities, campaign members, and policies. For trade-show tasks this usually means show details, exhibitors, meeting-interest records, CRM accounts, CRM contacts, and policies. For import-batch tasks this usually means batch metadata, raw contacts, suppression records, CRM accounts, CRM contacts, and policies.
4. Join records deterministically. Prefer stable IDs when present; otherwise match companies by normalized company name and contacts by normalized email, then normalized phone, then exact contact name within the matched account.
5. Build the JSON from facts already fetched. Do not add explanatory prose, template metadata, comments, or undeclared fields.
6. Validate the completed object against the template shape, enum values, counts, totals, sorting rules, and JSON syntax before returning it.

Useful shell pattern:

```bash
BASE="${TASK_ENV_BASE_URL%/}"
curl -sS "$BASE/api/..."
```

If no `TASK_ENV_BASE_URL` environment variable exists, use the base URL text supplied by the runner or prompt.

## Normalization Rules

- Emails: trim surrounding whitespace and lowercase. Use `""` when the output field requires a string and no email is supplied; use `null` only when the template says the field is nullable.
- Phones: keep digits only. Preserve a leading country code when it is present in the source. Use `""` for missing phone strings unless the template says otherwise.
- Company names: trim whitespace for display. For matching, compare case-insensitively and also use CRM account IDs or exhibitor `crm_account_id` fields when available.
- Dates: compute follow-up due dates by adding the event's configured day offsets to `end_date`; output `YYYY-MM-DD`.
- Currency and counts: output integer USD and integer counts. Totals must be recomputed from the included records, not copied from source summary text.
- Platform lists: use only platform enums allowed by the template or policy and sort them in the enum order shown in the template.

## Event Sponsor And Badge Handoffs

Fetch the event, sponsor orders/packages, badges, invoices, CRM accounts, contacts, opportunities, campaign members, and policies.

Sponsor status rules:

- Ignore canceled or inactive sponsor orders when reporting active sponsor statuses.
- `paid_deferred`: active sponsor with an invoice whose status is paid/deferred or whose paid amount covers the package.
- `open_invoice`: active confirmed sponsor with an open invoice or unpaid balance.
- `proposal_only`: active proposal-stage sponsor with no invoice or no confirmed payment.
- `not_sponsor`: use only when the template explicitly asks for non-sponsor account status rows.
- Package amount comes from the sponsor order/package. For open invoices, `open_balance = invoice amount - paid_amount`; otherwise open balance is zero unless the template asks for unpaid totals.
- Sponsor finance follow-up targets are unpaid/open-invoice and proposal-only sponsors. Sort account names ascending when the template asks for a list.

Badge and lead qualification rules:

- Sponsor contacts and attendees are not qualified non-sponsor leads. Classify them as sponsor attendees when their company/account is an active sponsor or their badge type is sponsor.
- Exclude non-business badge types such as student, press, media, academic, or community-only attendees when the prompt asks for business leads.
- Exclude CRM accounts whose status is disqualified or whose `disqualified_reason` is non-null.
- Exclude records without usable contactability when the template has a missing-contact exclusion. A usable contact normally has at least one normalized email or phone.
- Qualified non-sponsor leads are business badges that are not active sponsors, not disqualified, and contactable.
- Use the event's configured `lead_opportunity_amount` for each qualified non-sponsor account unless the prompt gives a different sizing rule.

CRM action rules:

- Account action is `update_existing` when a CRM account match exists, otherwise create the account action named by the template.
- Contact action is update when a matching contact exists, otherwise create the contact action named by the template.
- Campaign-member action is create/add when no matching campaign member exists, update when one exists with a wrong status, and no-action when one already has the target status.
- Sponsor target campaign status is usually `attended_sponsor` when the sponsor badge was scanned and `registered_sponsor` for registered sponsor contacts without an attended badge. Qualified non-sponsor badge scans target `attended`. Excluded records target `excluded` only when the template asks for explicit campaign-member handling.
- Count CRM actions from the records implied by the handoff, using the exact action buckets declared by the template.

Event output checks:

- Sort sponsor statuses by account name unless another ordering is declared.
- Sort badge decisions by badge ID when requested.
- Sort campaign-member action rows by the declared subject key.
- Sort excluded records by the template rule, commonly company name then contact name.
- Lead task count normally equals the number of qualified lead accounts or badge leads that require handoff tasks.
- Sponsor finance task count normally equals the number of unpaid/open/proposal sponsor accounts requiring finance follow-up.

## Trade-Show Prospecting

Fetch show metadata, exhibitors, meeting-interest records, CRM accounts, contacts when relevant, and policies.

Qualification:

- Qualify exhibitors that manufacture, OEM-build, or embed covered target platforms described by the prompt or policy.
- Covered platform enums commonly include `AUV`, `ROV`, and `Underwater Camera`; emit only enums allowed by the template.
- Infer platforms from exhibitor descriptions and policy context. For example, autonomous underwater vehicle language maps to `AUV`, remotely operated vehicle language maps to `ROV`, and camera module/camera-system manufacturing maps to `Underwater Camera`.
- Exclude adjacent-only exhibitors using the template's controlled reasons: distributor/reseller only, service/consulting/operator only, sensor-vendor only, research-only, or not-target-market. Keep excluded exhibitors visible only when the template asks for an exclusion list.

Enrichment and ranking:

- Join meeting interest by company name unless a stable ID is provided. Preserve requested fields such as `requested_demo`, `interest_score`, booth, country, website, and CRM account ID.
- Mark CRM action as update when `crm_account_id` or another CRM match exists; otherwise create. Excluded exhibitors use no-import when declared by the template.
- If the prompt gives a priority or opportunity formula, use it exactly. If no formula is given, use the task's policy and meeting-interest signals; a common default is demo-requested with score at least 90 as tier A, demo-requested with score at least 80 as tier B, and remaining qualified leads as tier C.
- If ranked output is required, rank by the prompt's ordering criteria. When broader platform coverage is a tiebreaker, compare the number of covered platform enums after applying enum-order sorting. Assign contiguous 1-based ranks after sorting.

Trade-show output checks:

- Sort qualified exhibitors alphabetically when the template says so; otherwise sort by rank.
- Sort excluded exhibitors alphabetically by company name unless another rule is declared.
- Platform coverage counts count each qualified exhibitor once per platform enum included in its platform list.
- Existing CRM overlap counts include only qualified records with a CRM account match, and account ID lists should use the template's declared ordering.
- Total opportunity is the sum of included qualified lead opportunity estimates.

## Import-Batch Cleanup

Fetch batch metadata, raw contacts, suppression records, CRM accounts, CRM contacts, and policies.

Processing order:

1. Normalize email and phone for every raw row.
2. Mark rows with neither normalized email nor normalized phone as missing-contact/unusable.
3. Mark rows as suppressed when normalized email or phone matches a suppression record or an existing opted-out CRM contact.
4. Deduplicate remaining contactable, unsuppressed rows. Use `email:<normalized_email>` as the duplicate key when email exists; otherwise use `phone:<normalized_phone>`.
5. Pick one winning row per duplicate key. Use task policy if provided; otherwise prefer the most reliable source, then latest `captured_at`, then lexicographically greatest row ID. A practical source preference is partner or sponsor uploads before exhibitor forms, badge scans, webinar forms, and manual uploads.
6. Keep only winning, non-suppressed, usable rows in `clean_contacts`.

Import actions:

- Clean rows whose company matches an existing non-disqualified CRM account are update-existing actions; new companies are create-account actions.
- Duplicate and missing-contact removals count as no-import when the template has a no-import bucket.
- Suppressed rows count as suppress actions.
- Campaign-member import count is the number of surviving clean contacts that should be imported into the batch campaign.

Import output checks:

- Use the winning source row ID as the clean contact ID when the template calls for that.
- Sort clean contacts, duplicate keys, and removed rows exactly as declared.
- Duplicate removed count is the number of non-winning duplicate rows.
- Suppressed removed count is the number of rows removed by suppression.
- Unusable removed count is the number of rows removed for missing usable contact data.
- Removed rows should include every removed row with a controlled reason and no extra fields.

## Final Validation Checklist

- The response is one valid JSON object and nothing else.
- Every required key from the template is present; no undeclared keys are present.
- All enum strings exactly match the template.
- Nulls and empty strings follow the template field types.
- Lists are sorted by the declared rules.
- Counts equal the actual number of included or removed records they summarize.
- Currency totals equal the sum of the relevant integer amounts.
- Dates were derived from source dates and offsets, not guessed.
- No task-specific training answer values or unrelated source records are included.
