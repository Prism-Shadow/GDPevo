# HarborCRM Controlled Vocabulary Reference

Every value in an output must come from these enumerated sets. Do not coin new values.

## Sponsor statuses

| Value | Meaning |
|---|---|
| `paid_deferred` | Sponsor has paid in full or has a deferred payment arrangement with zero open balance. |
| `open_invoice` | Sponsor has at least one invoice with a non-zero open balance. |
| `proposal_only` | Sponsor has an order/package but no invoice has been issued. |
| `not_sponsor` | Account is not a sponsor for this event. |

## CRM actions — Account

| Value | Meaning |
|---|---|
| `create_account` | No matching CRM account exists; create one. |
| `update_existing` | A matching CRM account exists; update it. |
| `no_import` | Do not import this record (excluded or non-qualifying). |
| `suppress` | Suppress this record (suppression-list match). |

## CRM actions — Contact

| Value | Meaning |
|---|---|
| `create_contact` | No matching CRM contact exists; create one. |
| `update_existing` | A matching CRM contact exists; update it. |

## CRM actions — Campaign Member

| Value | Meaning |
|---|---|
| `add_campaign_member` | Add a new campaign-member record (used in event handoff contexts). |
| `create` | Create a new campaign-member record. |
| `update` | Update an existing campaign-member record. |
| `update_campaign_member` | Update an existing campaign-member record (alternate form). |
| `no_action` | No action needed (e.g., already correct). |
| `no_import` | Do not import or create a campaign-member record. |

## Combined CRM actions (badge-level shorthand)

| Value | Meaning |
|---|---|
| `create_account_contact_campaign_member` | Create account, contact, and campaign member all at once. |
| `create_contact_campaign_member` | Create contact and campaign member under an existing account. |

## Campaign-member target statuses

| Value | Meaning |
|---|---|
| `attended_sponsor` | Attended the event as sponsor personnel. |
| `registered_sponsor` | Registered but did not attend; sponsor personnel. |
| `attended` | Attended the event as a non-sponsor. |
| `excluded` | Excluded from the campaign. |

## Badge classifications

| Value | Meaning |
|---|---|
| `sponsor_attendee` | Badge belongs to a sponsor company. |
| `qualified_non_sponsor_lead` | Non-sponsor badge that qualifies as a sales lead. |
| `excluded` | Badge does not qualify (see exclusion reason). |

## Exclusion reasons

| Value | Context |
|---|---|
| `sponsor_attendee` | Event / badge |
| `existing_disqualified` | CRM account status |
| `inactive_sponsor_record` | Event sponsor |
| `non_business_badge` | Badge type |
| `missing_contact` | Badge / import row |
| `duplicate` | Import batch |
| `suppressed` | Import batch |
| `distributor_only` | Trade show |
| `service_only` | Trade show |
| `sensor_vendor_only` | Trade show |
| `sensor_only` | Trade show |
| `research_only` | Trade show |
| `not_target_market` | Trade show |

## Platform enums

| Value |
|---|
| `AUV` |
| `ROV` |
| `Underwater Camera` |

Always sort platforms in this order: AUV, ROV, Underwater Camera.

## Priority tiers

| Value |
|---|
| `A` |
| `B` |
| `C` |

## Contact source names

| Value | Meaning |
|---|---|
| `badge_scan` | Scanned at an event. |
| `sponsor_form` | Submitted via sponsor form. |
| `partner_upload` | Uploaded by a partner. |
| `webinar_form` | Registered for a webinar. |
| `exhibitor_form` | Submitted via exhibitor form. |
| `manual_upload` | Manually uploaded. |

## Trade-show relationship types

| Value | Meaning |
|---|---|
| `distributor` | Distributor, not a manufacturer. |
| `service_provider` | Service-only company, no hardware. |
| `sensor_vendor` | Sells sensors but does not build the target platforms. |
| `research` | Research institution, not a commercial prospect. |

## Removal reasons (import batch)

| Value | Meaning |
|---|---|
| `duplicate` | Removed due to duplicate key match. |
| `missing_contact` | Removed due to missing contact name. |
| `suppressed` | Removed due to suppression-list match. |
