# HarborCRM Playbook

This playbook captures reusable rules for HarborCRM JSON reconciliation tasks. The prompt and `answer_template.json` always take precedence.

## Universal Rules

- Return exactly one JSON object, with no surrounding prose.
- Preserve template-required key order when practical; never add extra fields.
- Use integers for USD amounts and counts unless the template says otherwise.
- Use `null` only where the template allows null. Use an empty string only where the template expects a string but no value is supplied.
- Recount aggregate totals from the final included/excluded lists, not from intermediate candidates.
- Sort after final decisions are made.

## Normalization And Matching

- Email: trim whitespace and lowercase.
- Phone: remove all non-digits. Do not format with punctuation.
- Company/account name matching: prefer explicit IDs. If no ID exists, compare normalized company/account names, then website or email domain, then contact evidence.
- Contact matching: prefer normalized email, then normalized phone, then exact normalized name within the matched account.
- Existing disqualified CRM accounts are not qualified leads. If a template asks for exclusions, record them with the controlled disqualification reason that best matches the template.
- Existing opted-out or suppression-listed contacts should not be imported; classify them as suppressed or no-import according to the template.

## Event And Sponsor Reconciliation

Use event details for names, campaign codes, lead opportunity amounts, and due dates. Lead due date is normally `event.end_date + followup_days_after_end`; sponsor finance due date is normally `event.end_date + sponsor_followup_days_after_end`.

Sponsor status rules:

- `paid_deferred`: active sponsor/order/opportunity has a paid or closed-won finance state with no open balance.
- `open_invoice`: active sponsor has an invoice or finance record with unpaid balance.
- `proposal_only`: active sponsor commitment exists without an issued invoice or collected payment.
- `not_sponsor`: use only when the template explicitly asks for a sponsor-status record for a non-sponsor account.

Sponsor amounts should come from package/order/opportunity source amounts. For sponsor revenue totals, sum the committed package/order amount by status. Track open invoice balance separately when the template has a balance field.

Sponsor finance follow-up usually includes accounts with `open_invoice` or `proposal_only`; count one task per follow-up account unless the prompt says otherwise.

Badge and campaign-member handling:

- Sponsor attendees are not non-sponsor leads. If included in badge-level output, classify them as sponsor attendees and use the sponsor campaign status requested by the template.
- Qualified non-sponsor business badges become lead handoff records unless the matched CRM account is disqualified, contact information is unusable, or the badge is clearly non-business.
- Non-business badges include press, students, education/lab-only, personal/non-corporate, and other non-commercial attendees unless the prompt targets them.
- Missing-contact means the row lacks usable contact facts required by the template, commonly both normalized email and phone.
- Campaign member action is `create` or `add_campaign_member` when no existing member exists, `update` when an existing member needs a new target status, and `no_action` when the existing member already has the target status.
- For badge-only subject keys, use the template's requested convention when present; otherwise prefer a stable `badge:<badge_id>` key.

CRM action counts should be derived from final importable work:

- Account create/update counts come from qualified leads that need account creation or existing account updates.
- Contact create/update counts come from qualified leads or sponsor badge contacts that need contact work.
- Campaign member create/update counts come from the final campaign-member actions.

## Tradeshow Prospecting

Join tradeshow exhibitors with meeting-interest rows by company name or ID. Use CRM account IDs on exhibitors first, then fall back to account name/domain matching.

Qualified exhibitors are platform makers or OEM builders in the target market named by the prompt. Use the prompt's policy language first; otherwise infer from descriptions:

- `AUV`: autonomous underwater vehicles, autonomous subsurface drones, AUV scouts.
- `ROV`: remotely operated vehicles, inspection or cleaning ROVs.
- `Underwater Camera`: underwater camera modules, camera arrays, low-light inspection cameras.

Sort platform arrays in enum order: `AUV`, `ROV`, `Underwater Camera`.

Common exclusions:

- Distributor, dealer, reseller, supply-only: `distributor_only`.
- Consulting, services, operators, dashboard-only, analytics-only without hardware manufacturing: `service_only`.
- Sensor-only vendor without platform manufacturing: `sensor_vendor_only` or `sensor_only`, matching the template enum.
- University/lab/research-only: `research_only`.
- Outside the campaign market: `not_target_market`.

Priority tiers depend on the prompt. When the prompt does not define thresholds, a useful default from the examples is:

- `A`: requested demo and interest score at least 90.
- `B`: requested demo and interest score at least 80.
- `C`: all other qualified leads.

When ranking is requested, apply the prompt's order exactly. A common ranking is demo-requested first, then interest score descending, then broader platform coverage, then company name ascending. Use 1-based contiguous ranks.

Opportunity estimates come from prompt-provided tier values or event/show lead opportunity values. Totals are sums over final qualified leads only. Platform coverage counts count each platform occurrence, so a company with two platforms contributes to both platform counts.

## Import Batch Cleanup

Build cleaned contacts from raw rows after normalization, suppression, and duplicate resolution.

Removal order for reasoning:

1. Normalize email and phone for every raw row.
2. Mark rows suppressed when normalized email or phone matches suppression data or an opted-out CRM contact, if the template treats opt-outs as suppression.
3. Mark rows with no usable contact channel as missing contact.
4. Group remaining importable candidates by duplicate key: `email:<normalized email>` when email exists, otherwise `phone:<normalized phone>`.
5. Choose one winner per duplicate group. Prefer policy-provided source precedence when available. If absent, prefer more complete contact facts, then trusted partner/exhibitor/sponsor sources over generic/webinar/manual sources, then newest capture timestamp, then lexicographically greatest row ID.

Duplicate summaries should list each duplicate key, the winning row ID, and removed row IDs. Removal summaries should include duplicate, suppressed, and unusable rows with template-controlled reasons, sorted as requested.

Clean contact rules:

- Use the winning source row ID as the clean contact ID when the template asks for that convention.
- Preserve the winning row's company and contact display names.
- Store normalized email and normalized phone.
- `update_existing` when a non-disqualified CRM account matches; `create_account` when no account matches; use `no_import` or `suppress` only for removed/non-imported rows when the template includes those action totals.
- Existing contact ID is filled only when the surviving row matches a CRM contact by email, phone, or strong account/name evidence.

Import action totals usually count:

- `create_account` and `update_existing`: surviving clean contacts.
- `suppress`: rows removed due to suppression or opt-out.
- `no_import`: rows removed for duplicates, missing contact, or other non-suppression no-import reasons.

Campaign-member import count is the number of surviving clean contacts that should be added to the batch campaign.

## Final Cross-Checks

- Every list count in a summary equals the actual list length or per-item count.
- Every amount total equals the sum of the source values used in the final list.
- Every due date is date arithmetic from source dates, not the current date.
- Every output enum is one of the template's allowed values.
- Every list is sorted by the template's exact rule.
- The response is valid JSON and nothing else.
