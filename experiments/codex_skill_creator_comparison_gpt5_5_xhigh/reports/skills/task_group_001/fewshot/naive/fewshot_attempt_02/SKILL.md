---
name: harborcrm-handoff-solver
description: Solve HarborCRM CRM handoff, trade-show prospecting, and import-cleanup tasks by fetching the public API data, applying CRM qualification rules, and returning template-shaped JSON only.
---

# HarborCRM Handoff Solver

Use this skill when a task asks for a HarborCRM JSON handoff, reconciliation, prospecting summary, or CRM import cleanup using a runner-provided API base URL and an `input/payloads/answer_template.json` file.

## Required Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before fetching data.
2. Extract the task type, identifiers, required endpoints, allowed enum values, required keys, ordering rules, and any explicit campaign-specific formulas from the prompt and template.
3. Fetch only public business endpoints needed for the current identifiers. Prefer endpoints named in the prompt. If the prompt gives only a family of resources, inspect list/detail endpoints for the named `event_id`, `show_id`, or `batch_id`.
4. Build the result from current API data. Do not use remembered values from examples. Do not emit fields outside the template.
5. Validate every enum, date, integer count, currency total, null, empty string, and ordering rule against the template.
6. Return one JSON object only, with no prose outside the JSON.

Useful fetch pattern:

```bash
BASE="${TASK_ENV_BASE_URL%/}"
curl -sS "$BASE/api/policies"
curl -sS "$BASE/api/crm/accounts"
curl -sS "$BASE/api/crm/contacts"
curl -sS "$BASE/api/crm/opportunities"
curl -sS "$BASE/api/crm/campaign_members"
```

Then add the identifier-specific resources requested by the task, for example event resources, trade-show resources, or import-batch resources. Query-string filters are useful when available, but always tolerate APIs that return the full collection.

## Shared Normalization And Matching

Normalize before comparing or emitting:

- Email: trim whitespace and lowercase. Use `""` when no usable email is present.
- Phone: keep digits only. Use `""` when no usable phone is present.
- Names and company names: trim whitespace. Match accounts primarily by supplied `account_id` or `crm_account_id`, then exact normalized company name, then domain from email or website when the data supports it. Be conservative with aliases unless the API explicitly links the records.
- Existing account action: `update_existing` when a non-disqualified CRM account already exists; otherwise `create_account` for a qualified importable company.
- Existing contact action: update only when a matching non-opted-out CRM contact exists for the same account or normalized email; otherwise create when the row is importable and contactable.
- Suppression: a row/contact is suppressed when its normalized email or phone matches suppression data or an opted-out CRM contact.
- Disqualified CRM accounts are exclusions, not qualified leads, even if event or show activity looks promising.

Counts, totals, and summary lists must be computed from the classified records that belong in the answer, not copied from source collection lengths unless the template says so.

## Event Sponsor And Badge Tasks

For event reconciliation tasks, fetch the event detail, sponsor packages or orders, badges, finance invoices, CRM accounts, contacts, opportunities, campaign members, and policies if exposed.

Sponsor status rules:

- Use only active sponsor records for sponsor-status sections. Treat confirmed orders/packages as active. Exclude canceled or inactive sponsor records unless the template asks to report them separately.
- If an active sponsor has a finance invoice with paid/deferred status and no open balance, classify as `paid_deferred`.
- If an active confirmed sponsor has an open or partially paid invoice, classify as `open_invoice`; compute `open_balance` as invoice amount minus paid amount when the field is not directly supplied.
- If an active sponsor/order has no invoice and is only proposed, classify as `proposal_only`.
- Use `not_sponsor` only when the template explicitly allows a sponsor-status row for a non-sponsor.
- Sponsor revenue totals are integer USD sums over included sponsor-status rows. Open-invoice package revenue and open balance are separate when both are requested.

Badge and lead rules:

- Sponsor attendees are contacts whose company/account is an active sponsor or whose badge type is sponsor. They are excluded from non-sponsor lead lists but may still need sponsor campaign-member create/update actions when the template asks for badge-level handling.
- Non-business badges such as student, press, academic, personal, or otherwise non-commercial types are excluded with the template's controlled reason.
- Existing disqualified CRM accounts are excluded even if the badge is business-oriented.
- Missing-contact records are excluded when both normalized email and normalized phone are empty or the template defines contact data as insufficient.
- Qualified non-sponsor leads are business badges that are not sponsor attendees, not disqualified, and have usable contact/company data.
- Use the event's `lead_opportunity_amount` for each qualified non-sponsor account unless the prompt gives another formula.

Campaign-member actions:

