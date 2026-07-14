# ClinicProtocol Decision-Support Skill

## Overview

This skill covers structured clinical decision-support tasks served through a remote ClinicProtocol API. Every task follows a common pattern: fetch the relevant protocol card, pull patient/encounter/observation data from the API, apply protocol rules to the data, and return a single JSON object matching the supplied answer-template schema.

## Environment

- **Base URL**: `http://34.46.77.124:9016` (set as `GDPEVO_ENV_BASE_URL`; do NOT use localhost).
- All data lives behind the remote HTTP API — never read local source files.

## General Workflow

1. **Identify the protocol** — the task prompt names the clinical scenario; the answer template's `primary_protocol` enum pins the exact protocol code (e.g. `HEAD_INJURY_2026`, `RESP_ACUTE_2026`). Start by fetching that protocol card from the API to get the decision rules.
2. **Fetch patient data** — query the API for the patient record (`patient_id` from the prompt). Understand demographics, problem list, medications, allergies, recent encounters.
3. **Fetch encounter/observation data** — pull the encounter if one is named, then pull all relevant Observation resources for that patient. Filter carefully (see Observation Discrimination below).
4. **Apply protocol rules** — map the protocol's decision logic onto the patient+encounter data. Most protocols are deterministic: a given set of findings maps to one correct risk level, disposition, dose, etc.
5. **Assemble the answer** — fill every required field from the answer template, using only values from the template's allowed enums. Sort all string lists lexicographically.

## API Usage Habits

- Protocol cards are fetched by their protocol code (e.g. `GET /protocols/HEAD_INJURY_2026`). Read the card fully before making any decisions — it contains thresholds, exclusion criteria, and step-by-step logic.
- Patient resources are fetched by patient ID. Observations are filtered by patient, LOINC code, date range, and status.
- When a task asks about a specific time window (e.g. "May 2026"), constrain queries to that window exactly.
- When a task provides a "current clinical time," use it as the reference point for recency checks, follow-up scheduling, and ignoring stale data.

## Output Field Conventions

### Always present
- `patient_id` — exact string from the prompt or API response.
- `primary_protocol` — the protocol code; must match the single allowed value in the template's enum.
- `case_id` — present when the task involves a specific encounter or case; use the exact ID from the prompt.

### Lists
- All string lists must be **sorted lexicographically** (standard string sort, case-sensitive). The answer template confirms this with `"ordering": "sort_lexicographic"`.
- Empty lists should use `[]`, never `null` or a missing key.
- List items must come from the template's `items_enum` — never invent values.

### Enums
- Every categorical field is backed by an explicit `allowed` list in the answer template. Use only those exact strings — same case, same underscores.

### Dates and times
- Full timestamps: ISO-8601 with timezone offset (e.g. `2026-07-06T09:00:00-05:00`).
- Date-only: `YYYY-MM-DD` (e.g. `2026-05-02`).
- Month-only: `YYYY-MM` (e.g. `2026-05`).

### Evidence IDs

The `evidence_ids` field (when required by the template) lists the stable resource IDs that directly support the decision. Follow these rules:

- **Include** the encounter/case ID when the decision is tied to a specific encounter.
- **Include** observation IDs that provided the critical values used in the decision (e.g. the GCS score that triggered a red flag, the CXR that confirmed consolidation, the final potassium result that determined the dose).
- **Exclude** preliminary, erroneous, wrong-LOINC, and superseded/old observations — these belong in exclusion lists (e.g. `ignored_observation_ids`, `excluded_observation_ids`), not in evidence.
- **Sort** evidence_ids lexicographically like any other string list.

When the answer template does NOT include `evidence_ids` in its required keys, omit the field entirely.

## Observation Discrimination

Observation resources from the API often include distractors. Filter methodically:

1. **Status** — use only `final` Observations for clinical decisions. Preliminary, amended, entered-in-error, and cancelled statuses are not decision-grade and should be excluded/ignored.
2. **LOINC code** — confirm the observation's code matches the expected LOINC for the analyte being assessed. Observations with different LOINC codes (even if the display name looks similar) are wrong and must be excluded.
3. **Recency** — when the protocol specifies a lookback window, ignore observations outside it. An old final result may be valid data but not applicable to the current decision.
4. **Value plausibility** — if a value is obviously erroneous (e.g. impossible physiological value, mismatched units), exclude it.

Excluded observations should be recorded in the appropriate exclusion list (`ignored_observation_ids` or `excluded_observation_ids`) when the template requires one. This demonstrates that they were seen and deliberately filtered out.

## Decision Rules

- Protocol cards are deterministic decision trees. Given the same inputs, the same outputs are always correct. There is no probabilistic or "best judgment" variation — follow the protocol logic exactly.
- When the protocol defines thresholds (e.g. potassium < 3.5 mEq/L → replace), use the **latest final** value to determine which branch applies.
- Risk stratification is cumulative: count all applicable risk factors/red flags present, then map the count to the risk level per the protocol.
- Contraindications are driven by patient-level data (allergies, comorbid conditions, current medications) combined with protocol rules.

## Common Pitfalls

1. **Using preliminary/erroneous observations as evidence** — always check status. Only `final` counts.
2. **Including wrong-LOINC observations** — verify the LOINC code, not just the display name.
3. **Missing exclusions** — when the template has an exclusion list, populate it with every observation you reviewed and rejected, with the reason implied by the ID.
4. **Wrong date arithmetic** — when scheduling follow-up labs, respect the "current clinical time" and the protocol's timing rules (e.g. "next morning" means the following calendar day at the standard morning lab draw time).
5. **Inventing enum values** — if a patient finding doesn't match any `items_enum` entry, it doesn't go in the list. Only use values present in the template's allowed lists.
6. **Case sensitivity** — protocol codes, enum values, and IDs are case-sensitive. `HEAD_INJURY_2026` ≠ `head_injury_2026`.
7. **Forgetting lexicographic sort** — lists that are correct in content but unsorted will fail validation. Sort last, after you've finalized the item set.
8. **Omitting required top-level keys** — the template's `required_top_level_keys` is authoritative. Every key listed there must appear in the output, even if its value is an empty list.
