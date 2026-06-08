# Notes for test_001

## English

This test task extends the branch reporting workflow from `E001` and is anchored by `train_001` and `train_004`. It targets `BR-009`, with a noisy local memo that omits one South-region branch.

The task asks for a branch close package: M24 income statement, M24/M23 revenue variance, FY2025 branch metrics, regional context, and branch ranking facts. The visible payloads provide environment access, the target branch and periods, and the output schema.

Material map: Finance Ops period map resolves the fiscal-year convention; account metadata controls rollups; branches define the correct South-region membership; records provide monthly values. The stale memo is a source-conflict distractor.

Evaluation has 8 scoring points with weights 2, 2, 1, 2, 3, 2, 2, and 3. Transfer-dependent points include period convention, account rollup, same-scope ARPU and labor-headcount ratios, regional branch inclusion, and ranking direction. Task-specific difficulty comes from exploring a different branch and region.

Likely pitfalls include following the stale local memo, treating M1-M12 as the current year, omitting allocations from EBITDA, or computing ARPU from a single month instead of the fiscal-year record set.

Construction record: created by Codex on 2026-06-02.

