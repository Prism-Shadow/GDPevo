# Notes for test_005

## English

This test task is a board labor-cost sensitivity pack for `ENS-OAK` under `case_oak_sensitivity`. It is derived from `E002` and anchored by `train_002` and `train_005`.

The task asks for annual forecast totals, growth rates, Year + 2 quarter and pay-type detail, roster treatment counts, largest growth pay type, and a controlled risk classification. The risk rule is solver-visible in the request memo; the calculation logic still depends on the shared rate book, roster, and scenario drivers.

Transfer-dependent difficulty includes cumulative driver use, future-year seniority bands, quarter-week handling, and combined overscale/title treatment. Task-specific difficulty comes from the Oak roster's partial-quarter employees and a separate board sensitivity case.

There are 8 scoring points with raw weights 1, 3, 2, 2, 3, 2, 2, and 2. The evaluator exact-matches numeric totals and the risk enum.
