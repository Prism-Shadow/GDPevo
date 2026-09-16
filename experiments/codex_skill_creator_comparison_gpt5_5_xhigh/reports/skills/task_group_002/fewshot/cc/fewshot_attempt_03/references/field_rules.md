# MedBridge Field Rules

Use these rules after gathering API evidence. They are schema-adaptation rules, not fixed answer values.

## Evidence Collection

- Start with IDs in the prompt: quote IDs, RFQ IDs, customer IDs, opportunity IDs, event IDs, voucher codes, invoice IDs, freight IDs, and product codes.
- Fetch direct records first. Then use exact searches to find linked records:
  - quote ID -> freight quote candidates
  - RFQ ID -> requested modules and customer
  - opportunity ID -> invoices, payments, revenue journals, events, vouchers
  - customer or explicit account display name -> linked event/voucher records when the prompt asks for them
- Policies are general business rules. Fetch them when output fields mention payment terms, quote validity, EXW scope, freight reconfirmation, module granularity, or revenue recognition.

## Price and Quote Fields

- `quote_id` or `rfq_id`: use the API record ID that matches the prompt.
- `customer_id`: use API `customer_id`.
- `quote_date` or `as_of_date`: use the date specified in the prompt or source record for the business decision.
- `product_code`: use the quote line product or RFQ requested module code.
- `confirmed_quantity` or `quantity`: use the prompt-confirmed quantity when present; otherwise use the source record.
- `article_number`: use product `article_number`.
- `unit_price`, `unit_price_usd`, or catalog tier price: selected product tier `unit_price_usd`.
- `lead_time_days`: selected tier `lead_time_days`.
- `shelf_life_months`: product `shelf_life_months`.
- `line_total`: quantity times unit price.
- `exw_total_usd` or `grand_total` before freight: sum of all line totals.
- `quote_basis`: adapt from incoterm and policy. Use an EXW-only value for indicative quotes without destination; use an EXW-plus-freight value when freight options are separate additions.
- `offer_validity_days`: use the quote-validity policy when the template asks for offer validity.
- Documentation flags come from the prompt, product family, customer type, and policy records; keep boolean fields boolean.

## Freight Fields

- `freight_id`: freight record `id`.
- `mode`: uppercased freight `mode`.
- `freight_cost_usd`: freight `cost_usd`.
- `valid_until`: freight `valid_until`.
- `transit_days`: use API text or compact min-max style to match the target template style.
- `grand_total_usd`: EXW total plus freight cost.
- `validity_status`: `VALID` when active and not expired on the quote date; otherwise `STALE` or the closest enum in the template.
- `source_is_stale`: true when status is stale, validity expired, or notes identify a stale source.
- `risk_level`: uppercased `route_risk`.
- `risk_flag`: `NONE` for low risk; otherwise use the template's border/customs risk enum when available.
- `customs_border_risk`: derive from customs/border wording in risk notes. If the note only mentions shelf-life, congestion watch, or longer transit, do not inflate customs risk.
- `all_freight_options_valid_on_quote_date`: true only when every included option is active and valid through the quote date.
- `freight_reconfirmation_required`: true when freight policy says to reconfirm at final order, any included option is stale/expired, or the prompt asks for freight-control flags.
- `recommended_mode`: choose among included options after excluding stale and high customs/border risk options; then prefer lowest cost unless urgency, temperature control, or prompt instructions change the priority.
- Warning text should be concise and mention only material control issues: reconfirmation requirement, expired validity, stale source, high customs/border risk, or excluded freight.

## Policy and Account Terms

- Customer `payment_profile`, `segment`, `customer_type`, recurring status, prompt account type, and policy records determine payment terms.
- New NGO accounts without approved credit generally require `PREPAY_100`.
- Recurring approved NGO or commercial accounts generally use `NET_30_AFTER_PO` unless the prompt or policy is stricter.
- Module RFQs stay at module line level unless component pricing is explicitly requested.
- EXW-only quotes exclude freight. EXW-plus-freight quotes show freight as separate options and keep freight controls visible.

## Milestone and Revenue Fields

- Phase order determines normalized milestone labels when the template uses `MS1`, `MS2`, `MS3`, or phase numbers.
- `phase_total_amount`: sum opportunity phase amounts.
- `opportunity_matches_phase_total`: compare phase total to won amount.
- `total_paid_amount`: sum paid invoice amounts or posted payments. Prefer reconciled invoice paid totals when present.
- `outstanding_balance`: sum invoice outstanding amounts, or opportunity outstanding amount when it agrees with invoices.
- `invoice_state`: map paid to `PAID`, unpaid/open outstanding invoices to `OPEN`, void to `VOID`, otherwise `UNKNOWN` if allowed.
- `payment_state`: `PAID` when paid amount equals invoice amount; `PARTIAL` when paid amount is greater than zero but less than invoice amount; `UNPAID` when paid amount is zero.
- `amount_unpaid`: invoice amount minus paid amount.
- `due_date`: null for fully paid milestones when the field drives follow-up; otherwise use invoice due date.
- Revenue recognition is required for paid completed milestones. Match posted journals by opportunity plus invoice ID or phase ID.
- Missing revenue recognition for a paid milestone should create the template's accounting action, usually owned by accounting.
- Unpaid future milestones do not need revenue recognition; route collection or monitoring based on due date and as-of date.

## Event and Voucher Fields

- Fetch explicit event IDs and voucher codes from the prompt first. If missing, use linked records found by exact opportunity/customer search.
- Map event status and voucher status to template enums by uppercasing and adapting confirmed/scheduled wording to the closest allowed enum.
- Voucher discount fields use the voucher's numeric discount value; max-use fields use max redemptions.
- Invitation tasks should use the prompt's contact name when supplied. If a due date is required but only an event date is available, set a reasonable pre-event task date from the business context rather than the event date itself.
