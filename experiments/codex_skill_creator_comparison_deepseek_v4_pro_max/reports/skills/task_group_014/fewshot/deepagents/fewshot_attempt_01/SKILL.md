---
name: northstar-payer-ops
description: "Northstar Health Plan payer operations structured determination workflows. Use when working as a Northstar payer operations role (UM nurse reviewer, pharmacy appeals coordinator, payment integrity analyst, peer-to-peer coordinator, or UM-finance analyst) to produce structured JSON determinations against the Northstar task environment. Supports five business domains: (1) prior authorization UM nurse determination, (2) pharmacy coverage appeal and assistance intake, (3) claim repricing and payment integrity correction, (4) peer-to-peer discussion finalization, (5) therapy margin queue analysis. Uses REST business endpoints and a bearer-token SQL endpoint. Triggers on Northstar case IDs, appeal IDs, claim IDs, or payer ops role names with a bearer-token SQL environment."
license: MIT
compatibility: designed for deepagents-code
---

# Northstar Payer Operations

Produce structured JSON determinations for Northstar Health Plan payer operations against the shared task environment. The environment exposes REST business endpoints and a SQL endpoint.

## Environment Setup

Connect to the task environment using the base URL provided in your task. See [references/environment.md](references/environment.md) for the full endpoint catalog and bearer-token SQL query construction.

Do not inspect environment source files, database files, or generated data directly. Use only the provided endpoints.

## General Rules

### Output format

Return exactly one JSON object. No markdown, comments, or prose outside the JSON. Match the answer template shape exactly -- do not add extra top-level keys.

### basis_audit trail

Every determination must include a `basis_audit` object with four required keys:

- `source_precedence`: exactly one of the six precedence rules below, chosen by business domain
- `precedence_record_order`: all controlling and exception records in source-precedence order, highest priority first
- `controlling_record_ids`: records that directly control the result
- `exception_record_ids`: records explaining gaps, exclusions, denials, or missing information

See [references/basis-audit.md](references/basis-audit.md) for the complete source-precedence rules, ordering conventions, and domain mapping.

### Document handling

- Use the freshest available clinical or financial records. Stale records go in `excluded_documents`, `exception_record_ids`, or `stale_source_rejected` depending on the domain template.
- List document IDs and record IDs in the order specified by the answer template (typically ascending ID or operational evidence order).

### Numeric and date conventions

- Currency: JSON numbers in dollars, rounded to two decimal places
- Numeric ratios: four decimal places
- Dates: ISO 8601 YYYY-MM-DD
- Modifiers: use `null` when absent, never an empty string
- List ordering: follow the answer template ordering rule for each list

## Business Domains

### 1. UM Nurse Prior Authorization Review

Review a prior authorization case against policy criteria and produce a determination summary. See [references/um-nurse-review.md](references/um-nurse-review.md).

### 2. Pharmacy Coverage Appeal and Assistance Intake

Process a coverage-exception appeal and manufacturer assistance intake screen. See [references/pharmacy-appeals.md](references/pharmacy-appeals.md).

### 3. Payment Integrity Claim Repricing

Reprice a paid claim against the current benchmark schedule and produce a correction packet. See [references/payment-integrity.md](references/payment-integrity.md).

### 4. Peer-to-Peer Discussion Finalization

Finalize a completed peer-to-peer discussion and produce the structured P2P summary for the authorization file. See [references/peer-to-peer.md](references/peer-to-peer.md).

### 5. Therapy Margin Queue Analysis

Analyze a therapy service margin queue and classify payer-service rows for action. See [references/margin-analysis.md](references/margin-analysis.md).
