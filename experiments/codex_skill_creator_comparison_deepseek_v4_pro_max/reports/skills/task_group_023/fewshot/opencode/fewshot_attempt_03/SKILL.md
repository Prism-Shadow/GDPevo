---
name: pho-algorithmic-audit
description: Solve Public Health Observatory algorithmic transportability audits. Use when the user presents an analysis_request.json and answer_template.json referencing a PHO protocol, mentions "Public Health Observatory", "algorithmic audit", "transportability", "PHO", or a task requiring six-module statistical computation against a read-only REST API at TASK_ENV_BASE_URL, or when the prompt asks to complete a registered audit using a Web portal with controlled publication gates.
---

# PHO Algorithmic Audit Solver

This skill enables solving Public Health Observatory (PHO) registered algorithmic audits.
Every audit follows the same structure: resolve published data from a read-only REST API,
run multiple independent statistical modules exactly as specified, apply controlled
decision gates, and return a single JSON object conforming to a supplied answer template.

## Workflow

1. **Read the request and template.** The workspace contains `analysis_request.json` and
   `answer_template.json`. Read both completely. The request defines the geography,
   years, measures, cohorts, module specifications, and decision rules. The template
   defines the exact JSON structure, field names, array lengths, precision, and enum
   values the answer must match.

2. **Discover the API base URL.** The prompt text contains `<TASK_ENV_BASE_URL>`.
   Replace that token with the actual base URL before making any HTTP request.

3. **Fetch all required data.** Use the endpoints described in [references/api.md](references/api.md).
   Apply the release-resolution rules from the request: filter by effective status,
   value type, source type, and validity flags; select the greatest revision then
   latest release timestamp then lowest record ID for each entity-measure-time key.
   Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable
   — never zero-fill them.

4. **Construct cohorts in declared order.** Build each cohort (primary, balanced,
   broad, dual-source, machine-learning) from the effective completeness predicates.
   Preserve entity-code then time order in every aligned array. When a cohort excludes
   entities, report them sorted ascending.

5. **Execute modules in declared order.** The request lists modules in a specific
   sequence. Complete each one fully before moving to the next. Every module is
   self-contained: it uses its own cohort, hyperparameters, and random state.
   For detailed implementations of each statistical method, see
   [references/methods.md](references/methods.md).

6. **Apply decision gates on unrounded values.** After all modules are complete,
   evaluate each business predicate on unrounded computed values. Count passing gates
   and select the classification from the request's controlled decision mapping.
   Report every gate's PASS/FAIL status in the declared module order.

7. **Format the answer.** Follow [references/formatting.md](references/formatting.md)
   precisely. The answer template is the contract — every key, array length, order,
   precision, enum value, and type must match. Submit exactly one JSON object with
   no narrative outside it.

## Core Principles

**Never carry values across invocations.** Every audit recomputes all evidence from
the effective request and the portal. The same protocol ID may be used with different
years, measures, geographies, or thresholds — recompute everything from scratch.

**Preserve every declared order.** Entity codes, feature lists, cluster groups, time
periods, grid values, and checkpoint intervals must appear in the exact order declared
by the request. When the template says "ascending ASCII" or "ascending state code",
sort accordingly. Never sort aligned result arrays independently of their companion
identifier arrays.

**Respect the information boundary.** Use only the portal API endpoints listed in the
environment access. No credentials are needed. Do not access endpoints not listed.

**Precision rules.** Report non-integer statistics to the decimal places declared
by the request (typically 4). Use JSON null only when a value is mathematically
unavailable (e.g., a t-statistic when the standard error is exactly zero). Never
use NaN, Infinity, or string representations of numbers.

**PRNG determinism.** Every random module uses a specific seed/stream declared in
the request. Implement the generator exactly as specified — do not substitute
library RNGs. Record checkpoints at the declared replicate numbers without
resetting the stream.

**Complete every module before deciding.** Even if an early gate would fail, all
modules must produce their full evidence. The decision module evaluates all gates
and picks the first failed module by precedence only for reporting.

## Quick Reference

| Concern | Reference |
|---|---|
| API endpoints, filtering, release resolution | [references/api.md](references/api.md) |
| Ridge, elastic net, FE, GMM, bootstrap, PCA, clustering, conformal, sensitivity, Shapley | [references/methods.md](references/methods.md) |
| JSON precision, ordering, null rules, enum values | [references/formatting.md](references/formatting.md) |
