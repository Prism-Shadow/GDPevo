# test_004 Notes: Central branch watch-list stress report

## English

Data lineage: This task belongs to `SCN_011_bank_branch_credit_risk_lending_committee`, source examples `E001`, `E002`, and `E003`, and follows the task-group design for `test_004`. It uses only shared public environment data for branch `CENTRAL`: loans, branch metrics, public policy, and the FDIC Q4 2024 benchmark.

Task definition: The solver-visible request asks for a committee-ready JSON packet for Central as of 2025-03-31. The target population is loans with `current_rating >= 6`. The output includes `branch_id`, `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`, and `npa_benchmark`.

Scenario fit and material map: `/api/branches/CENTRAL/loans` supplies loan records, `/api/branches/CENTRAL/metrics?quarter=2025Q1` supplies total and nonperforming loan balances, `/api/policies` supplies factor-score and stress conventions, and `/api/benchmarks/fdic/q4-2024` supplies the benchmark. This is a portfolio surveillance, stress, and workout triage workflow in the same family as the source examples.

Solution and evaluation basis: Central has seven adversely rated loans totaling 8,959,908.25. Available LTV, FICO, liquidity-month, and debt-to-asset factors produce the CDFI-style class map in `answer.json`; missing non-applicable factors are not scored. The large hotel loan `CEN-LN-901` is underwater and nonaccrual, so it is the projected-loss exposure and receives `partial_chargeoff_review`. The +200bp watch-list stress uses `dscr / 1.18`, rounded to two decimals, and all four adverse loans with DSCR breach 1.00 after stress. NPA exposure is 7,753,634.12 over total loans of 20,504,486.58, producing a 0.3781 branch ratio and 3,683.43 bps variance over the FDIC 0.0098 benchmark.

Scoring basis: Seven exact-match scoring points are used: SP001 adverse count/balance weight 2; SP002 risk class mapping and projected-loss set weight 3; SP003 stressed DSCR breach set weight 3; SP004 dominant problem exposure/action weight 2; SP005 severe bucket counts weight 2; SP006 NPA/FDIC variance weight 2; SP007 monitoring cadence weight 1. Common pitfalls include using all weak-looking Central loans instead of only current-rating adverse loans, treating missing DSCR as a breach, missing the projected-loss override, or using the wrong FDIC benchmark field.

Transfer design: The main transfer anchor is `train_004`, which establishes CDFI factor scoring, watch-list stress arithmetic, projected-loss treatment, workout action enums, and severe bucket counts. `train_001` anchors NPA numerator/denominator handling and the FDIC total-loans noncurrent benchmark comparison. High-value scoring points SP002, SP003, SP004, SP005, and SP006 depend on those anchors plus Central-specific exploration.
