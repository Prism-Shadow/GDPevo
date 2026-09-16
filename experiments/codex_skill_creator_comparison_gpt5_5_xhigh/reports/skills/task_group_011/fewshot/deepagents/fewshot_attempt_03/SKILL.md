---
name: credit-office-committee
description: Prepare committee-ready JSON credit-office answers from the public task API. Use for branch risk-rating migration, pending loan allocation, credit-union segment posture, adverse-rated watch-list stress, and competing CRE application decisions that must follow a supplied answer_template.json.
---

# Credit Office Committee

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json`; treat the template's keys, enum values, ordering, and precision as the output contract.
2. Get the API base URL from `TASK_ENV_BASE_URL` or the prompt. Query only the public credit-office endpoints named in the environment note.
3. Fetch `/api/policies` first. Use its risk-rating thresholds, CDFI factor scores, CRE weights, stress formulas, concentration rules, and benchmark versions instead of inventing thresholds.
4. Fetch the target branch or segment records and the relevant benchmark table. Recompute all numbers from API data; do not use local cached data or example answers.
5. Return only valid JSON matching the template. Sort lists exactly as requested and round currency to 2 decimals, ratios to 4 decimals, basis points to 2 decimals, and weighted CRE scores to 1 decimal unless the template says otherwise.

## Helper Script

Use [scripts/credit_committee.py](scripts/credit_committee.py) for deterministic drafts:

```bash
python3 skill/scripts/credit_committee.py rating-migration --branch BRANCH_ID --review-date YYYY-MM-DD --current-rating-min 3
python3 skill/scripts/credit_committee.py allocation --branch BRANCH_ID
python3 skill/scripts/credit_committee.py segment-posture --segment SEGMENT_ID
python3 skill/scripts/credit_committee.py watchlist-stress --branch BRANCH_ID --adverse-rating-min 6
python3 skill/scripts/credit_committee.py competing-cre --branch BRANCH_ID --applications APP_ID APP_ID
```

Add `--base-url "$TASK_ENV_BASE_URL"` if the environment variable is not set. The helper prints JSON to stdout. Before finalizing, compare its keys to the task template and adjust any task-specific field names or requested subsets.

## Reusable Rules

- **Risk-rating migration:** Re-derive each target loan's final rating as the worst numeric rating from available DSCR, LTV, and payment-status delinquency factors. If no objective factor is available, retain the current rating. Material downgrades are loans where `final_rating - current_rating` is at least the policy notch threshold. Follow-up coverage normally starts at final rating 6: rating 6 to `watchlist`, rating 7 to `special_assets`, and rating 8 or nonaccrual/projected-loss cases to `partial_chargeoff_review`.
- **NPA and FDIC variance:** Use the latest branch metrics row. `branch_npa_ratio = nonperforming_loans / total_loans_outstanding`; variance is branch ratio minus the requested FDIC benchmark metric.
- **Watch-list stress:** For adversely rated loans, compute CDFI factor score from available LTV, debt-to-asset, FICO, and liquidity fields. Use policy score bands; classify underwater nonaccrual or rating-8 credits as `Projected Loss` even if the numeric factor score is lower. Apply the policy watch-list stress formula only where DSCR is present.
- **Allocation packages:** Separate gross approved amount from bank capacity used. SBA guarantees reduce bank capacity used; participations reduce retained bank exposure. For sector concentration reporting, use gross approved exposure over `latest_total_loans + gross_approved_amount`. For retained participation sizing, solve the sector limit with retained bank exposure over `latest_total_loans + committed_capacity_amount`.
- **Competing CRE:** Use the policy CRE dual-stress formula, CRE policy concentration limit, FDIC real-estate delinquency benchmark, and weighted five-factor score. Lower weighted score is stronger. Concentration or benchmark underperformance becomes controlled reason-code treatment and usually pushes the selected path to `participation_required` or `conditional_approve`.
- **Credit-union segments:** Pull the segment endpoint plus NCUA benchmark rows. Compare the state to US and to the median of listed peer states. Higher delinquency or loan-to-share is weaker; higher ROAA or positive-net-income percentage is stronger. Map control issues, missing lien/insurance checks, staffing constraints, benchmark weakness, and capacity pressure to the allowed control and escalation enums.
