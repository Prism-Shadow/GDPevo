# Notes for test_003

## English

This test task extends `E003` and is anchored by `train_003`. It targets production `PROD-LYRIC-27`, which has a different service mix, more musicians, sound-check duration issues, and multiple premium combinations.

The task asks for service counts, category totals, weekly total, conflict flags, per-musician totals, and top-paid musician. The visible prompt does not provide step-by-step payroll logic; the solver must use the shared payroll rate book and production data.

Material map: `/api/payroll/rate-book` contains service rates, time limits, premium percentages, doubles, vacation, substitute, and guarantee rules. `/api/payroll/productions` contains schedule and roster assignments.

Transfer-dependent scoring points include premium stacking, substitute electronic treatment, doubles, weekly guarantee adjustments, service time-limit conflicts, and sorted conflict flags. Task-specific difficulty comes from the larger roster and additional sound-check mismatch flags. There are 9 scoring points with raw weights 2, 3, 2, 3, 3, 1, 2, 2, and 2.
