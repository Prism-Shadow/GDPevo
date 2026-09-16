---
name: medbridge-sales-ops
description: Integrate with the MedBridge Sales Ops REST API to verify quotes, RFQs, accounts, freight, policies, revenue journals, and events, then produce strictly-validated JSON decision packages. Use this skill whenever the user mentions MedBridge, MedBridge Sales Ops, Health Horizon Aid, NovaAid, GreenHarvest Labs, Helios Health Alliance, Meridian Public Health, a quote revision, an RFQ, an account reconciliation, freight options, revenue recognition, or any task that references a shared MedBridge API at a task environment base URL. The skill handles fetching and cross-referencing customer, product, quote, RFQ, freight, policy, invoice, payment, revenue-journal, event, and voucher records and assembling the correct JSON output structure from a supplied template.
---

# MedBridge Sales Ops API

You are solving a MedBridge Sales Ops integration task. The user provides a prompt, a base URL for the shared MedBridge Sales Ops REST API, and an answer template JSON file. Your job is to call the API, cross-reference the returned records, apply the correct business rules, and return strictly-valid JSON that exactly matches the template.

## API

The API base URL is provided in the prompt as a variable — look for `<TASK_ENV_BASE_URL>`, `${BASE_URL}`, or `${TASK_ENV_BASE_URL}`. All endpoints are read-only GET calls.

### Endpoints

| Endpoint | Key fields returned |
|---|---|
| `GET /api/customers` | Customer list: `customer_id`, `name` |
| `GET /api/customers/{id}` | Full customer: `customer_id`, `name`, `type`, `category`, `payment_terms_policy`, `preferred_freight_mode` |
| `GET /api/products` | Product list: `code`, `description`, `article_number`, `tiers` |
| `GET /api/products/{code}` | Single product with `tiers` array: `min_quantity`, `max_quantity`, `unit_price`, `lead_time_days`, `shelf_life_months` |
| `GET /api/quotes` | Quote list |
| `GET /api/quotes/{id}` | Full quote: `quote_id`, `customer_id`, `quote_date`, `product_code`, `quantity`, `basis`, `status` |
| `GET /api/rfqs` | RFQ list |
| `GET /api/rfqs/{id}` | Full RFQ: `rfq_id`, `customer_id`, `date`, `items` (array of `product_code`, `quantity`), `basis` |
| `GET /api/freight-quotes` | Freight quote list |
| `GET /api/freight-quotes/{id}` | Full freight: `freight_id`, `mode`, `cost`, `transit_days`, `valid_until`, `risk_level`, `risk_flag` or `customs_border_risk`, `product_code` |
| `GET /api/policies` | Policy list |
| `GET /api/policies/{id}` | Full policy: `customer_type`, `quote_basis`, `payment_terms`, `freight_reconfirmation_required`, `recommended_freight_mode`, `offer_validity_days`, `who_documentation_required` |
| `GET /api/opportunities` | Opportunity list |
| `GET /api/opportunities/{id}` | Full opportunity: `opportunity_id`, `customer_id`, `stage`, `amount`, `milestones` (array of `milestone_id`, `amount`, `phase_number`) |
| `GET /api/invoices` | Invoice list |
| `GET /api/invoices/{id}` | Full invoice: `invoice_id`, `customer_id`, `opportunity_id`, `milestone_id`, `phase_number`, `total`, `status` (OPEN/PAID/VOID), `due_date` |
| `GET /api/payments` | Payment list |
| `GET /api/payments/{id}` | Full payment: `payment_id`, `invoice_id`, `amount` |
| `GET /api/revenue-journals` | Revenue journal list |
| `GET /api/revenue-journals/{id}` | Full journal: `journal_id`, `milestone_id`, `invoice_id`, `amount`, `debit_account`, `credit_account` |
| `GET /api/events` | Event list |
| `GET /api/events/{id}` | Full event: `event_id`, `customer_id`, `opportunity_id`, `date`, `status`, `voucher_code` |
| `GET /api/vouchers/{code}` | Voucher: `code`, `status`, `discount`, `max_uses` |

If a list endpoint returns summary records without enough detail, make the individual GET calls for each record you need.

## General Rules

**JSON output only.** The prompt will always say to return only JSON matching the provided template. Read the template carefully — it defines every field name, enum value, type, and structure. Do not add extra keys, do not omit keys, do not wrap the output in markdown fences or explanatory text. The output must be a single JSON object.

**Dates.** All dates are ISO `YYYY-MM-DD`. Quote dates and business dates are given in the prompt; the current business date may be called `as_of_date` or `quote_date`.

