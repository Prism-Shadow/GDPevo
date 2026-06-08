# Notes

## English

This task checks whether a solver can combine module-level quote construction with advisory freight comparison for `Q-TE-FC-4560`. The expected answer keeps only the three field-clinic modules, uses the internal catalog prices and lead/shelf data, computes an EXW subtotal of `36630.00`, and shows air, sea, and road freight as advisory grand totals. The recommended advisory mode is `SEA`; road carries a medium border-risk flag. Quote controls require `PREPAY_100`, `30` offer-validity days, `EXW_WITH_ADVISORY_FREIGHT`, freight excluded from the base total, component overexpansion avoided, and policy controls for advisory freight, base-total exclusion, module-line-only policy, and new-client payment source.

The evaluator uses eleven weighted scoring points totaling 33 points: module line set, quantities and unit prices, EXW subtotal, freight grand totals, transport recommendation, quote controls, component-overexpansion avoidance, route-risk flag, advisory/base-total policy controls, component-line policy control, and payment-source policy control.

