---
name: cedar-ridge-intake
description: "Healthcare intake coordination workflow for processing patient rosters, referral batches, transfer reviews, and chronic-care enrollment panels against the Cedar Ridge Intake Coordination Portal API. Use when the task involves: (1) verifying patient access or insurance, (2) auditing referral readiness or chart activation, (3) reviewing dialysis or other transfer packets, (4) preparing chronic-care enrollment panels, (5) any batch workflow that follows a JSON answer template with controlled vocabularies, or (6) tasks referencing the Cedar Ridge Intake Coordination Portal or a task environment base URL with patients/referrals/transfers/chart endpoints."
compatibility: designed for deepagents-code
---

# Cedar Ridge Intake Coordination

## Overview

This skill covers batch healthcare intake workflows against the Cedar Ridge Intake Coordination Portal REST API. Every task follows the same pattern: fetch data from multiple endpoints, reconcile records, apply deterministic business rules, and produce a JSON answer that conforms to a provided answer template.

## Core Workflow

Follow these steps in order for every intake task:

### 1. Orient from the answer template

Read the answer template first. It defines:
- The required top-level keys and their types
- Every allowed enum value for every field
- Ordering rules for lists (usually ascending by ID)
- Which fields treat arrays as unordered sets

Never use a value outside the template's allowed enums. Never guess ordering.

### 2. Fetch all relevant data

Use the portal base URL from the task prompt. Hit the endpoints described in [API Endpoints](references/api_endpoints.md). Common patterns:

- For roster tasks: fetch patients, their charts, insurance/referral data, pharmacy lookups, and ICD codes
- For referral audits: fetch all referrals in the batch, then each referral's patient, chart, documents, and ICD codes
- For transfer reviews: fetch transfers, patients, documents, and capacity data
- For enrollment panels: fetch program candidates, then each candidate's chart and clinical history

Fetch in parallel where endpoints are independent. Use `POST /query` for complex multi-table reconciliations.

### 3. Reconcile records

Cross-reference entities by their IDs. Common reconciliation patterns are in [Business Rules](references/business_rules.md). Key checks:

- Compare referral ICD chapters against expected chapters for the service line
- Detect duplicate referrals for the same patient
- Flag shared insurance IDs across different patients
- Check document completeness against required document lists
- Check document freshness against staleness limits
- Verify authorization status
- Assess risk factors from chart and patient data

### 4. Apply business rules

Use the rules in [Business Rules](references/business_rules.md) to determine:

- Registration/intake status for each entity
- Blocker and reason codes
- Priority tiers and follow-up cadences
- Next-contact owner and route
- Chart activation needs

Every rule is deterministic: given the same inputs, the same outputs must result.

### 5. Build and validate the output

Construct the JSON answer following [Output Conventions](references/output_conventions.md). Validate:

- Every list is sorted as the template requires
- Every enum value is from the template's allowed set
- Unordered-set arrays have consistent but arbitrary ordering
- All counts in summaries match the per-entity results exactly
- No prose outside the JSON

## Key Principles

- **Template-driven**: The answer template is authoritative for output shape and allowed values. Defer to it always.
- **Deterministic rules**: Business logic is rule-based, not judgment-based. Same inputs always produce same outputs.
- **Ascending ID order**: Unless the template says otherwise, sort lists ascending by their primary ID field.
- **Unordered sets**: Reason codes, issue codes, and blocker codes are sets. Order is not meaningful, but be consistent.
- **Count accuracy**: Every count in a summary must equal the number of entities in the corresponding state.
- **JSON only**: Final output must be pure JSON. No explanatory prose, no markdown wrapping.
