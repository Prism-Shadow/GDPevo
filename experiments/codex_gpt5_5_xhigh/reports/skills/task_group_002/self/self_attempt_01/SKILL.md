# MedBridge Sales Ops SOP

Use this skill for MedBridge Sales Ops tasks that ask for quote/RFQ reconciliation, freight options, account milestone status, invoices, payments, revenue recognition, events, or vouchers.

## API workflow

- Use the environment note for the base URL. Sanity check with `GET /health`, then inspect `GET /api` if endpoints are uncertain.
- Public collections: `/api/customers`, `/api/products`, `/api/rfqs`, `/api/quotes`, `/api/freight-quotes`, `/api/policies`, `/api/opportunities`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`.
- Most collections also support `GET /api/<collection>/<id>` where listed by `/api`; otherwise fetch the collection and filter locally.
- Use `/api/search?q=<text>` for ambiguous customer names, product names, quote IDs, RFQ IDs, contacts, event names, or voucher codes. Treat search as discovery, then verify against the canonical collection record.
- Pull policies early. They define payment terms, quote scope, freight validity, module granularity, quote validity, EXW exclusions, and revenue recognition.

## Source precedence

- Exact ID in the task beats search results. If an ID is not given, prefer exact name/contact/product matches over fuzzy matches.
- Current commercial records beat older planning records: prefer RFQs with active working statuses such as `open`, quotes with `revision_requested` or `advisory_requested` when the task is about active revisions, and closed/won opportunities when the task is about service delivery.
- Ignore or clearly label records with `draft`, `superseded`, `archived`, `closed_lost`, `stale`, or `mismatch` unless the question explicitly asks about them.
- For quote revisions, use the current `confirmed_quantity` or line-level `confirmed_quantity`; prior quantities and prior prices are historical context only.
- Product catalog `price_tiers` override prior quote prices and benchmark notes. Choose the tier where `min_qty <= quantity` and `quantity <= max_qty`, treating `max_qty: null` as no upper bound.
- Module RFQs should stay at module/bundle line level. Do not price components from composition notes unless the customer explicitly asks for component-level pricing.
- Customer payment profile is useful context, but policy rules override it when applicable, especially new NGO prepayment and recurring NGO net terms.

## Quote and RFQ reconciliation

- For each requested line, join RFQ/quote `product_code` to `/api/products`.
- Quantity source order: line `confirmed_quantity`, quote `confirmed_quantity`, line `requested_quantity`, RFQ `requested_modules[].quantity`.
- Calculate `unit_price_usd` from the selected catalog tier. Calculate `line_total_usd = quantity * unit_price_usd`.
- Carry product `unit`, `lead_time_days` or `lead_time_weeks`, `weight_kg`, `cbm`, and `cold_chain_required`.
- Shipment totals are normally `sum(quantity * product.weight_kg)` and `sum(quantity * product.cbm)` unless an attached freight quote provides the shipment metrics to use.
- For indicative RFQs without a confirmed destination, quote EXW only and exclude freight. Include EXW exclusions: freight, insurance, import duty, customs clearance, and last-mile handling are not included unless separately offered.
- For module requests, consolidate repeated module quantities when the RFQ narrative says to consolidate. Do not split sachets, kits, or components out of a module.

## Freight handling

- Join freight options by `freight_quotes.quote_id == quote.id`.
- Use only options with `status: active` unless the user asks to discuss stale/mismatched options. Exclude `stale` and `mismatch` from recommended pricing.
- Check `valid_until`; freight is valid only through that date and must be reconfirmed at final order.
- Preserve freight as separate optional lines when the incoterm is `EXW plus freight options`; do not roll freight into the EXW product subtotal unless asked for a delivered total.
- Include `mode`, `forwarder`, `cost_usd`, `transit_days_text`, `route_risk`, `risk_notes`, `valid_until`, and cold-chain support when relevant.
- If any product requires cold chain, verify freight `cold_chain_support`; flag non-supporting options instead of silently recommending them.
- For grant or need-by timing, compare product lead time plus freight transit range against the stated need-by date. Prefer transparent risk notes over overconfident pass/fail claims.

## Account, invoice, and revenue tasks

- Join `opportunities` to `customers`, then phases to `invoices` by `invoice_id` and `phase_id`.
- Join invoices to `payments` by `invoice_id`; use posted payments to verify paid status and payment date/reference.
- Join revenue by `revenue-journals.invoice_id` or `phase_id`.
- Revenue recognition rule: when a milestone is complete and paid, verify or create recognition from Deferred Revenue to Implementation Services Revenue. Paid complete milestones without a posted revenue journal are missing recognition. Unpaid future milestones stay outstanding. Due or overdue unpaid invoices drive collection follow-up.
- Treat `proposal`, `negotiation`, and draft invoices as distractors for won-account revenue recognition unless the task explicitly asks about pipeline/proposals.
- Use invoice `status`, `due_date`, `paid_amount_usd`, and `outstanding_amount_usd` together; do not infer paid/overdue from one field alone.

## Events and vouchers

- Join events to vouchers by `events.voucher_code == vouchers.code`, and also verify matching `customer_id` and `opportunity_id`.
- Report event `status`, `event_date`, `primary_contact`, `follow_up_owner`, and voucher `discount_percent`, `max_redemptions`, `redemptions_used`, `valid_until`, and `status` when asked for follow-up readiness.
- Expired, completed, tentative, or nonmatching event/voucher records should be labeled instead of mixed into current active recommendations.

## Output conventions

- Follow any requested schema exactly. If none is specified, use a compact table plus short notes.
- Preserve API identifiers exactly: `customer_id`, `product_code`, `quote_id`, `rfq_id`, `invoice_id`, `phase_id`, `event_id`, and voucher `code`.
- Money is USD unless a record says otherwise. Use two decimals for calculated amounts and keep freight separate from catalog/product subtotals.
- Dates should be ISO `YYYY-MM-DD`. Quote pricing is valid for 30 calendar days from `quote_date` unless overridden; freight validity uses each freight quote `valid_until`.
- Status words should come from the API when possible. If adding an interpretation, make it explicit, e.g. "action: collect", "risk: stale freight", or "recognition missing".
- Include concise source notes for non-obvious decisions: tier selected, stale/mismatch freight excluded, EXW exclusions, payment-term policy, or revenue-recognition gap.

## Common traps

- Component composition arrays and narrative component lists are usually distractors for module quotes.
- Prior quantities, prior unit prices, older benchmarks, and superseded RFQs should not override current quote/RFQ quantities or catalog tiers.
- Freight quotes can share a quote ID but still be stale, mismatched, wrong-size benchmarks, or distractor routes; filter by status and reasonableness.
- New NGO/prospect accounts generally need prepayment policy treatment even when the customer profile says review.
- EXW does not include freight or import/delivery costs; "EXW plus freight options" means separate optional freight.
- Paid invoice does not automatically mean recognized revenue; verify a revenue journal for each complete-and-paid milestone.
- Open proposals and draft invoices are not closed-won revenue obligations unless the task asks about pipeline.
