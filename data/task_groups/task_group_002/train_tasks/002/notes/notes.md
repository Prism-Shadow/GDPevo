# Notes
## English

- Task: `train_002` for `task_group_002`.
- Scenario: new NGO module-level EXW quote for RFQ `RFQ-TR-IEHK-204`, customer `CUST-NOVAID`, quote date `2026-06-01`.
- Main behavior being tested: quote requested IEHK modules only, not component composition.
- Required business controls: `EXW_ONLY`, freight excluded, `PREPAY_100`, 30-day validity, and WHO documentation required.
- Evaluation uses eight weighted checks: module line set, quantities, catalog unit prices, totals, shelf-life and lead-time fields, EXW/freight exclusion, new-client payment and validity, and WHO documentation flag.

