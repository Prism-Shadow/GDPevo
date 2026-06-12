# Q3 Receivables And Pipeline Operations Review Notes

## Data lineage

The task is built from the ApexCloud Retention Operations API dataset in `task_group_004/env/data`. The answer uses A/R aging rows from `ar_aging.json`, CRM account identity from `accounts.json`, pipeline rows from `opportunities.json`, all-region HR context from `hr_summary.json`, and `apex_connect` event context from `event_performance.json`.

## Task definition

The solver must produce a Q3 2026 operations review for all regions. The review starts with customers that have A/R exposure in the older aging buckets as of 2026-09-30, then summarizes CRM opportunities with close dates from 2026-07-01 through 2026-09-30, and adds HR plus event operating context.

## Scenario fit

This fits a Revenue Operations closeout review because it combines collections follow-up volume, CRM linkage quality, pipeline outcomes, open pipeline exposure, workforce context, and event performance in one controlled JSON output.

## Material map

Solver-visible materials are the prompt and `answer_template.json`. The public service exposes endpoint families for finance A/R aging, accounts, opportunities, HR summaries, and event performance. No generated source files are copied into the payloads.

## Solution and evaluation basis

The expected solution selects A/R rows at `as_of=2026-09-30` where `61_90 + 90_plus` is greater than zero, computes overdue balances from those two buckets, links only rows that correspond to CRM accounts, and assigns `collections_followup` due on 2026-10-15. Pipeline metrics use opportunities with close dates inside Q3 2026: Closed Won and Closed Lost for outcomes, all other stages for open pipeline, and product-line aggregation for the top open product line. HR headcount and unpaid claims are summed across all Q3 rows; event orders and revenue come from the single `apex_connect` Q3 row.

## Transfer design

The task transfers to other operations-review problems by preserving the same reasoning pattern: start with a trigger population, validate cross-system identity linkage, calculate dated pipeline metrics, then add auxiliary operating context without changing the required JSON contract.
