---
name: crescent-finance-ops-reporting
description: Build single-JSON reports from the Crescent Finance Ops API. Use when a prompt includes `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json` and asks for a branch close package, regional management view, compensation summary or forecast, or weekly payroll review.
---

# Crescent Finance Ops Reporting

Read the memo and template first. Then fetch only the endpoints needed for the report family and return one JSON object with no prose.

## Shared workflow

1. Read `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json`.
2. Identify the report family from the required top-level keys and memo fields.
3. Use the base URL from environment access to query only the matching API endpoints.
4. Build the final object exactly in template shape. Do not add commentary, markdown, or extra keys.
5. Follow the template's rounding and ordering rules exactly. If a list is not otherwise ordered, use stable ascending IDs. Keep enums and labels verbatim.
6. Before finishing, verify that every required key is present and that derived totals reconcile.

## Family references

- [Branch close and regional reporting](references/branch-close.md)
- [Compensation summaries and forecasts](references/compensation.md)
- [Weekly payroll review](references/payroll.md)
