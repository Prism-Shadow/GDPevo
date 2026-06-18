# Notes
## English

- Task: `test_002` for `task_group_002`.
- Scenario: new NGO cholera response module EXW quote for RFQ `RFQ-TE-CHOL-882`, customer `CUST-RELIEFPOINT`, quote date `2026-06-01`.
- Main behavior being tested: normalize the noisy RFQ to the requested cholera module lines only, without duplicate commercial lines or component-level expansion.
- Required business controls: `EXW_ONLY`, freight excluded, `PREPAY_100`, 30-day offer validity, `duplicate_rfq_normalized` true, module-line granularity, component exclusion, new-client policy source, indicative EXW scope, and catalog-line-sum total basis.
- Evaluation uses eight weighted checks totaling 18 points: module-only line set, quantities, catalog prices and line totals, grand total, shelf-life and lead-time fields, commercial scope controls, granularity/component controls, and policy-source controls.
