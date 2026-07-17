# Notes

## English

This task checks whether a solver can combine module-level quote construction with advisory freight comparison for `Q-TE-FC-4560`. The expected answer keeps only the three field-clinic modules, uses the internal catalog prices and lead/shelf data, computes an EXW subtotal of `36630.00`, and shows air, sea, and road freight as advisory grand totals. The recommended advisory mode is `SEA`; road carries a medium border-risk flag. Quote controls require `PREPAY_100`, `30` offer-validity days, `EXW_WITH_ADVISORY_FREIGHT`, freight excluded from the base total, component overexpansion avoided, and policy controls for advisory freight, base-total exclusion, module-line-only policy, and new-client payment source.

The evaluator uses eleven weighted scoring points totaling 33 points: module line set, quantities and unit prices, EXW subtotal, freight grand totals, transport recommendation, quote controls, component-overexpansion avoidance, route-risk flag, advisory/base-total policy controls, component-line policy control, and payment-source policy control.

## 中文

本任务用于检查求解器是否能把模块级报价和建议性运费比较结合起来，目标报价为 `Q-TE-FC-4560`。预期答案只保留三个 field-clinic 模块，使用内部目录中的价格、交期和保质期数据，计算 EXW 小计 `36630.00`，并将空运、海运和陆运作为建议性运费选项展示其含运费总额。推荐的建议运输方式是 `SEA`；陆运需要标记为中等边境风险。报价控制项要求 `PREPAY_100`、报价有效期 `30` 天、`EXW_WITH_ADVISORY_FREIGHT`、运费不计入基础总额、避免展开到组件级报价，并填写关于建议性运费、基础总额排除运费、仅模块级行和新客户付款来源的政策控制。

评估器包含十一个加权评分点，总分 33 分：模块行集合、数量和单价、EXW 小计、运费选项总额、运输建议、报价控制、避免组件过度展开、路线风险标记、建议性运费/基础总额政策控制、组件行政策控制，以及付款来源政策控制。
