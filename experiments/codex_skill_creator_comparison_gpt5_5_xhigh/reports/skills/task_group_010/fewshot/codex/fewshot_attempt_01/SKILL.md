---
name: asteria-portfolio-decisions
description: Use when an Asteria Investment Office task needs live environment lookup and a strict JSON answer for credit trades, correlation reviews, allocation views, or committee risk decisions.
---

# Asteria Portfolio Decisions

Use this skill for Asteria Investment Office prompts that ask for a strict JSON output after checking the shared environment. Typical signals are a portfolio id, a stale worksheet warning, index-level correlation work, allocation views, or credit rotation/trade packages.

## Workflow

1. Read `prompt.txt`, the payload files, and the answer template first.
2. Treat live environment records as authoritative over local notes when they conflict.
3. Load only the live endpoints needed for the task. See [Asteria workflow reference](references/asteria-workflow.md).
4. Compute the requested numbers from the live data.
5. Return JSON only, matching the template exactly.

## Output Rules

- Use the template's field order, enums, list order, and numeric precision.
- Keep identifiers sorted when the schema says to.
- Use the common `as_of_date` from live records, not a stale local note.
- For a precedence field, choose `current_environment_over_stale_payload` when the prompt says the local worksheet may be stale.
- Do not add commentary, markdown, or extra keys.

## Common Patterns

- Credit trade and rotation tasks: choose from current holdings and candidate bonds, check issuer watchlist status, respect HY and duration constraints, and avoid watchlist buys when asked.
- Correlation tasks: convert monthly levels to simple returns, then compute Pearson correlation on aligned return series.
- Allocation tasks: map macro signal scores to views using the policy thresholds in the reference and use prior views to compute the change.
- Committee tasks: combine the correlation result with allocation views and pick actions that match the requested sleeve role.
