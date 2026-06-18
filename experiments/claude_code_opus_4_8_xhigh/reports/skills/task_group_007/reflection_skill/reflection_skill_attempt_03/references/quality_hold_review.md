# SOP: Procurement quality-hold replenishment-control review

A request payload names `target_supplier_ids`, an `analysis_window` (start/end), and the allowed
`decision_choices`. For each target supplier, compute recent-incident metrics over the window, assign a
replenishment-control decision, and hold purchase orders. Report per-supplier rows (sorted by
`supplier_id` asc), a global held-PO list, a release list, and a summary.

## Data to pull
- `GET /suppliers` (quality_status, name).
- `GET /incidents?supplier_id=&start=&end=` per supplier (window filters `open_date`, inclusive).
- `GET /purchase_orders?supplier_id=` per supplier.

## Per-supplier recent-incident metrics (over the window)
- `recent_incident_count` = incidents with `open_date` in [start, end].
- `recent_rma_count` = those with `incident_type == RMA`.
- `severe_or_critical_count` = those with `severity in {high, critical}`.
- `open_incident_count` = those with `status == open`.
- `affected_skus` = sorted unique SKUs from those incidents.
- `sample_incident_ids` = the first **up to 5** incident ids after sorting ascending (a max-5 cap).

## Decision policy (validated; payload policy is authoritative if it states thresholds)
The decision is **not** determined by coarse `quality_status` alone. Apply, first match wins:

1. `quality_status == quality_hold` → `freeze_new_replenishment`.
2. else if recent risk is material → `buyer_review_required`. The validated discriminator is
   **`severe_or_critical_count >= 2`** (a supplier on `watch` with only 1 severe/critical incident lands
   on monitor even with more total incidents / RMAs / an open incident). Treat `severe_or_critical_count`
   as the primary risk signal; if the payload gives explicit thresholds (incident count, rma count, cost),
   apply those exactly and in the payload's order.
3. else → `monitor_only`.

Validated example shape (do not hardcode — illustrates the boundary): quality_hold ⇒ freeze; watch with
2 severe/critical ⇒ buyer_review; watch with 1 severe/critical (even with higher incident/RMA/open
counts) ⇒ monitor.

## Held purchase orders (the corrected, important rule)
- A supplier's `held_po_ids` = its POs with `status in {open, confirmed}`, sorted ascending, **capped at
  the first 5** (same max-5 sampling convention as `sample_incident_ids`).
- Hold POs for every supplier whose decision is **not** the lowest tier `monitor_only` — i.e. both
  `freeze_new_replenishment` AND `buyer_review_required` suppliers get up to 5 held POs. `monitor_only`
  suppliers hold none (`[]`).
- Do **not** hold all open/confirmed POs without the cap, and do **not** restrict the held set by SKU or
  eta — it is purely the first-5 open/confirmed ids by ascending po_id.

(Blind-phase error: it held ALL open/confirmed POs and only for the frozen supplier. Correct is first-5,
for freeze and buyer_review alike.)

## Derived outputs
- Top-level `held_po_ids` = sorted unique union of every supplier's `held_po_ids`.
- `release_supplier_ids` = supplier_ids whose decision is `monitor_only`, sorted.

## Summary (recompute from rows)
- `suppliers_reviewed` = number of target suppliers.
- `freeze_count`, `buyer_review_count`, `monitor_count` = decision tallies.
- `held_po_count` = size of the top-level held_po_ids union.
- `total_recent_incidents` = sum of `recent_incident_count` across suppliers.
