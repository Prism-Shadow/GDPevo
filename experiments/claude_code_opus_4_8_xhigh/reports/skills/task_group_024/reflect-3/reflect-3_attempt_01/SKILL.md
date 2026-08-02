# Reflect Portfolio Analytics Skill

Use the staged inputs, environment, and judge feedback only during train-time skill generation.

Core rules:
- Use only `environment_access.md` for the runtime endpoints.
- Read the prompt and answer template first.
- During train reflection, make exactly three judge submissions per train task and use the returned score/correct values to refine the next attempt.
- Do not include judge instructions in test-time solving.
- Filter with authoritative status/date/duplicate fields, not mirror or legacy fields.
- Classify using signal precedence: Security, Reliability, TechDebt, then NewFeature.
- Count items, not points.
- Round percentages to one decimal place and breach/readiness values to the required precision.
- Keep exclusion lists separate from included primary sets.
