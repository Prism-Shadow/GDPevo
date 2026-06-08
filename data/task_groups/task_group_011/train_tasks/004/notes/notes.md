# train_004 Notes: Summit watch-list stress and workout actions

## English

Data lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, source examples `E001`, `E002`, and `E003`, and follows the task-group design for `train_004`. It uses only the shared environment data in `task_group_011_bank_branch_credit_risk_lending_committee/env`: branch `SUMMIT`, public policies, and loan records from the credit-office API/database.

Task definition: The solver-visible request asks for a committee-ready JSON watch-list packet for Summit as of 2025-03-31. The target population is loans with `current_rating >= 6`. The output must include `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, and `severe_bucket_counts`.

Scenario fit and material map: `/api/branches/SUMMIT/loans` supplies the loan records; `/api/policies` supplies CDFI factor scores and the +200bp watch-list stress formula; `answer_template.json` defines the exact output schema. The workflow is a portfolio surveillance and workout triage task, matching the source examples' watch-list, stress, and adverse-classification work.

Solution basis: Summit has seven adversely rated loans totaling 7,675,179.41. CDFI-style objective factor scores use available LTV, FICO, liquidity months, and debt-to-asset factors; missing non-applicable factors are not scored. The `Projected Loss` classification is assigned to the underwater nonaccrual/loss-grade loan `SUM-LN-902`, consistent with the source scenario's projected-loss convention. Watch-list stress uses `stressed_dscr = dscr / 1.18`, rounded to two decimals, and flags breaches below 1.00. Action mapping follows the portfolio surveillance convention: rating 6 to `watchlist`, rating 7 to `special_assets`, and underwater/nonaccrual loss-grade exposure to `partial_chargeoff_review`.

Scoring basis: Seven exact-match points are used: SP001 adverse count/balance weight 2; SP002 risk classes weight 3; SP003 stressed DSCR breach set and DSCR values weight 3; SP004 largest problem exposure/action weight 2; SP005 projected-loss classification weight 2; SP006 severe bucket counts weight 2; SP007 monitoring cadence weight 1. Common pitfalls are using all Summit loans instead of adverse-rated loans, treating DSCR-missing loans as stress breaches, forgetting the underwater projected-loss override, or mis-sorting the severe bucket counts.

Transfer design: As a train task, this teaches by answer comparison how the shared policy fields, CDFI factor-score bins, watch-list stress formula, action enums, and payment-status/risk-rating cross-tabs are expected to be operationalized. It anchors later Central-branch watch-list stress work without exposing those test answers.

Construction record: Author `train_004_builder`; created and updated 2026-06-03. Major changes: created minimum complete prompt, template, standard answer, evaluator, and notes.

