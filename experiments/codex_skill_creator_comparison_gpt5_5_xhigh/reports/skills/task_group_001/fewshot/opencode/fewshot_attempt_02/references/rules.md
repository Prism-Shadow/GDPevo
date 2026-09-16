# HarborCRM Reusable Rules

These rules are inferred from the staged HarborCRM examples. Apply them procedurally to the current prompt, API data, and answer template. Do not copy values from examples; compute all IDs, names, dates, amounts, statuses, counts, and rankings from the current API responses.

## Shared Hygiene

- Email: trim whitespace and lowercase.
- Phone: keep digits only. A blank phone remains an empty string.
- Contactability: an email or a phone is sufficient unless the prompt/template requires both.
- Account matching: prefer explicit `account_id` or `crm_account_id`; otherwise match by normalized company name, clear abbreviation/canonical-name variants, or email/website domain. Do not update a CRM account whose status is disqualified or whose `disqualified_reason` is populated.
- Existing contact matching: prefer normalized email, then contact ID, then name within a matched account if the data supports it.
- Date offsets: when an event exposes `end_date` and follow-up day counts, due date equals `end_date + days`.
- Amounts: use integer USD from the source record requested by the prompt. Do not convert or format currency strings.

## Event Sponsor And Badge Handoff

### Sponsor status

Build sponsor status rows from active sponsor/order/package records for the requested event.

- Ignore canceled or otherwise inactive sponsor records as active sponsors.
- `confirmed` sponsor with a paid/deferred invoice status maps to `paid_deferred`.
- `confirmed` sponsor with an open invoice maps to `open_invoice`.
- `proposal_sent` sponsor with no paid invoice maps to `proposal_only`.
- If a schema includes `not_sponsor`, use it only for accounts the prompt asks to compare against sponsors but that have no active sponsor record.
- For open invoices, report package/order amount as the sponsor revenue amount and separately report open balance as `invoice.amount - invoice.paid_amount`.
- Finance follow-up targets are open-invoice and proposal-only sponsors. Count one task per target account unless the prompt gives another unit.

### Badge classification

Classify each badge for the requested event from badge type, sponsor records, CRM account status, and available contact facts.

- Sponsor attendees are contacts whose badge is sponsor-type or whose company/account is an active sponsor. Exclude them from non-sponsor lead lists.
- Qualified non-sponsor leads are business attendees from non-sponsor, non-disqualified accounts with usable contact information.
- Exclude non-business badges such as student, press, academic-only, media-only, or personal/non-company records.
- Exclude CRM accounts already disqualified. If both inactive sponsor and disqualified account could apply, prefer the more specific template reason when the prompt implies it.
- Use `missing_contact` when no usable email or phone is present.
- If the schema asks for badge-only contact facts, include importable badge contacts that do not already have a matching CRM contact. This can include sponsor attendees when the same schema asks to create sponsor contact or campaign-member work.

### CRM and campaign-member actions

- Account action is create when no non-disqualified CRM account matches; update when a matching account exists.
- Contact action is create when the account exists but no matching contact exists; update when the contact exists and changed fields are implied.
- Campaign-member create/update/no-action depends on current membership for the event/campaign:
  - create when no member exists and the badge/contact should be imported.
  - update when a member exists but target status should change.
  - no_action when an existing member already has the target status or the badge is an excluded sponsor attendee that needs no new work.
  - no_import for excluded records that should not enter CRM.
- Typical target statuses are `attended` for qualified non-sponsor badge scans, `attended_sponsor` for sponsor badge scans, `registered_sponsor` for sponsor contacts that registered but did not scan, and `excluded` only when the template requests excluded campaign rows.

### Event totals

- Lead pipeline totals use the event's lead opportunity amount multiplied by qualified non-sponsor accounts, unless the template asks for open opportunity records instead.
- Sponsor revenue totals sum active sponsor/order amounts by mapped sponsor status.
- Exclusion counts count badge-level decisions by exclusion reason.

## Trade-Show Prospecting

