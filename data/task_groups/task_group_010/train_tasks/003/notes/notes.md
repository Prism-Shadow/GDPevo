# train_003 Notes

## English

### Data and Source Lineage

This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, using source examples `E001`, `E002`, and `E003`. The direct design anchor is `E003`, the quarterly active allocation view workflow. The task uses the implemented shared environment under `task_group/task_group_010_institutional_portfolio_risk/env/`, specifically `env/data/opportunity_sets.json`, `env/data/prior_views.json`, `env/data/macro_signals.json`, and `env/data/policies.json`. The task-local visible payload is `input/payloads/allocation_request.json`, which names the focused Q2 2026 opportunity-set subset and output fields.

### Task Definition and Scenario Fit

The solver acts as a CIO-desk analyst updating active allocation views for Q2 2026. The required output is a normalized JSON object with lineage fields, eight allocation rows, and one portfolio-level risk overlay. This fits the task group because it requires the same institutional investment strategy work as the source scenario: synthesizing current macro signals with prior allocation positioning, applying controlled portfolio-policy conventions, and producing committee-ready structured decisions instead of prose.

### Material Map

`input/prompt.txt` gives the business request and points solvers toward the relevant shared API surfaces. `input/payloads/allocation_request.json` defines the focus set: Europe, Japan, Emerging Markets, India, Latin America, U.S. Treasuries, Corporate High Yield, and EUR. `input/payloads/answer_template.json` defines the solver-visible schema, enum choices, and ordering expectations without revealing scoring weights or answers. In the shared environment, `opportunity_sets.json` supplies asset classes, `prior_views.json` supplies Q1-to-Q2 lineage records, `macro_signals.json` supplies Q2 signal scores and rationale codes, and `policies.json` supplies the as-of date and policy id.

### Solution and Evaluation Basis

The standard answer was derived from current environment records. Q2 signal scores map to views using the allocation policy, changes are measured against the Q1 prior view embedded in the `Q2_2026` prior-view records, and conviction follows the absolute signal-score bands. The resulting rows are: Europe `OW/UP/MEDIUM/EUROPE_RECOVERY`; Japan `UW/DOWN/MEDIUM/JAPAN_POLICY_RISK`; Emerging Markets `UW/DOWN/MEDIUM/CHINA_DEPENDENCE`; India `OW/UNCHANGED/HIGH/INDIA_OFFSET`; Latin America `OW/UP/MEDIUM/LATAM_DIVERSIFIER`; U.S. Treasuries `OW/UP/MEDIUM/DURATION_SUPPORT`; Corporate High Yield `UW/DOWN/MEDIUM/HY_VALUATION_RISK`; EUR `OW/UP/MEDIUM/EUROPE_RECOVERY`. The overlay is `DURATION_QUALITY_TILT` with primary action `tilt_to_duration_quality`, supported by `DURATION_SUPPORT`, `HY_VALUATION_RISK`, and `CHINA_DEPENDENCE`.

The evaluator has eight exact-match scoring points with raw weights: lineage fields weight 1; equity core views weight 3; diversifier views weight 3; rates/credit/currency views weight 3; all change directions weight 2; all convictions weight 2; all rationale codes weight 2; risk overlay weight 1. Row comparisons are keyed by `opportunity_set` so list order does not create incidental failures. Likely model pitfalls include treating `prior_views.json` as the final Q2 answer, ignoring current macro signals, using free-form rationales instead of enum codes, confusing Japan equity with Japanese government bonds, or making EUR defensive because USD was previously overweight.

### Transfer Design

As a train task, `train_003` lets solvers infer recurring allocation-view conventions for later allocation tasks: current macro signals override stale or prior positioning, prior-quarter rows establish lineage and change direction, signal magnitude controls conviction, rationale codes remain controlled enums, and cross-asset rows should be keyed by exact opportunity-set names. It is a real task rather than a worked example; the solver-visible prompt does not reveal the mapping procedure or scoring rubric, and the transfer is intended to emerge from attempting the task and comparing against this answer.
