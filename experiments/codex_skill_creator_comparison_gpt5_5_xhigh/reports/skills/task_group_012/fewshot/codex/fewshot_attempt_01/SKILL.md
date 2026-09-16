---
name: peopleops-console-reconciliation
description: Resolve PeopleOps Console evidence-reconciliation tasks across recruitment, leave, payroll, onboarding closeout, folder/notice review, and audit-heavy case checks. Use when a prompt asks you to open the runner URL, inspect authoritative records, apply source precedence over drafts or stale summaries, and return JSON that matches a provided answer template.
---

# PeopleOps Console Reconciliation

## Overview

Use this skill for PeopleOps Console tasks that ask for a final JSON record built from the console, case detail, ledgers, policy views, messages, notices, or audits.

## Workflow

1. Read the prompt and answer template before browsing the app.
2. Open the configured runner URL, sign in with the supplied credentials, and inspect the workspace named in the prompt.
3. Use [evidence-map.md](references/evidence-map.md) to identify the authoritative source for each field family.
4. Prefer submitted, approved, or assignment-history records over draft, stale, or summary-only records.
5. Match the answer template exactly. Use the template's enum labels as written, keep arrays as IDs only, and preserve booleans and numbers exactly.
6. Exclude records outside the decision scope, especially draft records and adjacent audit events that do not directly support the final decision.
7. Return a single JSON object only.

## Output Rules

- Do not invent labels or paraphrase controlled values.
- Do not add markdown, commentary, or extra keys.
- When a template includes audit fields, include only the events that directly support the selected decision and list exclusions explicitly when requested.
