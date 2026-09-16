---
name: credit-risk-committee
description: "Credit risk committee analysis for bank and credit union lending operations using a shared public credit office API. Supports rating migration reviews, lending-committee allocation packages, credit-union segment posture pages, watch-list stress packets with CDFI risk classes, and competing CRE decisions. Use when the user asks to prepare committee-ready credit analysis, review a branch loan portfolio with risk-rating re-derivation, allocate lending capacity across pending applications, assess a credit-union segment against NCUA benchmarks, stress-test an adverse watch list, or compare competing CRE applications. Triggers on phrases like rating migration review, lending committee, allocation package, segment posture, watch-list stress, competing CRE, FDIC benchmark, NCUA benchmark, CDFI risk class, risk rating review, credit risk committee, or when a task references a branch_id with a shared credit office API."
license: MIT
compatibility: designed for deepagents-code
---

# Credit Risk Committee

## Overview

Prepare committee-ready credit analysis for bank branches and credit-union
segments using a shared credit office public API. The API provides branch data,
loan portfolios, pending applications, sector exposures, credit policies, FDIC
and NCUA benchmark data, and credit-union segment details. All analysis is
driven by policy rules fetched from the API itself - never hard-code thresholds
or formulas.

## Quick Start

Always begin by loading the policy rules and confirming the target entity.

1. Fetch `/api/policies` to load all credit rules, factor tables, and stress
   formulas. These are authoritative for every computation.
2. If the task targets a branch (`branch_id`), fetch the branch, its metrics
   (most recent quarter at index 0), its loans, sector exposures, and
   applications as needed.
3. If the task targets a credit-union segment (`segment_id`), fetch the segment
   and the NCUA benchmark table.
4. Fetch FDIC benchmarks when the task requires NPA or CRE delinquency comparison.
5. Build the JSON answer from the bottom up: compute individual loan-level
   values first, then aggregate, then fill in composite summary objects.

## Five Committee Workflows

### 1. Rating Migration Review

Re-derive risk ratings for loans meeting a current-rating threshold, then
summarize migration, material downgrades, NPA benchmark variance, and the most
severe problem credit. See Patterns 1-4 in
[workflow_patterns.md](references/workflow_patterns.md) and
[credit_methodology.md](references/credit_methodology.md).

Key data: branch loans (filtered by `current_rating`), branch metrics
(most recent quarter), FDIC benchmark. Start by re-deriving every loan's
`final_rating` using the dominant-factor rule, then build all aggregations
from those results.

### 2. Lending Committee Allocation

Screen pending applications against fatal-issue criteria, rank the survivors,
allocate lending capacity in priority order, flag sector concentration breaches,
and produce decline reason codes. See Pattern 6 in
[workflow_patterns.md](references/workflow_patterns.md).

Key data: branch (for `lending_capacity_q1`, `sector_ceiling_pct`),
applications, sector exposures. Compute `committed_capacity_amount` as the
bank-retained share (for SBA: `approved * (1 - sba_guaranty_pct)`;
for participation: the retained portion).

### 3. Credit-Union Segment Posture

Compare a segment's state against NCUA national and peer-state benchmarks,
determine a posture recommendation, and build operating controls and escalation
triggers. See Pattern 7 in
[workflow_patterns.md](references/workflow_patterns.md).

Key data: credit-union segment, NCUA benchmark table. Compute peer median
across the named peer states (exclude the target state and US row). Compare
direction on all four metrics.

### 4. Watch-List Stress Packet

For loans with adverse ratings, assign CDFI risk classes from objective factors,
run the +200bp DSCR stress, queue workout actions, and summarize by rating/payment
buckets. See Pattern 5 in
[workflow_patterns.md](references/workflow_patterns.md).

Key data: branch loans filtered by `current_rating` threshold, policies for
CDFI factor tables and stress formula. The watch-list stress formula is
`stressed_dscr = dscr / 1.18`.

### 5. Competing CRE Decision

Compare two CRE applications with weighted CDFI scoring, CRE dual stress,
branch CRE concentration analysis, and FDIC delinquency variance. Recommend
the stronger credit with conditions and assign reason codes to the unselected
one. See Pattern 8 in
[workflow_patterns.md](references/workflow_patterns.md).

Key data: the two applications, branch loans (for existing CRE exposure),
sector exposures, FDIC benchmark. The CRE dual stress formula is
`stressed_dscr = dscr * 0.85 / 1.18`.

## API and Methodology References

- **[api_endpoints.md](references/api_endpoints.md)** - Complete API reference
  with endpoint paths, field types, and data shapes. Load this first to
  understand what data is available.
- **[credit_methodology.md](references/credit_methodology.md)** - Policy rules
  for risk-rating derivation, CDFI factor scoring, CRE weighted scoring, stress
  formulas, concentration limits, and benchmark comparison. Also covers watch-list
  action assignment and credit-union posture heuristics.
- **[workflow_patterns.md](references/workflow_patterns.md)** - Reusable
  computational patterns for each of the five committee workflows plus
  general numerical and ordering rules.

## General Rules

### Precision and Ordering

- USD exposure and currency: 2 decimal places
- Ratios: 4 decimal places unless the answer template specifies otherwise
- NCUA integer metrics (bps, pct): keep as integers
- Variance bps: 2 decimal places
- Weighted CDFI scores: 1 decimal place
- Sort lists as specified in each answer template's ordering rules

### Answer Format

- Always output valid JSON matching the requested answer template shape
- Do not include narrative text outside the JSON
- Use only enum values and identifiers allowed by the template
- Include every required key; do not omit optional keys that have data

### Data Fetching

- All API base URLs are supplied as `<TASK_ENV_BASE_URL>` by the runner
- No authentication is required
- Policy rules are always fetched fresh from `/api/policies` - never hard-code
  thresholds or assume stale values
- Use `/api/manifest` for endpoint discovery and record counts
