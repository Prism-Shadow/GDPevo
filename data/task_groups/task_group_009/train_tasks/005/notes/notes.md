# Notes for train_005

## English

This train task extends `E002` into a two-year board forecast for `ENS-MAPLE` under scenario `case_maple_board`. It requires the solver to combine the compensation rate book, roster records, and scenario driver data.

The visible task asks for current, Year + 1, and Year + 2 annual totals; Year + 2 quarter totals; Year + 2 pay-type totals; growth rates; largest growth pay type; and roster treatment counts. It preserves the source example's driver-change modeling workflow in structured JSON form.

Material map: `/api/compensation/rate-book` provides pay types, MWS, title percentages, seniority bands, and forecast rules. `/api/compensation/rosters` provides ensemble-specific employees. `/api/compensation/scenarios` provides future-year growth factors.

The standard answer applies the scenario drivers cumulatively, advances years of service before assigning seniority bands, uses roster quarter weeks, and avoids double-counting title premiums when overscale notes say they are combined. Scoring uses 8 points with raw weights 1, 3, 2, 2, 3, 2, 1, and 1.

Transfer design: this task reinforces future-year driver handling and roster-note treatment for compensation tests `test_002` and `test_005`.

Construction record: created by Codex on 2026-06-02.

