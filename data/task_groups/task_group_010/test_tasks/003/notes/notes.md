# test_003 Notes

## English

### Data and Source Lineage

This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk`, with source-example lineage from `E003` quarterly active allocation views and secondary scenario support from the cross-asset currency handling in `E002` and `train_005`. The task uses the shared Asteria Investment Office environment, especially `env/data/opportunity_sets.json`, `env/data/prior_views.json`, `env/data/macro_signals.json`, and `env/data/policies.json`. The solver-visible local files are `input/prompt.txt`, `input/payloads/allocation_request.json`, and `input/payloads/answer_template.json`.

The rework was requested after direct calibration scored `0.852941` avg@2, which showed that the original prompt and broad rubric made the task too easy without train-derived allocation experience.

### Task Definition and Scenario Fit

The solver acts as a CIO-desk analyst updating Q3 2026 active allocation views across equities, fixed income, and currencies for a global multi-asset reference model. The expected answer is a normalized JSON object with task lineage, fifteen active allocation rows, a USD-base currency overlay, and three controlled cross-asset judgment enums.

This task fits the group because it is an institutional allocation refresh: the solver must coordinate macro signals, opportunity-set taxonomy, prior-quarter records, controlled rationale codes, and currency-overlay decisions. It stays within the active allocation view family while mixing equity regional views, duration and credit views, and currency views.

### Material Map

`input/prompt.txt` gives the business request without listing endpoint names or a procedural source-mapping checklist. `allocation_request.json` names the target quarter, prior quarter, requested opportunity sets, currency overlay universe, and controlled enum choices for the output. `answer_template.json` defines the exact solver-visible JSON contract, including prior-view lineage, current signal scores to three decimals, rationale-code enums, overlay decisions, and cross-asset judgment choices.

In the shared environment, `opportunity_sets.json` supplies asset classes, `prior_views.json` supplies the prior-quarter lineage records for the target refresh, `macro_signals.json` supplies current Q3 scores and rationale codes, and `policies.json` supplies the as-of date, policy set id, and allocation mapping policy id.

### Solution and Evaluation Basis

The standard answer is derived from the current shared environment. For each requested opportunity set, the answer records the prior view from the Q3 refresh lineage record, the Q3 macro signal score, the final active view, the change versus the prior view, conviction, and the controlled rationale code. The Q3 final views are: U.S. Large Cap `N`, U.S. Small Cap `OW`, Europe `OW`, Japan `N`, Emerging Markets `UW`, India `OW`, Latin America `OW`, U.S. Treasuries `OW`, German Bunds `OW`, Corporate Investment Grade `OW`, Corporate High Yield `UW`, USD `UW`, EUR `OW`, JPY `UW`, and CHF `N`.

The USD-base currency overlay is `reduce_dollar_beta`: reduce USD exposure, add EUR exposure, reduce JPY exposure, and hold CHF exposure. The cross-asset judgments prefer small-cap, Europe, India, and Latin America over U.S. Large Cap and broad EM; prefer duration and investment-grade credit over high-yield beta; and express the currency bias as reducing USD, adding EUR, reducing JPY, and holding CHF.

The evaluator has nine exact-match scoring points with raw weights: task and policy lineage weight 2; prior-view and signal-score lineage weight 3; core equity view rows weight 2; diversifier equity view rows weight 2; fixed-income view rows weight 2; currency view rows weight 2; controlled rationale codes weight 3; currency overlay weight 3; cross-asset judgment enums weight 2. Row checks are keyed by `opportunity_set`, and overlay checks are keyed by `currency`, so incidental list order does not determine correctness.

Likely pitfalls include using the Q3 prior-view record as the final answer, comparing against Q1 rather than Q2 lineage, omitting current signal scores, treating rationale as free text, collapsing the currency overlay into the allocation rows only, or choosing broad equity/rates-credit stance enums from isolated view labels rather than the mixed opportunity-set pattern.

### Transfer Design

This is a test task. `train_003` anchors the allocation-view conventions: current signals drive active views, prior-quarter records drive change direction, signal magnitude controls conviction, and rationale codes remain controlled enums. `train_005` anchors currency handling inside a cross-asset committee workflow and the habit of turning mixed opportunity-set evidence into controlled action enums.

The rework increases transfer dependence by removing endpoint and workflow leakage from the prompt, requiring row-level prior-quarter lineage, adding signal-score evidence, splitting scoring across equity subgroups, fixed income, currencies, and rationale style, and adding a currency overlay plus cross-asset judgment block. A direct solver can still solve the task fairly from the shared environment, but it must reconstruct the active-allocation conventions rather than follow an explicit prompt recipe.

### Construction Record

Author: task-builder 8, reworked by calibration maintainer. Created: 2026-06-03. Updated: 2026-06-03. Major changes: reduced solver-visible procedural leakage; expanded `answer_template.json`; updated `answer.json`; replaced the evaluator with nine targeted scoring points; updated `task_group.yaml` rubric; refreshed notes.

