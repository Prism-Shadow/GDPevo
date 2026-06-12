# Notes for train_002

## English

This train task is derived from `E002`, the orchestra CBA compensation forecast model. It asks for the current-year compensation summary for `ENS-REDWOOD` using the shared compensation rate book and roster data.

The task definition requires quarter totals, annual pay-type totals, annual total, largest pay type, and counts for combined overscale/title notes and partial-quarter employees. The visible inputs are the prompt, environment access payload, request memo, and answer template.

Material map: `/api/compensation/rate-book` supplies MWS, pay types, title premium percentages, seniority bands, quarter weeks, and business rules. `/api/compensation/rosters?ensemble_id=ENS-REDWOOD` supplies employee roster attributes, overscale, years of service, quarter weeks, and notes.

The solution calculates Minimum Weekly Scale, Titled Position Premium, Seniority, and Overscale for each roster row and quarter. If a roster row says combined overscale includes title premium, title premium should not be added separately. Partial-quarter rows use their listed quarter weeks. The seven scoring points have raw weights 2, 3, 3, 2, 1, 2, and 2.

Transfer design: this task teaches the solver to separate rate-book assumptions from roster inputs, use quarter weeks, and inspect overscale/title notes. Those conventions transfer to compensation forecast test tasks.
