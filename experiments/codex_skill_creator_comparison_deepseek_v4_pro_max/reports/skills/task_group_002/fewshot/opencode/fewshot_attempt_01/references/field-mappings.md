# API Field to Template Field Mappings

How MedBridge Sales Ops API fields map to the common output template shapes
across the three reconciliation workflows.

## Workflow 1: Quote Revision with Freight

### quote_summary / pricing section

| API source | API field | Template field(s) |
|---|---|---|
| Quote detail | `id` | `quote_id` |
| Quote detail | `customer_id` | `customer_id` |
| Quote detail | `quote_date` | `quote_date` |
| Quote detail | `primary_product_code` | `product_code` |
| Quote detail | `confirmed_quantity` | `confirmed_quantity` |
| Product detail (matched tier) | `unit_price_usd` | `unit_price_usd` or catalog_tier.`unit_price_usd` |
| Product detail (matched tier) | `lead_time_days` | `lead_time_days` or catalog_tier.`lead_time_days` |
| Product detail (matched tier) | `shelf_life_months` | `shelf_life_months` or catalog_tier.`shelf_life_months` |
| Computed | `confirmed_quantity * unit_price_usd` | `exw_total_usd` |
| Product detail (matched tier) | `min_qty`, `max_qty` | catalog_tier.`min_quantity`, catalog_tier.`max_quantity` |
| Customer detail | `payment_profile` | `payment_terms` |
| Quote detail | `incoterm` | `quote_basis` |

### Freight options

| API source | API field | Template field(s) |
|---|---|---|
| Freight quote | `id` | `freight_id` |
| Freight quote | `mode` (uppercase) | `mode` |
| Freight quote | `cost_usd` | `freight_cost_usd` |
| Freight quote | `transit_days_text` | `transit_days` |
| Freight quote | `valid_until` | `valid_until`, checked for staleness |
| Freight quote | `route_risk` (mapped) | `risk_level` |
| Freight quote | `risk_notes` (derived) | `risk_flag` |
| Computed | `exw_total_usd + cost_usd` | `grand_total_usd` |
| Freight quote | `valid_until` vs quote_date | `validity_status`, `source_is_stale` |
| Freight quote | `route_risk` (derived) | `customs_border_risk` |

### Policy flags

| API source | API field | Template field(s) |
|---|---|---|
| Computed (lowest-cost low-risk valid mode) | | `recommended_mode` |
| Policy `POL-FREIGHT-RECONFIRM` | | `freight_reconfirmation_required` = true |
| Computed (all freight valid_until >= quote_date) | | `all_freight_options_valid_on_quote_date` |
| Customer detail | `segment` | `customer_policy` (e.g. `RECURRING_NGO`) |

## Workflow 2: Indicative Module RFQ

### quote_header

| API source | API field | Template field(s) |
|---|---|---|
| RFQ detail | `id` | `rfq_id` |
| RFQ detail | `customer_id` | `customer_id` |
| RFQ detail | `quote_date` | `quote_date` |
| Fixed | `"USD"` | `currency` |
| Policy `POL-INDICATIVE-EXW` | | `quote_basis` = `"EXW_ONLY"` |

### Line items (one per requested module)

| API source | API field | Template field(s) |
|---|---|---|
| RFQ `requested_modules` | `product_code` | `product_code` |
| Product detail | `article_number` | `article_number` |
| RFQ `requested_modules` | `quantity` | `quantity` |
| Product detail (price tier) | `unit_price_usd` | `unit_price` |
| Product detail (price tier) | `lead_time_days` | `lead_time_days` |
| Product detail (price tier) | `shelf_life_months` | `shelf_life_months` |
| Computed | `quantity * unit_price` | `line_total` |

### quote_controls

| API source | API field | Template field(s) |
|---|---|---|
| Computed (sum of line totals) | | `grand_total` |
| Fixed | | `freight_excluded` = true |
| Customer + policy | `payment_profile` → policy | `payment_terms` |
| Policy `POL-QUOTE-VALIDITY` | | `offer_validity_days` = 30 |
| Derived (NGO medical modules) | | `who_documentation_required` = true |

## Workflow 3: Engagement Reconciliation

### account_status / engagement_reconciliation header

| API source | API field | Template field(s) |
|---|---|---|
| Opportunity detail | `id` | `opportunity_id` |
| Opportunity detail | `customer_id` | `customer_id` |
| Customer detail | `name` | `customer_name` |
| Opportunity detail | `stage` (map: `closed_won` → `WON`) | `stage` |
| Opportunity detail | `won_amount_usd` | `won_amount` (exact field name varies) |
| Opportunity detail | `outstanding_amount_usd` | `outstanding_balance` |
| Computed (sum phases) | | `phase_total_amount` |
| Computed (won == phase sum) | | `opportunity_matches_phase_total` |
| Computed (sum paid) | | `total_paid_amount` |
| Opportunity detail | `contact` | `primary_contact.contact_name` |
| Fixed from prompt or as_of_date | | `as_of_date` |

### Milestones array

| API source | API field | Template field(s) |
|---|---|---|
| Phase | `phase_id` (or derived MS1, MS2...) | `milestone_id` |
| Phase | `amount_usd` | `amount` |
| Invoice | `status` (mapped) | `invoice_state` or `payment_status` |
| Payments + invoice | paid vs total | `payment_state` |
| Payments | sum `amount_usd` | `paid_amount` or `amount_paid` |
| Computed | invoice amount - paid | `amount_unpaid` |
| Invoice | `due_date` | `due_date` |
| Revenue journal | existence check | `recognition_status` or `revenue_recognition_status` |

### Revenue recognition summary

| Source | Template field(s) |
|---|---|
| Computed (see reconciliation-patterns.md) | `recognition_status` |
| List of recognized phase_ids | `recognized_milestones` |
| List of paid-but-not-recognized phase_ids | `missing_required_milestones` |
| Sum of recognized amounts | `recognized_amount` |

### Event and voucher

| API source | API field | Template field(s) |
|---|---|---|
| Event detail | `id` | `event_id` |
| Event detail | `event_date` | `event_date` |
| Event detail | `voucher_code` | `voucher_code` |
| Voucher detail | `discount_percent` | `voucher_discount` or `discount_amount` |
| Voucher detail | `max_redemptions` | `voucher_max_uses` or `max_uses` |

### Follow-up tasks

Tasks are derived, not directly from any single API record. See the main
SKILL.md follow-up routing logic and reconciliation-patterns.md for the
decision tables.
