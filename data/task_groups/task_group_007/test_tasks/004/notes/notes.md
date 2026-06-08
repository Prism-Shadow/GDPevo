# test_004 Notes

## English

Data/source lineage: This task belongs to `SCN_007_erp_inventory_order_fulfillment` and uses source examples `E001`, `E002`, and `E003`. The assigned brief is `test_004` in `scratch/task_builder_briefs.md`: build an order release task for `TEST_QUALITY_E` that combines fulfillment checks with supplier quality holds and active severe incidents. The shared generated environment under `task_group/task_group_007/env/` supplies the authoritative ERP API data. Task-local solver-visible payloads are `input/prompt.txt`, `input/payloads/release_control_memo.md`, and `input/payloads/answer_template.json`.

Task definition: The solver must inspect live API records for `TEST_QUALITY_E`, classify each order as `RELEASE_TO_SHIP`, `MANUAL_REVIEW`, or `BACKORDER_INVENTORY`, identify blocked SKUs, attach controlled reason codes, and produce a supplier-risk rollup. The expected JSON includes per-order decisions, inventory status, quality-hold suppliers, active severe incident IDs, risk supplier IDs, next actions, and summary counts.

Scenario fit and material map: This is an ERP release-control workflow using `/orders?wave=TEST_QUALITY_E`, `/customers/<customer_id>`, `/products/<sku>`, `/inventory?warehouse_id=&sku=`, `/suppliers`, and `/incidents?status=open`. It combines fulfillment control from `train_001` and `train_004` with supplier quality and incident analysis from `train_005` and `train_003`.

Solution basis: Effective available stock is `on_hand - reserved - quarantined - safety_stock`. An order has `SHORTAGE` when any ordered SKU is below the order quantity at the order warehouse. High and critical open incidents are active severe incidents. The supplier-risk rollup covers suppliers represented in the wave by ordered SKUs under supplier quality hold or by active severe incidents on ordered SKUs. Account blocked, account review, supplier quality hold, inactive product, and active severe incident conditions route covered orders to release-control review; uncovered orders without manual-review overrides become `BACKORDER_INVENTORY`; fully covered orders without risk become `RELEASE_TO_SHIP`.

Standard answer summary: 12 orders; 6 backorders, 5 manual reviews, and 1 release. Risk suppliers are `SUP-002`, `SUP-003`, `SUP-007`, `SUP-009`, `SUP-010`, and `SUP-011`. Active severe incidents counted in the wave are `INC-90028`, `INC-90043`, `INC-90048`, `INC-90154`, `INC-90174`, `INC-90182`, and `INC-90201`.

Evaluation is exact-match with 8 scoring points and total raw weight 17: SP1 release decisions, weight 3; SP2 inventory statuses and blocked SKUs, weight 2; SP3 reason code sets, weight 3; SP4 quality-hold supplier mapping, weight 2; SP5 active severe incident IDs and risk supplier IDs, weight 2; SP6 risk supplier rollup, weight 3; SP7 next actions, weight 1; SP8 summary counts and order-id sets, weight 1.

Likely pitfalls: using on-hand stock instead of effective availability; ignoring safety stock; treating only `critical` as severe and missing `high`; applying active severe incidents at whole-supplier level instead of ordered-SKU evidence for the rollup; missing inactive product `NW-1019`; allowing account review orders to backorder without release-control review.

Transfer design: `train_001` anchors customer override and fulfillment outcome conventions. `train_004` anchors effective availability and backorder/manual-review distinctions. `train_005` anchors supplier quality holds and incident-linked release control. `train_003` reinforces incident filtering and high/critical severity treatment. Transfer-dependent points are SP1, SP3, SP4, SP5, and SP6; SP2 also benefits from train-derived effective-stock calculation.

Construction record: Author `test_004` task-builder subagent. Created 2026-06-01. Updated 2026-06-01. Built only `task_group/task_group_007/test_tasks/004/` and `scratch/task_builder_reports/test_004.md`.