**Money.** All money fields are numbers with two decimal places (e.g., `42480.00`). Compute totals as quantity × unit_price. Compute grand totals as EXW total + freight cost.

**IDs.** Use the exact IDs returned by the API — do not guess or fabricate them.

**Null vs. 0 vs. empty.** When the template shows `null` as a value, use JSON `null`, not `0` or `""`. Follow the template literally.

## Workflow Pattern

Every MedBridge task follows this sequence:

1. Read the template JSON to understand the exact output structure and controlled vocabularies (enums).
2. Identify the primary record IDs from the prompt (quote ID, RFQ ID, opportunity ID, customer ID).
3. Fetch the primary record from its endpoint, then fan out to secondary records (customer, product, freight, policies, invoices, payments, journals, events, vouchers).
4. Cross-reference: match records by shared IDs (`customer_id`, `product_code`, `milestone_id`, `invoice_id`, `opportunity_id`).
5. Apply business rules (below) to compute status fields, flags, and recommendations.
6. Fill every field in the template with the computed or fetched values.
7. Return the completed JSON.

When cross-referencing freight quotes, match by `product_code` — the freight record's `product_code` should match the product code from the quote or RFQ.

When cross-referencing invoices and payments, first fetch invoices linked to the opportunity (`opportunity_id`), then for each invoice fetch payments matched by `invoice_id`.

When cross-referencing revenue journals, fetch journals whose `milestone_id` or `invoice_id` matches the paid invoices.

## Business Rules

### Product Tier Selection

Products have tiered pricing. Given a confirmed quantity, select the tier whose `min_quantity <= quantity <= max_quantity`. Use the `unit_price`, `lead_time_days`, and `shelf_life_months` from that tier. If the quantity falls outside all tiers, use the closest tier and note it if the template has a warnings field.

### Freight Validity

A freight quote is valid when its `valid_until` date is on or after the quote date. When `valid_until` is before the quote date, the freight quote is stale. Report `validity_status` as `"VALID"` or `"STALE"`, and `source_is_stale` as `true` when stale.

### Freight Risk Interpretation

A `risk_level` of `"HIGH"` or `"MEDIUM"` with a risk flag other than `"NONE"` should be surfaced in any warnings. Risk flags like `"MEDIUM_BORDER_RISK"` mean the route has border/customs complications. Treat `risk_flag` and `customs_border_risk` as the same concept — the API may use either field name.

### Recommended Mode

Combine the policy's `recommended_freight_mode` with freight validity and risk assessment. Recommend the policy-preferred mode unless that mode's freight quote is stale or has a high risk. When the preferred mode is compromised, recommend the lowest-risk valid alternative. If all modes are stale or high-risk, flag `freight_reconfirmation_required` as `true`.

Alternatively, the policy field `freight_reconfirmation_required` may already be set — copy it directly if the template asks for it.

### Payment Terms

Get the payment terms from the **quoted customer's policy**, not from a generic default. Look up the customer, find their `type` or `category`, then match it to the policy record with the same `customer_type`. Take `payment_terms` from that policy.

For an RFQ with a new account, use `"PREPAY_100"` unless the policy record for the customer type says otherwise.

### Offer Validity

For RFQ tasks, `offer_validity_days` comes from the policy (`offer_validity_days` field). Default to 30 if the policy is silent.

### Revenue Recognition

For account reconciliation tasks, revenue recognition checks whether every **paid** milestone has a matching revenue journal entry:

- A milestone is **PAID** when all its invoices are paid (sum of payments equals invoice totals) and the invoice status is `"PAID"` or `"OPEN"` with full payment coverage.
- For each paid milestone, look for a revenue journal with a matching `milestone_id` and `amount` matching the paid amount. If found, status is `"RECOGNIZED"`. If not found, status is `"MISSING_REVENUE_JOURNAL"`.
- An **unpaid** milestone with open invoices and no payments gets `"NOT_REQUIRED_UNPAID"` — revenue is only recognized when cash is received.
- The overall `recognition_status` is `"COMPLETE_FOR_PAID_MILESTONES"` when every paid milestone is recognized, or `"MISSING_FOR_PAID_MILESTONES"` when at least one paid milestone lacks a journal.

### Milestone Reconciliation

Verify that the sum of the opportunity's milestone amounts equals the `won_amount`. Report `opportunity_matches_milestones` or `opportunity_matches_phase_total` accordingly.

