# Quoting families (A, A′, B)

These produce a priced quote package. Always: pull the customer, the
quote/RFQ, and the product(s); select the catalog tier by *confirmed* quantity;
ignore `prior_*` price fields; recompute every total.

---

## Family A / A′ — Catalog quote + freight decision

Template A keys: `quote_summary`, `freight_options`, `policy_flags`.
Template A′ keys: `pricing` (with nested `catalog_tier`), `transport_decisions`,
`client_warnings`. Same underlying work; A′ asks for more explicit
validity/risk/warning fields.

### Steps
1. `GET /api/quotes/<quote_id>` → confirmed_quantity, customer_id,
   product_code, quote_date, `incoterm`, `source_notes`.
2. `GET /api/customers/<customer_id>` → segment / is_recurring / payment_profile
   → payment terms (see main SKILL "Payment terms").
3. `GET /api/products/<code>` → choose the `price_tiers` row bracketing the
   confirmed qty → unit_price, lead_time_days; product `shelf_life_months`.
   `exw_total = qty × unit_price`. (A′ also wants the tier's
   `min_quantity`/`max_quantity` echoed under `catalog_tier`; `max_qty:null`
   stays as the template wants, often a large/sentinel or echoed null — follow
   the template.)
4. Freight: fetch `/api/freight-quotes`, keep the canonical
   `FR-<PRODUCT>-<MODE>` rows for this exact `quote_id` (AIR, SEA, ROAD), drop
   `FR-DIS-*` and any row with a different `quote_id` or a non-`active` status
   that the loose filter dragged in. For each kept row:
   - `freight_cost_usd` = `cost_usd`
   - `transit_days` = from `transit_days_text` (e.g. "4-6 days"). If the
     template's example shows the numeric range without the word "days"
     (e.g. "3-5"), strip the suffix to match; otherwise keep `transit_days_text`
     verbatim. Match the template's own example formatting.
   - `valid_until` = the row's `valid_until`
   - `validity_status` (A′) = `VALID` if `valid_until >= quote_date` and
     `status == active`, else `STALE`. `source_is_stale` = the boolean of that.
   - `risk_level`/`route_risk` echo (UPPERCASE), and `risk_flag` per template
     (e.g. road medium → `MEDIUM_BORDER_RISK`, low → `NONE`).
   - `customs_border_risk` (A′): UPPERCASE, but border-specific — AIR/SEA
     usually `LOW`, ROAD takes the real border risk. Use `risk_notes` to judge:
     a SEA row whose `route_risk` is "medium" only for shelf-life reasons is
     still `LOW` customs/border risk.
   - `grand_total_usd` = exw_total + this option's freight_cost.
5. policy_flags / client_warnings:
   - `recommended_mode` = cheapest VALID, acceptable-risk option (compare
     grand_total). Exclude stale/expired and high-border-risk lanes.
   - `freight_reconfirmation_required` / `freight_reconfirmation_required`:
     `true` (POL-FREIGHT-RECONFIRM applies to all freight quotes).
   - `all_freight_options_valid_on_quote_date`: `true` only if every kept option
     has `valid_until >= quote_date`; `false` if any is stale.
   - `road_quote_invalid_or_stale` (A′): `true` if the ROAD row is stale/expired.
   - `freight_warning` (A′, free text): name the stale row, its expiry vs quote
     date, its risk, and that all rates need reconfirmation at order. Free text
     is matched loosely; be accurate and specific, not verbose.
   - `quote_basis`: map the quote `incoterm`. "EXW plus freight options" →
     `EXW_PLUS_FREIGHT_OPTIONS` (or the template's freight-inclusive token), not
     bare `EXW`.
   - `customer_policy` (category code, not the policy id) and `payment_terms`.

### Mistakes I made here (and the fix)
- Output `customs_border_risk` as lowercase raw `route_risk` (`medium` for sea).
  FIX: uppercase, and treat customs/border risk as border-specific → sea `LOW`.
- Used `validity_status: EXPIRED` for the stale road row. FIX: the enum is
  `STALE`.
- Set `quote_basis: EXW` when the quote was "EXW plus freight options".
  FIX: `EXW_PLUS_FREIGHT_OPTIONS`.
- Output the policy *id* for `customer_policy`. FIX: the category code
  (e.g. `RECURRING_NGO`).
- Left "days" on `transit_days` when the template's example used a bare range.
  FIX: match the template example's formatting.

---

## Family B — Module / RFQ EXW-only quote

Template keys: `quote_header`, `line_items`, `quote_controls`.

For indicative RFQs with no confirmed destination (POL-INDICATIVE-EXW):
quote EXW only, exclude freight.

### Steps
1. `GET /api/rfqs/<rfq_id>` → `requested_modules` (each `product_code` +
   `quantity`), customer_id, quote_date, currency. The RFQ may include a
   `component_composition_distractors` list and a narrative telling you NOT to
   split modules into component SKUs — **honor that: one line per requested
   module, never per component** (POL-MODULE-GRANULARITY).
2. For EACH requested module: `GET /api/products/<code>` → `article_number`,
   the single applicable `price_tiers` row → `unit_price`, `lead_time_days`;
   product `shelf_life_months`. `line_total = quantity × unit_price`.
   Emit one `line_items` entry per module, in RFQ order. (The template shows
   only one example line — include ALL requested modules, not just one.)
3. quote_controls:
   - `grand_total` = Σ line_total (cent precision; compute it, don't guess).
   - `freight_excluded`: `true`.
   - `payment_terms`: from customer → here typically `PREPAY_100` for a new NGO.
   - `offer_validity_days`: `30` (POL-QUOTE-VALIDITY).
   - `who_documentation_required`: `true` for WHO/IEHK emergency-health kits
     (template default for this kit family).
   - `quote_basis`: `EXW_ONLY`.

### Notes / pitfalls
- Do not split modules into components even though the API exposes
  `components` and the RFQ lists `component_composition_distractors`.
- A module with no quantity defaults to the RFQ's stated quantity (often 1).
- `grand_total` should equal the sum of the line totals you computed. Trust that
  sum; do not back-fill a different stored figure.
