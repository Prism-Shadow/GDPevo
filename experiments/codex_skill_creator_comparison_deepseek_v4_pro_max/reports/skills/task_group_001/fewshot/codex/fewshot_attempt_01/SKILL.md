---
name: harbor-crm
description: HarborCRM event, trade-show, finance, import-batch, and CRM API integration. Use when Codex needs to reconcile post-event sponsor finances, qualify trade-show exhibitors for prospecting campaigns, clean and import contact batches, prepare CRM handoffs from badge scans, or cross-reference CRM accounts/contacts/opportunities/campaign-members with event and trade-show records. Covers controlled status/reason enums, contact normalization, deduplication, suppression, CRM-action classification, follow-up date calculation, and platform-coverage qualification for marine/aquaculture robotics prospecting.
---

# HarborCRM Integration

## Overview

HarborCRM exposes a unified REST API for event management, trade-show prospecting, finance reconciliation, import-batch processing, and Salesforce-style CRM records. The API base URL is always supplied by the runner. All endpoints are public GETs; no authentication is required.

## Core Workflow

1. Read the task prompt for the target identifiers (event_id, show_id, batch_id) and the answer template.
2. Fetch all relevant endpoints in parallel. The answer template and the prompt list which endpoints to use.
3. Reconcile data across endpoints using the processing rules in this skill.
4. Produce a single JSON object conforming to the answer template.

### Recurring task patterns

| Pattern | Key Endpoints | Typical Output |
|---|---|---|
| Post-event sponsor+lead handoff | `/api/events/{id}` plus sub-resources (`/orders`, `/badges`, `/sponsor_packages`), `/api/finance/invoices`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members`, `/api/policies` | Sponsor statuses, qualified leads, exclusion lists, CRM action counts, follow-up dates |
| Trade-show prospecting | `/api/tradeshows/{id}`, `/tradeshows/{id}/exhibitors`, `/tradeshows/{id}/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies` | Ranked qualified exhibitors, exclusion list, platform/priority counts |
| Import batch cleaning | `/api/import_batches/{id}`, `/{id}/raw_contacts`, `/{id}/suppression`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies` | Clean contacts, duplicates removed, suppression removed, action totals |
| Post-event badge reconciliation | `/api/events/{id}` plus sub-resources, `/api/finance/invoices`, all CRM endpoints, `/api/policies` | Sponsor statuses, badge decisions, campaign-member actions, opportunity summary, exclusion counts |
| CRM-ready prospecting summary | `/api/tradeshows/{id}`, sub-resources, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies` | Ranked leads with tiers/opportunities, exclusion list, summary counts |

### Endpoint reference

See [references/api_reference.md](references/api_reference.md) for complete field-level documentation of every endpoint and response shape.

### Processing rules

See [references/processing_patterns.md](references/processing_patterns.md) for reusable rules covering:

- Contact normalization (email, phone)
- Sponsor status classification from orders + invoices
- CRM action determination (create_account vs update_existing vs no_import vs suppress)
- Duplicate resolution (email-based key, winner-row selection)
- Suppression checking
- Exclusion logic with controlled reason enums
- Follow-up due date calculation
- Priority tier assignment for prospecting
- Platform coverage classification from exhibitor descriptions
- Sorting conventions

## Scripts

### `scripts/normalize_contact.py`

Deterministic contact normalization for email and phone. Run it to normalize individual contacts:

```bash
python3 scripts/normalize_contact.py --email " jane.doe@example.com " --phone "(415) 555-0188"
# {"email": "dana.ruiz@helioware.example", "phone": "14155550188"}
```

The script returns one JSON line per call. It is useful for batch normalization when processing many contacts in a loop, or as a reference implementation when inlining the logic.

## Controlled enums

All enums must be used exactly as listed. Do not invent new values.

| Domain | Enum field | Allowed values |
|---|---|---|
| Sponsor status | `status` | `paid_deferred`, `open_invoice`, `proposal_only` |
| Sponsor status (broad) | `sponsor_status` | `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor` |
| Badge classification | `classification` | `sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded` |
| CRM action (import) | `crm_action` | `create_account`, `update_existing`, `no_import`, `suppress` |
| CRM action (extended) | `crm_action` | also `create_contact`, `add_campaign_member`, `create_account_contact_campaign_member`, `create_contact_campaign_member`, `update_campaign_member`, `no_action` |
| Campaign member status | `status` / `target_status` | `attended_sponsor`, `registered_sponsor`, `attended`, `excluded` |
| Campaign member action | `action` | `create`, `update`, `no_action`, `no_import` |
| Contact source | `source_name` | `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload` |
| Badge type (non-business) | `badge_type` | `student`, `press` |
| Platform | `platform` | `AUV`, `ROV`, `Underwater Camera` |
| Exclusion reason (event) | `reason` | `sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`, `missing_contact` |
| Exclusion reason (trade show) | `exclusion_reason` | `distributor_only`, `service_only`, `sensor_vendor_only`, `research_only`, `not_target_market` |
| Relationship type | `relationship_type` | `distributor`, `service_provider`, `sensor_vendor`, `research` |
| Priority tier | `priority_tier` | `A`, `B`, `C` |
| Suppression reason | `reason` | `global_opt_out`, `privacy_request`, `role_account` |
| Duplicate key format | | `email:{normalized_email}` |
| Removal reason | `reason` | `duplicate`, `missing_contact`, `suppressed` |
| Order status | `order_status` | `confirmed`, `proposal_sent`, `canceled` |
| Invoice status | `status` | `paid_deferred`, `open` |
| CRM account status | `status` | `customer`, `prospect`, `disqualified` |
| Opportunity stage | `stage` | `closed_won`, `proposal`, `qualification`, `discovery` |
