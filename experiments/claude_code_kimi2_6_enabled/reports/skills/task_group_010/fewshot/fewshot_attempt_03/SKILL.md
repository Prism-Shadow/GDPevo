# Skill: Structured Financial Portfolio JSON Generation

## Purpose
Generate strictly-schema-compliant JSON answers for portfolio analysis, risk review, and allocation committee tasks. Input always contains a prompt, data payloads, and an `answer_template.json` that serves as the schema contract.

## Prerequisites
- Read `/workspace/environment_access.md` for any environment URL overrides.
- Read `input/prompt.txt` to understand the high-level request.
- Read **all** files under `input/payloads/` — there may be multiple JSON data sources.
- Read `input/payloads/answer_template.json` — this is the **schema contract**, not a fill-in-the-blanks form.

## Step-by-Step Procedure

### 1. Discovery — Load All Inputs
Read every file in `input/payloads/` before performing any calculation. Data sources may include:
- Raw index level histories (`index_levels`)
- Correlation matrices (`correlation_matrix`)
- Risk metric tables (`risk_metrics`)
- Carry/momentum/volatility signals (`carry`, `momentum`, `vol_z`)
- Prior views and constraints (`prior_views`, `constraints`)
- Meeting memos or review requests

### 2. Schema Extraction — Parse `answer_template.json`
The `answer_template.json` defines the exact output contract. Extract the following for **every** required top-level key:
- `type`: string, number, list, boolean, enum
- `required_value`: if present, the exact literal value required (e.g., `"PF-MA-HELIO"`, `"Q2_2026"`)
- `format`: e.g., `"YYYY-MM-DD"`
- `length`: for lists, exact expected count
- `item_order`: for lists, the exact ordering of items by a discriminant field (e.g., `opportunity_set` or `pair_role`)
- `allowed_values`: for enums, the closed set of permitted strings
- `precision`: for numbers, decimal places (typically 3)
- `calculation`: human-readable formula or method (e.g., "Pearson correlation of monthly simple returns", "signal_score = (carry + mom + vol_z) / 3")
- `ordering_rule`: special sorting rules (e.g., "Index ids within each pair must be sorted alphabetically")

### 3. Calculation — Derive Each Field from Payload Data
Perform calculations **exactly** as specified in the template. Common patterns:

#### Correlation from Index Levels
- Compute **monthly simple returns**: `(level_t / level_{t-1}) - 1` for consecutive months.
- Compute **Pearson correlation** between two return series.
- Round to the `precision` specified (usually 3 decimal places).
- For pair fields, **sort index IDs alphabetically** before placing them in the list.

#### Signal Scores
- Formulas like `signal_score = (carry + mom + vol_z) / 3` are common.
- Round to specified precision.

#### Z-Scores
- `z_score = (value - mean) / std_dev` across the cross-section of assets.
- Round to specified precision.

#### Rankings
- Rank assets by a computed metric (e.g., signal_score, z_score).
- `rank` is typically 1-based.

#### View Determination (UW / N / OW)
- Compare signal_score against thresholds or cross-sectional rankings.
- `change` is derived by comparing the new `view` against `prior_view`:
  - Same → `"UNCHANGED"`
  - Higher (e.g., UW → N, N → OW) → `"UP"`
  - Lower (e.g., OW → N, N → UW) → `"DOWN"`

#### Rebalance Trigger & Next Step
- These are enums. Select the value that matches the narrative in the prompt and data.
- `rebalance_trigger` examples: `correlation_cap_breach`, `hy_cap_pressure`, `duration_drift`, `watchlist_concentration`, `committee_review`.
- `next_step` examples: `approve_rotation`, `defer_pending_risk_review`, `approve_with_monitoring`, `reject_constraint_breach`.

#### Boolean Flags
- `portfolio_risk_concentration_flag`: set based on whether any correlation or concentration metric exceeds a threshold described in the prompt or evident from the data.

### 4. Assembly — Build the Output JSON
- Include **all** `required_top_level_keys` in the exact order specified (or at minimum, ensure none are missing).
- For list fields, order items exactly according to `item_order` in the template.
- Use **only** values from `allowed_values` for enum fields.
- Format dates as `YYYY-MM-DD`.
- Ensure numbers match the specified `precision`.
- Ensure string fields with `required_value` match exactly.

### 5. Validation — Self-Check Before Writing
Run a mental checklist against the template:
- [ ] All `required_top_level_keys` present?
- [ ] All enum values in `allowed_values`?
- [ ] All list lengths match `length`?
- [ ] All list items in `item_order` sequence?
- [ ] All numbers rounded to `precision`?
- [ ] All `required_value` fields exact?
- [ ] Date format correct?
- [ ] Pairs alphabetically sorted where required?

## Common Pitfalls
- **Ignoring `answer_template.json`**: The prompt alone is insufficient; the template is the authoritative schema.
- **Wrong list ordering**: `item_order` is strict. Re-ordering items will fail validation.
- **Missing precision**: Financial metrics typically require 3 decimal places. Do not truncate or over-round.
- **Alphabetical pair sorting**: Index IDs inside correlation pairs must often be sorted alphabetically, even if the prompt mentions them in a different order.
- **Enum values**: Inventing rationale codes or trigger names that are not in `allowed_values` will fail.
- **Skipping payloads**: Some tasks have multiple payload files; missing one leads to incomplete calculations.

## Example Workflow Summary
1. `Read input/prompt.txt` → understand narrative.
2. `Read input/payloads/answer_template.json` → extract schema contract.
3. `Read input/payloads/*.json` → load all data.
4. Compute correlations, signal scores, z-scores, rankings, views per template rules.
5. Assemble JSON with exact keys, ordering, enums, and precision.
6. Write to `output/answer.json`.
