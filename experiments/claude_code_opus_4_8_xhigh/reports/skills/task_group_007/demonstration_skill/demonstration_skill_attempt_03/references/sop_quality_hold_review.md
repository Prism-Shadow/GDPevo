# SOP: Supplier quality-hold / replenishment-control review

**Shape of task:** for a short list of target suppliers, review recent incidents + supplier
quality status + open/confirmed POs and decide a replenishment control per supplier, then list
the POs held. Output is `{analysis_window, supplier_decisions[], held_po_ids[],
release_supplier_ids[], summary}`.

The request payload gives `target_supplier_ids`, the analysis window (`start`, `end`), and the
allowed `decision_choices` (e.g. `freeze_new_replenishment`, `buyer_review_required`,
`monitor_only`). `analysis_window` is copied from the request.

## Per supplier

For each target supplier:
1. **Recent incidents**: `GET /incidents?start=<start>&end=<end>&supplier_id=<id>` (open_date,
   inclusive). From this filtered list compute:
   - `recent_incident_count` = number of incidents.
   - `recent_rma_count` = incidents with `incident_type == RMA`.
   - `severe_or_critical_count` = incidents with `severity in {high, critical}`.
   - `open_incident_count` = incidents with `status == open`.
   - `affected_skus` = sorted unique `sku` values across the incidents.
   - `sample_incident_ids` = the incident ids sorted ascending, **capped at 5** (first 5).
2. **Quality status**: `quality_status` from `/suppliers`.
3. **Held POs** (see below).

## Decision (precedence top-down; first match wins)

Read the request's policy; the observed training logic was:

1. **freeze_new_replenishment** if `quality_status == quality_hold`. (A supplier on a hard
   quality hold gets its replenishment frozen.)
2. **buyer_review_required** if the supplier is elevated-risk but not on hold — observed
   trigger: `quality_status == watch` **and** `severe_or_critical_count >= 2`. (Multiple
   severe/critical recent incidents warrant a buyer to review before reordering.)
3. **monitor_only** otherwise (e.g. `watch`/`approved` with few severe incidents, even if the
   raw incident count is higher). Volume alone does not force review — severity does.

If the request states different thresholds, follow the request. Note that a single critical
incident does **not** by itself force buyer review (it took two severe/critical to escalate in
the training data); be conservative and prefer monitor_only when the elevated-risk signal is
weak.

## held_po_ids per supplier

- For `monitor_only` suppliers: hold **nothing** (`[]`). Releasing-from-control means no POs
  are held.
- For `freeze_new_replenishment` and `buyer_review_required` suppliers: take the supplier's
  POs with `status in {open, confirmed}`, sort by `po_id` ascending, and hold the **first 5**
  (cap at 5). (`received` / `cancelled` POs are never held.)

This 5-cap mirrors the 5-cap on sample incident ids — both surface a bounded sample rather
than the full set. If a future template removes the cap or filters POs differently (e.g. only
POs for affected SKUs), follow the template; absent other guidance, first-5-by-po_id is the
observed convention.

## Roll-ups

- `held_po_ids` (top level) = sorted unique union of every supplier's held POs.
- `release_supplier_ids` = suppliers whose decision is `monitor_only`, sorted.
- `supplier_decisions` sorted by `supplier_id` ascending; each row carries `supplier_id`,
  `supplier_name`, `quality_status`, the four counts, `affected_skus`, `sample_incident_ids`,
  `decision`, and its `held_po_ids`.

## summary

`suppliers_reviewed` (count of targets), `freeze_count`, `buyer_review_count`,
`monitor_count` (decision tallies), `held_po_count` (size of the deduped top-level
`held_po_ids`), `total_recent_incidents` (sum of `recent_incident_count`).

## Pitfalls
- Holding POs for a `monitor_only` supplier (it holds none).
- Including received/cancelled POs, or exceeding the 5-PO / 5-incident-sample cap.
- Letting incident **volume** override the severity-driven decision (more incidents but few
  severe → still monitor_only).
- Wrong window or wrong date field on `/incidents`.
