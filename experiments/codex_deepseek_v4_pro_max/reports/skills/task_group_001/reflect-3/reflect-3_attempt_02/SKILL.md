 # HarborCRM Event-to-CRM Handoff Skill

 ## Overview
 Reconcile event, trade-show, finance, and CRM data into import-ready handoff artifacts
 by fetching all relevant public HarborCRM API endpoints, normalizing inputs,
 resolving duplicates, matching against existing CRM records, and classifying
 records according to controlled vocabularies.

 ## Workflow Steps

 ### 1. Gather All Relevant Data
 Fetch every endpoint listed in the task prompt before beginning analysis.
 Build lookup maps indexed by key fields (account ID, account name, email domain,
 contact ID) to accelerate matching steps.

 ### 2. Normalize Inputs Before Comparison
 - **Email**: trim whitespace, lowercase the full address.
 - **Phone**: strip every non-digit character; preserve the country code.
 - **Company names**: trim whitespace; store in lowercase for matching.
 - **Dates**: parse ISO-8601 timestamps; compute follow-up due dates as
   `end_date + N days` using the event metadata (`followup_days_after_end`,
   `sponsor_followup_days_after_end`).

 ### 3. Sponsor Reconciliation
 - Match each non-canceled sponsor order to its finance invoice by `account_id`.
 - Classify status by invoice state:
   - `paid_deferred` – invoice exists and status is `paid_deferred`.
   - `open_invoice` – invoice exists and status is `open`.
   - `proposal_only` – no invoice exists for the order.
 - Compute `open_balance` for open invoices as `amount - paid_amount`.
 - Exclude canceled orders; flag associated contacts as `inactive_sponsor_record`.
 - Unpaid/unsettled sponsors (open_invoice + proposal_only) drive the finance
   follow-up list and total.

 ### 4. Badge and Contact Classification
 - Build a sponsor-contact set from both `ticket_contacts` on orders and any
   badge whose `badge_type` is `"sponsor"`.
 - For each badge, apply exclusions in priority order:
   1. Sponsor badge (type `"sponsor"`) → `sponsor_attendee`.
   2. Company name matches a canceled sponsor order → `inactive_sponsor_record`.
   3. Student / press badge type → `non_business_badge`.
   4. CRM account exists and is disqualified → `existing_disqualified`.
   5. Contact is a sponsor ticket contact → `sponsor_attendee`.
 - Surviving badges are `qualified_non_sponsor_lead`.

 ### 5. CRM Account and Contact Matching
 Match import/exhibitor/badge records against the CRM using a cascade:
 1. **Exact company-name match** (lowercased).
 2. **Email-domain match** – extract the domain from the contact email and
    look it up in CRM account domains.
 3. **Substring / fuzzy match** – if one name is a substring of the other,
    or significant words overlap.

 For contacts: first search within the matched account by lowercased contact
 name, then fall back to a global email lookup across all CRM contacts.

 Determine `crm_action`:
 - Account exists in CRM → `update_existing`.
 - Account not in CRM → `create_account`.
 - Contact suppressed (see §6) → `suppress`.

 ### 6. Duplicate Detection and Resolution
 - Group normalized records by normalized email (only among non-suppressed,
   non-unusable rows).
 - For each group with multiple records, select a single winner:
   1. Newest `captured_at` (descending).
   2. Source priority (highest first): `partner_upload`, `webinar_form`,
      `badge_scan`, `sponsor_form`, `exhibitor_form`, `manual_upload`.
   3. Lowest `row_id` (ascending).
 - Remove all other rows as duplicates; record the duplicate key (email),
   winner, and removed row IDs.

 ### 7. Suppression Handling
 - Check every raw contact against the suppression list by normalized email
   and normalized phone.
 - Suppressed contacts are counted in `import_action_totals.suppress` and
   listed in `removal_summary` with reason `"suppressed"`.
 - Unusable rows (no email AND no phone) are removed as `"missing_contact"`.

 ### 8. Trade-Show Prospecting
 - Classify exhibitor platform coverage using the controlled enum
   `["AUV", "ROV", "Underwater Camera"]`.
 - **Critical**: a company must BUILD, MANUFACTURE, or OEM-DESIGN the platform.
   Mere usage, resale, rental, or integration of third-party hardware does
   not qualify. Look for verbs like *builds*, *manufactures*, *designs*,
   *OEM*, *makes* in the exhibitor description.
 - Exclude non-qualifying exhibitors with controlled reasons:
   - `distributor_only` – reseller / distributor without own manufacturing.
   - `service_only` – consulting, analytics, or operating rented equipment.
   - `sensor_vendor_only` – sensor-only probe vendor, no platform.
   - `research_only` – academic / research entity.
 - Use CRM disqualification reasons when available.

 ### 9. Priority Tier and Opportunity Sizing
 For qualified leads at trade shows:
 - | Tier | Condition | Opportunity (USD) |
 - |------|-----------|--------------------|
 - | A | Demo requested AND interest score ≥ 90 | 120,000 |
 - | B | Demo requested AND interest score ≥ 80 | 90,000 |
 - | C | All other qualified leads | 50,000 |

 ### 10. Sort Order Conventions
 - **Sponsor statuses**: by `account_name` ascending.
 - **Qualified leads**: by `account_name` or `company_name` ascending unless
   a ranking rule is specified.
 - **Ranked leads**: demo-requested first, then interest score descending,
   then broader platform coverage (count of platforms descending), then
   company name ascending.
 - **Excluded records**: by `company_name` ascending, then `contact_name`
   ascending.
 - **Duplicate keys**: by `key` ascending.
 - **Removed rows**: by `row_id` ascending.
 - **Platform arrays**: always in enum order: `AUV`, `ROV`, `Underwater Camera`.

 ### 11. CRM Action Counting
 - Count actions implied by the handoff across accounts, contacts, and
   campaign members.
 - `campaign_members_create` = number of qualified leads being added as
   campaign members.
 - `campaign_members_update` = number of existing campaign members whose
   status requires a change (usually 0 for post-event reconciliation when
   existing statuses are already correct).
 - `campaign_member_import_count` = number of clean, importable contacts
   (create_account + update_existing rows).

 ### 12. JSON Output Rules
 - Return exactly one JSON object; no explanatory prose outside the JSON.
 - Use `null` (not the string `"null"`) for absent optional fields.
 - Use empty string `""` for missing email or phone values.
 - All monetary amounts in integer USD.
 - All dates in `YYYY-MM-DD` format.
 - All counts as integers.
 - Do not add fields beyond those declared in the answer template.
