# Notes for test_002

## English

This test task is a compensation forecast for `ENS-CEDAR` under `case_cedar_negotiation`. It is derived from `E002` and anchored by `train_002` and `train_005`.

The solver must produce annual totals, growth rates, Year + 2 quarter totals, Year + 2 pay-type totals, largest growth pay type, and roster treatment counts. The prompt does not provide the operating method; it only names the requested ensemble and scenario.

The solution uses the compensation rate book, roster rows, and scenario drivers. Transfer-dependent scoring points include seniority band advancement, cumulative future-year drivers, combined overscale/title handling, partial-quarter weeks, and pay-type construction. Task-specific difficulty comes from a larger roster and a different scenario with title percentage multipliers.

There are 8 scoring points with raw weights 1, 3, 2, 2, 3, 2, 1, and 1. Exact matching checks the structured answer fields.
