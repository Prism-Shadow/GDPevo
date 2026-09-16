# Risk Scoring Methodology

## Account-Level Risk Score

Each account receives a composite risk score derived from six signal categories. Scores are integers.

### Signal Categories

| Category | Max Points | Signals |
|---|---|---|
| **Renewal Pressure** | 25 | renewal_date within 3 months of assessment date |
| **Revenue Exposure** | 20 | Higher ARR = higher exposure; current_arr from billing snapshot |
| **NPS Sentiment** | 15 | Latest NPS < 50, or NPS decline >= 10 pts |
| **Support Health** | 15 | SLA misses (first-response or resolution), or avg compliance < 90% |
| **Usage Trend** | 15 | product_usage declining across the period |
| **A/R & Tenure** | 10 | Overdue balance > 0, or tenure <= 24 months with risk signals |

### Scoring Rules

**Renewal Pressure (0-25):**
- renewal_date <= assessment_date + 90 days AND renewal_date > assessment_date: +25
- renewal_date > assessment_date + 90 days: +10
- renewal_date already past: +5 (missed renewal)

**Revenue Exposure (0-20):**
- current_arr >= 1,000,000: +20
- current_arr >= 500,000: +15
- current_arr >= 200,000: +10
- current_arr >= 100,000: +5
- current_arr < 100,000: +0

**NPS Sentiment (0-15):**
- Latest NPS < 30: +15
- Latest NPS < 50: +10
- NPS declined >= 10 points between consecutive completed surveys (even if latest >= 50): +10
- Latest NPS >= 50 and stable: +0

**Support Health (0-15):**
- >= 3 SLA-missed tickets (first_response OR resolution): +15
- 1-2 SLA-missed tickets: +10
- Average SLA compliance < 90% across 3 months: +5
- No SLA issues: +0

**Usage Trend (0-15):**
- product_usage declined > 10% from first to last month: +15
- product_usage declined 1-10%: +10
- product_usage declined < 1% or flat: +5
- product_usage increased: +0

**A/R & Tenure (0-10):**
- Overdue balance > 0 AND tenure <= 24 months: +10
- Overdue balance > 0: +5
- Tenure <= 24 months with at least one other risk signal (NPS < 50, usage decline, SLA misses): +5
- Neither: +0

### Risk Level Thresholds

| Score Range | Risk Level |
|---|---|
| >= 60 | critical |
| 40-59 | high |
| 20-39 | medium |
| < 20 | low |

## Portfolio Risk Tiers

When computing portfolio-level summaries:

- **arr_at_risk**: Sum of current_arr for all accounts with risk_level critical or high.
- **collections_count**: Number of accounts with primary_action == collections_followup.
- **technical_recovery_count**: Number of accounts with primary_action == technical_recovery.
- **critical_or_high_count**: Count of accounts with risk_level critical or high.

## Churn Model Validation

When a churn model CSV is provided:

1. Count training_rows as total rows in train.csv (excluding header).
2. Count validation_rows as total rows in validation.csv (excluding header).
3. Count feature_count as number of columns minus 2 (exclude customer_id and Churn).
4. Compute accuracy_pct as (correct_predictions / validation_rows) * 100, rounded to 1 decimal.
5. Map accuracy to accuracy_band.
6. Determine tenure_coefficient_direction: negative if longer tenure correlates with lower churn; positive if longer tenure correlates with higher churn; zero if no correlation.

Note: The train dataset is labeled with a Churn column (Yes/No). The validation dataset also includes Churn. Candidates do not include Churn.

## Expansion Pipeline

For accounts with expansion opportunities:

- **expansion_pipeline** for an account: Sum of amount for all opportunities where account_id matches, state == open, and close_date falls within the analysis period.
- **net_revenue_exposure**: arr_at_risk - open_expansion_pipeline for the portfolio.
- **open_expansion_pipeline** (portfolio-level): Sum of expansion_pipeline across all accounts in scope.

## Net Revenue Exposure

net_revenue_exposure = arr_at_risk - open_expansion_pipeline

## Segment Classification

- **Strategic**: segment == Strategic
- **Enterprise**: segment == Enterprise
- All other segments treated as non-Strategic/Enterprise for counting purposes.
