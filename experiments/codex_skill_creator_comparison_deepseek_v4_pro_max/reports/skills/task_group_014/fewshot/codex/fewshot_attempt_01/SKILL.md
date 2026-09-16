---
name: northstar-payer-operations
description: Northstar Health Plan payer operations task solver. Use when working on Northstar utilization management determinations, pharmacy coverage appeals, payment integrity claim repricing, peer-to-peer summaries, or therapy margin queue analysis. Connects to the shared Northstar payer environment (HTTP API + SQL endpoint) to gather case records, policies, documents, rate schedules, appeals, and service margin data for structured determinations.
---

# Northstar Payer Operations

Solve Northstar Health Plan payer operations tasks by connecting to the shared environment, querying business records, and returning structured JSON determinations.

## Connection

Every Northstar task uses the same environment. See [environment.md](references/environment.md) for the base URL, SQL endpoint, and bearer token. Read that file before making any network call.

## General Workflow

1. Read the task prompt and payloads for the target business ID, role, reporting date, and domain.
2. Read the answer template for the exact required JSON shape — every field, enum constraint, and ordering rule in the template is binding.
3. Query the environment for all relevant business records using both REST endpoints and SQL.
4. Apply the business rules for the task domain (see [workflow_patterns.md](references/workflow_patterns.md)).
5. Form the structured JSON, filling every required field exactly as the template specifies.
6. Complete the basis_audit object per the rules in [basis_audit.md](references/basis_audit.md).

## Data Model and Records

The Northstar environment exposes cases, policies, documents, appeals, claims, rate schedules, service margins, drug trials, and authorizations. See [business_records.md](references/business_records.md) for record relationships and query guidance.

## Determination Logic

- Compare active clinical records against stale exports: prefer current records.
- For appeal tasks, payer appeal evidence takes precedence over manufacturer assistance.
- For payment integrity, match rate schedules by plan modifier and effective date.
- For P2P tasks, new patient-specific information from the P2P event controls.
- For margin analysis, classify below-threshold rows first, then flag charge-sensitive rows.

## basis_audit

Every Northstar determination includes a basis_audit object with four required keys. The full rules, source-precedence values, and ordering conventions are in [basis_audit.md](references/basis_audit.md).

## Task-Type Guidance

Detailed patterns for each task type are in [workflow_patterns.md](references/workflow_patterns.md):

- UM nurse determination — PT criteria, document classification, authorization
- Pharmacy appeal disposition — appeal routing, drug trials, manufacturer assistance
- Payment integrity repricing — benchmark selection, line corrections, recovery amounts
- Peer-to-peer summary — P2P outcome, unresolved criteria, appeal deadlines
- Margin queue analysis — threshold classification, charge sensitivity, gap calculation
