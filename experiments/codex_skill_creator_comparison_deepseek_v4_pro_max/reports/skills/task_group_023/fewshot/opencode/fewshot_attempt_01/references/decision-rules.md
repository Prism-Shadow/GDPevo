# Decision Rules

How to evaluate controlled-gate predicates and produce the final
classification.

## Evaluation principle

Every business predicate must be evaluated on **unrounded** computed values.
Rounding happens only in the final JSON output, never before gate evaluation.

## Gate structure

The request defines an ordered list of gates, each with a boolean condition.
Typical patterns include:

- **Coefficient sign and significance**: coefficient sign, direction, and
  p-value against a declared threshold (e.g. p <= 0.05).
- **Prediction quality**: pooled Q-squared or R-squared and RMSE against
  declared thresholds.
- **Bootstrap significance**: plus-one p-value against a declared threshold.
- **Conformal calibration**: aggregate coverage and optionally mean interval
  width against declared thresholds.
- **Trajectory stability**: minimum or mean leave-one-out adjusted Rand index
  and optionally cumulative explained variance against declared thresholds.
- **Source stability**: same-sign fraction and median absolute percent shift
  against declared thresholds.

Each gate's exact thresholds come from the request. Never substitute
different cutoffs.

## Counting passed gates

Count the number of gates whose unrounded values satisfy their boolean
condition. All gates are evaluated independently; one gate's failure does
not affect another's evaluation.

## Conclusion mapping

The request declares a precedence-ordered classification scheme. Common
patterns:

### All-gates-pass threshold

Evaluate every gate. Count passed gates. Apply the request's tiered mapping,
e.g. all six pass yields one class, at least four pass yields another, fewer
yields a third. Use the exact classification strings from the request.

### First-failed-module precedence

Evaluate gates in the declared precedence order. If all pass, return the
success class. Otherwise return the failure class with the name of the first
module (by precedence) whose gate failed. Use the exact module names from
the request.

### Count-threshold tiers

Apply the first matching tier in the declared order. Tiers typically use
thresholds like all gates pass, at least 4 pass, at least 2 pass, otherwise
a fallback. Use the exact controlled conclusion strings.

## Reporting per-gate results

When the answer template requires per-gate PASS/FAIL values, report each
gate's status using the exact controlled enum values (typically "PASS" or
"FAIL"). Order matches the request's gate precedence.

## Gate-specific patterns

### Coefficient-and-p-value gates

A gate like "coefficient is negative AND jackknife p-value <= 0.05" passes
when both conditions hold on unrounded values. The relevant coefficient may
be the full coefficient, the bias-corrected coefficient, or a specific named
coefficient -- follow the request's exact naming.

### Bootstrap p-value gates

The bootstrap p-value is the plus-one p-value: (exceedance_count + 1) /
(replicates + 1). Compare directly against the declared threshold.

### Conformal coverage gates

Coverage is the fraction of test observations falling within the prediction
intervals. Compare the aggregate (pooled) coverage against the declared
threshold. Some gates also check mean interval width.

### Stability ARI gates

For trajectory clustering, the gate checks the minimum or mean adjusted
Rand index across all leave-one-out stability runs. Compare directly against
the declared threshold.

### Source perturbation gates

A gate like "every scenario is stable AND maximum absolute percent shift
<= 25" requires both conditions. "Stable" is defined by the request (e.g.
HC3 p-value stays below a threshold). Check every scenario.

### RMSE deterioration gates

A gate like "deletion RMSE deterioration >= threshold" compares the pooled
RMSE of the model without a source group against the full model's pooled
RMSE. Pass when the deterioration meets or exceeds the threshold.