Fetch the show, exhibitors, meeting interest, CRM accounts, contacts, opportunities, and policies when available.

### Platform qualification

Qualify exhibitors that build, manufacture, OEM-build, or integrate target underwater platforms. Classify platforms in this enum order:

1. `AUV`
2. `ROV`
3. `Underwater Camera`

Use exhibitor descriptions and company context:

- AUV: AUV, autonomous underwater vehicle, autonomous scout/drone, underwater drone where the context is autonomous.
- ROV: ROV, remotely operated vehicle, inspection robot, pen-cleaning robot, tethered underwater robot.
- Underwater Camera: underwater camera, camera module, camera array, low-light inspection camera, camera-system OEM.

Exclude adjacent companies that do not build target platforms:

- distributor, reseller, dealer, sales agent only: `distributor_only`.
- consulting, services, operating rented platforms, analytics/dashboard/services without owned hardware: `service_only`.
- sensor-only or probe-only vendor: use `sensor_vendor_only` if allowed, otherwise `sensor_only`.
- research, university, lab-only, student program: `research_only`.
- outside the campaign target market: `not_target_market` when allowed.

### Priority, ranking, and opportunity

Always obey explicit prompt rules first. If the prompt does not define priority tiers but meeting-interest records exist, use this fallback:

- Tier `A`: requested demo and interest score at least 90.
- Tier `B`: requested demo and interest score at least 80.
- Tier `C`: all other qualified exhibitors.

When ranking is requested, sort by:

1. requested demo first,
2. interest score descending,
3. broader platform coverage descending,
4. company name ascending.

Assign rank as 1-based contiguous integers after sorting. Use prompt-provided opportunity sizing by tier; otherwise leave opportunity fields out unless the template requires them.

### Trade-show counts

- Qualified count is the number of qualified exhibitors included.
- Excluded count is the number of excluded exhibitors included.
- Platform counts count each qualified exhibitor once for each platform it covers.
- Existing CRM overlap count and IDs come from qualified exhibitors with `crm_account_id` or a matched non-disqualified CRM account.

## Import-Batch Cleanup

Fetch batch metadata, raw contacts, suppression records, CRM accounts, contacts, and policies.

### Removal sequence

1. Normalize each raw row's email and phone.
2. Remove rows with neither usable email nor usable phone as `missing_contact`.
3. Remove rows matching suppression by normalized email or phone as `suppressed`. Also treat an existing opted-out CRM contact as suppressed when the prompt expects suppression hygiene.
4. De-duplicate remaining rows by key:
   - Use `email:<normalized email>` when email exists.
   - Otherwise use `phone:<normalized phone>` when phone exists.
5. Choose one winning row per duplicate key.

### Duplicate winner selection

If the prompt does not specify a winner rule, choose the row with the best source and freshest data:

1. Source reliability, highest first: `partner_upload`, `sponsor_form`, `exhibitor_form`, `badge_scan`, `webinar_form`, `manual_upload`.
2. Later `captured_at`.
3. Higher or lexically later row ID for an exact tie.

List duplicate groups by duplicate key ascending and removed duplicate row IDs ascending.

### Clean contact rows

- Use the winning source row ID as both `clean_contact_id` and `source_row_id` when the template asks for that pattern.
- Preserve the winning row's company name, contact name, source name, and captured timestamp unless the template asks for canonical CRM names.
- Use normalized email and phone in clean outputs.
- Set existing account/contact IDs only when a non-disqualified CRM match is supported.
- Set `crm_action` to `update_existing` when a non-disqualified existing account matches, otherwise `create_account`. Use `suppress` or `no_import` only if the template includes removed rows in the clean list.

### Import counts

- `campaign_member_import_count` is the number of surviving clean contacts that should enter the batch campaign.
- `import_action_totals` should reconcile to the original raw rows when the template includes removed-row categories: created + updated + no_import + suppressed equals raw row count.
- Count duplicate removals and missing-contact removals as `no_import`; count suppressed rows as `suppress`.
- Removal summaries should count only rows actually removed for that reason.