- Join existing campaign members by event plus contact/account when CRM IDs exist.
- For an existing member already at the target status, use `no_action`.
- For an existing member at a different target status, use `update`.
- For an importable badge/contact without an existing member, use `create` or the template-specific create action.
- Use sponsor target statuses such as `attended_sponsor` or `registered_sponsor` for sponsor contacts; use `attended` for qualified non-sponsor badge attendees unless the prompt says otherwise; use `excluded` or `no_import` for excluded records when represented.
- For badge-only contacts, include normalized contact facts for importable badge contacts that are not already matched to an existing CRM contact, including sponsor badge contacts when the template's example of fields requires sponsor contact creation.

Dates and task counts:

- Compute follow-up due dates from the event `end_date` plus `followup_days_after_end` and `sponsor_followup_days_after_end` unless the prompt gives fixed dates.
- Lead task count usually equals the number of qualified non-sponsor lead accounts.
- Sponsor finance task count usually equals active sponsors needing finance follow-up, such as `open_invoice` and `proposal_only`.

## Trade-Show Prospecting Tasks

For trade-show prospecting tasks, fetch show detail, exhibitors, meeting interest, CRM accounts, contacts if needed, and policies.

Qualification:

- Qualify exhibitors that build, manufacture, OEM-build, or integrate target platforms covered by the campaign/policy.
- The recurring target platform enums are `AUV`, `ROV`, and `Underwater Camera` when the template allows them. Sort platforms in the enum order shown by the template.
- Exclude distributor-only, reseller-only, service-only, sensor-only/vendor-only, research-only, and not-target-market exhibitors using the controlled reason enum in the template.
- Use explicit relationship fields if present. Otherwise classify from exhibitor descriptions and policy notes.
- Existing CRM overlap comes from `crm_account_id` on the exhibitor when supplied, or conservative CRM account matching. Exclude disqualified CRM accounts unless the prompt says to keep them as near misses.

Interest, ranking, and sizing:

- Join meeting-interest rows by normalized company name or explicit company ID.
- Preserve requested enrichment fields from exhibitors, such as booth, country, website, requested demo, and score.
- When the prompt gives a ranking formula, apply it exactly. A common pattern is demo-requested first, then interest score descending, broader platform coverage, then company name ascending.
- Assign priority tiers and opportunity estimates from the prompt's thresholds. Do not infer amounts from previous tasks.
- Number ranks as 1-based contiguous integers after sorting.

Summaries:

- Qualified counts equal the number of qualified exhibitors/leads.
- Excluded counts equal the number of excluded near misses or excluded exhibitors included in the output.
- Platform coverage counts increment once per qualified company per platform.
- Priority counts include all allowed tiers from the template, using zero for absent tiers.
- Sort qualified or excluded lists by the template rule, often company name ascending unless a rank field controls ordering.

## Import Batch Cleanup Tasks

For import cleanup tasks, fetch batch detail, raw contacts, suppression entries, CRM accounts, CRM contacts, campaign members if needed, and policies.

Cleaning:

- Normalize email and phone first.
- A row is unusable with reason `missing_contact` when it lacks both usable normalized email and usable normalized phone, or when the template/prompt defines the contact as incomplete.
- A row is suppressed with reason `suppressed` when normalized email or phone matches suppression data or an opted-out CRM contact.
- Detect duplicates after normalization. Prefer duplicate keys in this order unless the prompt says otherwise: normalized email, normalized phone, then a conservative combination of normalized company plus normalized contact name.

Duplicate winner selection:

- Choose the row with the best source precedence when the task or data implies one. A common precedence is partner or curated uploads over generic forms.
- If source precedence does not decide, choose the most recent `captured_at`.
- If still tied, choose the lexicographically larger row ID only when examples show later replacement; otherwise choose the lower row ID and stay consistent.
- Record duplicate groups with `key`, `winner_row_id`, and sorted `removed_row_ids`. Count removed duplicate rows, not groups.

Import actions:

- Surviving, non-suppressed, contactable rows with an existing non-disqualified account use `update_existing`.
- Surviving rows without an existing account use `create_account`.
- Removed duplicates and missing-contact rows count as `no_import`.
- Suppressed rows count as `suppress`.
- Campaign-member import count equals surviving cleaned contacts that should become members of the batch campaign.
- Sort clean contacts, duplicate summaries, and removed rows exactly as the template requires.

## Final Validation Checklist

Before returning, verify:

- The top-level keys match the template exactly.
- Every required object key is present, including zeros, empty lists, `null`, or `""` where appropriate.
- No extra fields are present.
- All enums use the template's spelling.
- Currency and count values are integers.
- Dates are ISO `YYYY-MM-DD` when required.
- Lists are sorted by the stated rule.
- Summary counts and totals recompute from the emitted detail rows.
- The final response is valid JSON and contains no markdown or explanation.
