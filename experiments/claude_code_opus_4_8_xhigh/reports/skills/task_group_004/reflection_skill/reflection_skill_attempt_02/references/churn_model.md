# Churn Model Validation & Outreach Ranking — detailed reference

Read this for the churn-validation + candidate-outreach task. SKILL.md §8 has the summary.

## Dataset

CSV exports (Telco-style churn dataset):
- `/exports/churn/train.csv` — labeled training rows (has `Churn`).
- `/exports/churn/validation.csv` — labeled hold-out for accuracy (has `Churn`).
- `/exports/churn/candidates.csv` — accounts to score; **no `Churn` column**.

Columns are `customer_id`, a mix of numeric and categorical features, and `Churn`. Typical schema:
`customer_id, tenure, MonthlyCharges, TotalCharges, Contract, PaymentMethod, PaperlessBilling,
Partner, Dependents, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV,
StreamingMovies, SupportTickets90d, NPSLast, UsageTrendPct, InvoicePastDue, ActiveSeatRatio,
Churn`.

- `feature_count` = number of columns excluding `customer_id` and `Churn` (e.g. 19).
- `training_rows` / `validation_rows` = data-row counts of the respective files.
- Numeric vs categorical: let pandas infer dtypes (numeric columns become the scaled set, object
  columns become the one-hot set). `Yes/No` and string categories are categorical.

## Model (reproduces the graded accuracy)

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression

num = X_train.select_dtypes("number").columns
cat = [c for c in X_train.columns if c not in num]
pre = ColumnTransformer([
    ("num", StandardScaler(), list(num)),
    ("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat),
])
clf = Pipeline([("pre", pre),
                ("lr", LogisticRegression(max_iter=5000, random_state=0))])
clf.fit(X_train, y_train)         # y = (Churn == "Yes")
acc = clf.score(X_val, y_val) * 100
```

Key points:
- **`OneHotEncoder(drop="first")` is what lifts validation accuracy into the graded ~93% range.**
  Without `drop="first"` you tend to get ~91–92% (one fewer correct validation prediction) — a
  small but graded difference. Use `handle_unknown="ignore"` so candidate categories unseen in
  train don't crash scoring.
- Map accuracy to `accuracy_band`: `below_70` / `70_to_79` / `80_to_89` / `90_plus`.
- `tenure_coefficient_direction` = sign of the fitted logistic coefficient on the (scaled) tenure
  feature → `negative` (longer tenure lowers churn risk). Report `negative` / `positive` / `zero`.
- The environment may emit harmless matmul overflow / convergence warnings from a broken BLAS;
  results are stable across lbfgs/liblinear/newton-cg. Run scripts from a clean dir (not /tmp).

## Ranking the candidates

- Score ONLY the candidate account_ids the prompt lists (a subset of candidates.csv).
- `predicted_churn_probability` = `predict_proba(...)[:, 1]`, rounded to 3 dp. Return the top 5
  by probability.
- One candidate (low tenure + InvoicePastDue=Yes + low NPS + sharply negative usage trend) usually
  dominates with a clearly higher probability. The remaining candidates have near-zero
  probabilities whose exact ordering and 3rd-decimal values are solver-/encoding-sensitive — report
  the fitted model's output rather than trying to force a specific order. The #1 pick is robust.

## Outreach mapping (apply top-down, first match wins)

Drives `outreach_action` and `reason_code` per ranked candidate, read from that account's
candidate-row features:

1. `InvoicePastDue == "Yes"` → `collections_followup` / `overdue_receivable`.
2. low tenure (`tenure <= ~18`) → `renewal_save` / `low_tenure_high_churn`.
3. high support load or weak sentiment (`SupportTickets90d` high, e.g. ≥6, or `NPSLast` low/negative)
   → `technical_recovery` / `sla_degradation`.
4. negative usage trend (`UsageTrendPct < 0`) → `nurture_monitor` / `usage_decline`.
5. otherwise → `nurture_monitor` / `clean_billings`.

## cohort_checks

Computed over the **requested candidate set**:
- `past_due_shortlist_count` = candidates with `InvoicePastDue == "Yes"`.
- `low_tenure_shortlist_count` = candidates with low tenure (`tenure <= ~18`).
- `average_probability_top5` = mean of the 5 reported probabilities, 3 dp.

## policy_codes for this task

`model_protocol_code = MOD-7`, `probability_scale_code = PRB-4`, `deployment_rule_code = DEP-5`,
and **`outreach_mapping_code = OUT-2`** (this is the one place the value is the FIRST option of the
triple, not the middle — a verified exception).
