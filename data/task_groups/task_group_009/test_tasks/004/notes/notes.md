# Notes for test_004

## English

This test task is the all-company branch dashboard, derived from `E001` and anchored by `train_001` and `train_004`. It requires aggregation across all active branches in the shared Finance Ops environment.

The task definition is to produce FY2024/FY2025 revenue, FY2025 EBITDA, revenue growth, EBITDA margin, ARPU, sales per labor headcount, and four branch ranking facts. The visible payloads include only the environment entry point, board memo, and output schema.

The solution uses `/api/finance/branches` for the active branch set, `/api/finance/period-map` for fiscal years, `/api/finance/accounts` for rollups, and `/api/finance/records` for monthly values. The ranking checks require separate branch-level calculations for revenue growth, ARPU, gross-margin growth, and order growth.

There are 7 scoring points with raw weights 1, 1, 1, 3, 3, 1, and 2. Transfer-dependent points are period mapping, account classification, all-company aggregation, same-scope operating ratios, and ranking direction. Intrinsic difficulty comes from doing the same calculations over the full branch universe.