For each milestone, compute:
- `invoice_state`: from the invoice's `status` field
- `payment_state`: `"PAID"` when paid amount equals invoice total, `"PARTIAL"` when paid > 0 but less than total, `"UNPAID"` when paid is 0
- `paid_amount`: sum of payments for that milestone's invoices
- `amount_unpaid` or `outstanding_balance`: invoice total minus paid amount
- `due_date`: from the invoice, or `null` when fully paid

### Follow-Up Tasks

For account reconciliations, generate two types of follow-up:

**Collection task:** For each unpaid invoice or unpaid milestone, create a collection task. The `due_date` is the invoice's `due_date`. The `next_action` is `"COLLECT_UNPAID_MILESTONE"` or `"SEND_COLLECTION_NOTICE"` depending on the template vocabulary. The `owner_queue` is `"ACCOUNT_MANAGEMENT"` unless the template specifies otherwise.

**Event invitation task:** When an event is linked (status `"SCHEDULED"`), create an invitation task for the account contact. Use `"SEND_EVENT_INVITATION"` or `"SEND_BRIEFING_INVITE"` per the template vocabulary. Set the invite due date to roughly 3 weeks before the event date, or 2026-07-01 if the event is late July 2026. Attach the voucher code.

### Accounting Action

When a paid milestone has a missing revenue journal, generate an accounting action:
- `action`: `"RECORD_REVENUE_MS2"` (or whichever milestone it is)
- `debit_account`: `"DEFERRED_REVENUE"`
- `credit_account`: `"IMPLEMENTATION_SERVICES_REVENUE"`
- `owner_queue`: `"ACCOUNTING"`

When all paid milestones are recognized, use `"VERIFY_REVENUE_ONLY"` if the template provides that option.

### Warning Messages

When freight has stale or risky entries, produce a concise English warning string. Example pattern: `"Freight rates require reconfirmation at final order. FR-LD-ROAD expired on 2026-05-25 and has high customs or border risk, so it should not be used without a fresh quote."` — adjust the freight ID, date, and risk description to match the actual records.

### WHO Documentation

When the policy says `who_documentation_required: true`, copy that flag as `true` in the output. Do not infer it or hardcode it.

## Template Vocabularies

The template file defines the exact enum values. Never guess them. Common enums include:

For quote tasks: `mode` (`"AIR"`, `"SEA"`, `"ROAD"`), `risk_level` (`"LOW"`, `"MEDIUM"`, `"HIGH"`), `validity_status` (`"VALID"`, `"STALE"`), `quote_basis` (`"EXW"`, `"EXW_ONLY"`, `"EXW_PLUS_FREIGHT_OPTIONS"`), `payment_terms` (`"NET_30_AFTER_PO"`, `"PREPAY_100"`).

For reconciliation tasks: `invoice_state` (`"PAID"`, `"OPEN"`, `"VOID"`), `payment_state` (`"PAID"`, `"PARTIAL"`, `"UNPAID"`), `recognition_status` (`"RECOGNIZED"`, `"MISSING_REVENUE_JOURNAL"`, `"NOT_REQUIRED_UNPAID"`), `stage` (`"WON"`, `"OPEN"`, `"LOST"`), `event_status` (`"SCHEDULED"`, `"ACTIVE"`, `"COMPLETED"`, `"CANCELLED"`), `voucher_status` (`"ACTIVE"`, `"DRAFT"`, `"EXPIRED"`, `"DISABLED"`).

Always read the template first to confirm which enums apply.

## Common Mistakes to Avoid

- Fabricating IDs or values instead of fetching them from the API.
- Using the list endpoint as the final answer without fetching individual record details.
- Mixing up field names between different templates (e.g., `risk_flag` vs `customs_border_risk` — the API uses one, the template may use the other; map carefully).
- Computing EXW total but forgetting to add freight costs for grand totals.
- Forgetting to check freight `valid_until` against the quote date.
- Applying payment terms from the wrong customer's policy.
- Skipping revenue journal checks for paid milestones in reconciliation tasks.
- Returning JSON wrapped in markdown fences — the output must be raw JSON.
- Leaving template placeholder values (like `""` or `0`) in the final JSON instead of computed values.

## Performance

Batch API calls when possible. For list endpoints that return summary records, you typically need the individual detail endpoint for each relevant record. Parallelize those individual GET calls rather than fetching them sequentially.

## Reference Files

- [api_reference.md](api_reference.md) — Full field-level documentation for every endpoint
- [business_rules.md](business_rules.md) — Expanded business rules with detailed examples drawn from the training tasks
