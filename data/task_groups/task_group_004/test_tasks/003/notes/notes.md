# Q4 North America Operations Digest Notes

## Data lineage

The task is built from the ApexCloud Retention Operations API dataset in `task_group_004/env/data`. The answer uses North America Q4 A/R aging rows from `ar_aging.json`, CRM account identity from `accounts.json`, North America Q4 opportunities from `opportunities.json`, the North America Q4 HR row from `hr_summary.json`, and the Q4 `retention_summit` event row from `event_performance.json`.

## Task definition

The solver must produce a formal Q4 2026 operations digest for North America. The digest starts with customers that have A/R exposure in the older aging buckets as of 2026-12-31, ties those receivables to CRM accounts where an exact account exists, summarizes Q4 North America pipeline activity, and adds HR plus event leadership context.

## Scenario fit

This fits a Revenue Operations digest because it combines aged receivables, CRM follow-up readiness, closed and open pipeline, product-line concentration, workforce context, and retention event performance in one controlled JSON response.

## Material map

Solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The public service exposes endpoint families for finance A/R aging, accounts, opportunities, HR summaries, and event performance. No generated environment source files are copied into the payloads.

## Solution and evaluation basis

The expected solution selects North America A/R rows at `as_of=2026-12-31` where `61_90 + 90_plus` is greater than zero, computes overdue balances from those two buckets, links only exact CRM legal-name matches, and assigns `collections_followup` due on 2027-01-15. Pipeline metrics use North America opportunities with close dates from 2026-10-01 through 2026-12-31: `Closed Won` and `Closed Lost` for outcomes, all other stages for open pipeline, and open-pipeline product-line totals for the dominant product line. HR headcount and unpaid claims come from the single North America Q4 HR row; event orders and revenue come from the single Q4 `retention_summit` row.

## Transfer design

The task transfers the `train_003` pattern to a stricter regional Q4 digest: identify the receivables trigger population, validate cross-system identity by exact legal name, calculate dated pipeline metrics, and add operating context while preserving a compact JSON contract.

## Construction record

Built for `test_003` in `task_group_004`. The files created are `input/prompt.txt`, `input/payloads/answer_template.json`, `output/answer.json`, `eval/eval.sh`, and this notes file. The evaluator accepts an optional prediction path and defaults to the task's own answer.

Updated 2026-06-01: prompt wording was tightened after direct calibration showed the original phrasing made the receivables trigger and matching rule too explicit.
Updated 2026-06-01: added `task_scope` and `policy_audit` fields so scoring includes transfer-dependent source-policy and CRM matching conventions rather than only direct API aggregation.
Updated 2026-06-01: further reduced prompt cueing and expanded policy audit labels after a clean direct attempt still reconstructed most aggregates from the API. Easy aggregate weights were reduced and transfer-dependent policy weights retained at high value.
Updated 2026-06-01: added `policy_codes` aligned with `train_003`, so post-skill solvers can transfer internal code conventions learned from train answer comparison.
Updated 2026-06-01: changed policy codes to neutral internal enum values after direct solvers inferred the earlier semantic code labels.
