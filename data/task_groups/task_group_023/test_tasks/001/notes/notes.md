# test_001 Notes

## English

Data lineage: source scenario SCN_023 E001. This test task uses generated state health, SES, and region data from the shared Web portal.

Task definition: audit whether 2024 obesity is the primary driver of life expectancy. The solver must use Total rows, exclude territories, avoid stale substitute rows, join state-level SES records, and compute nested model diagnostics.

Scenario fit: the task matches the original state obesity/life-expectancy regression audit but uses generated Web evidence and structured exact scoring.

Material map: state-health provides OBESITY and LIFE_EXP with mixed years and strata; state-ses provides long-format confounders; state-regions provides region nesting.

Solution and evaluation basis: scoring covers sample/exclusions, filters, SES convention, bivariate and adjusted effects, VIF, ICC, high-leverage sensitivity, and final conclusion. Pitfalls include using stale 2023 CA or TX rows, stratified rows, or territory records.

Transfer design: anchored by train_001 and train_002. Transfer-dependent points require Total-row filtering, state-level FIPS extraction, VIF interpretation, and leverage sensitivity learned from train tasks; the outcome and missing-current pattern differ.

## 中文

数据来源：来自 SCN_023 的 E001，使用共享 Web 门户生成的州级健康、SES 和地区数据。

任务定义：审计 2024 年肥胖是否是寿命差异的主要驱动。求解者必须使用 Total 行、排除属地、不用陈旧替代行、连接州级 SES，并计算嵌套模型诊断。

场景适配：该任务对应原始州级肥胖-寿命回归审计，但以生成的 Web 证据和结构化精确评分呈现。

材料说明：state-health 提供混合年份/分层的 OBESITY 和 LIFE_EXP；state-ses 提供长格式混杂因素；state-regions 提供区域嵌套。

解答和评测：评分覆盖样本、筛选、SES 规则、双变量和调整效应、VIF、ICC、高杠杆敏感性和结论。常见错误是使用 2023 陈旧行、分层行或属地记录。

迁移设计：由 train_001 和 train_002 锚定。迁移点包括 Total 行筛选、州级 FIPS 提取、VIF 解释和敏感性判断；本任务改变了 outcome 和缺失模式。

## Scoring And Evaluation Details

Answer construction uses portal CSV rows filtered to the requested year and Total stratum, excludes territories, pivots state-level SES rows only, and computes deterministic OLS, VIF, ICC, and leverage sensitivity summaries at the declared precision.

Scoring points:

1. Weight 2: Correct analytic state count and exclusions. Exact checked field(s): `sample.states_in_model`, `sample.excluded_states`.
2. Weight 3: Correct current-year Total obesity and life-expectancy filters. Exact checked field(s): `filters.exposure_measure_id`, `filters.outcome_measure_id`, `filters.stratum_type`, `filters.stratum`.
3. Weight 2: Correct state-level SES join convention. Exact checked field(s): `filters.state_level_ses_rows_only`.
4. Weight 2: Correct bivariate standardized obesity effect. Exact checked field(s): `model.bivariate_std_beta`, `model.bivariate_p_bucket`.
5. Weight 3: Correct adjusted attenuation result. Exact checked field(s): `model.adjusted_std_beta`, `model.adjusted_p_bucket`, `model.attenuation_pct`.
6. Weight 2: Correct VIF bucket and culprit pair. Exact checked field(s): `diagnostics.max_vif_bucket`, `diagnostics.culprit_pair`.
7. Weight 1: Correct regional ICC bucket. Exact checked field(s): `diagnostics.regional_icc_bucket`.
8. Weight 3: Correct high-leverage sensitivity verdict. Exact checked field(s): `diagnostics.high_leverage_states`, `diagnostics.sensitivity_verdict`.
9. Weight 2: Correct final claim-support enum. Exact checked field(s): `conclusion`.

## 评分与评测细节

答案构造使用门户 CSV 中请求年份和 Total 分层，排除属地，只 pivot 州级 SES 行，并按声明精度计算 OLS、VIF、ICC 和杠杆敏感性。

评分点：

1. 权重 2：Correct analytic state count and exclusions.。精确检查字段：`sample.states_in_model`, `sample.excluded_states`。
2. 权重 3：Correct current-year Total obesity and life-expectancy filters.。精确检查字段：`filters.exposure_measure_id`, `filters.outcome_measure_id`, `filters.stratum_type`, `filters.stratum`。
3. 权重 2：Correct state-level SES join convention.。精确检查字段：`filters.state_level_ses_rows_only`。
4. 权重 2：Correct bivariate standardized obesity effect.。精确检查字段：`model.bivariate_std_beta`, `model.bivariate_p_bucket`。
5. 权重 3：Correct adjusted attenuation result.。精确检查字段：`model.adjusted_std_beta`, `model.adjusted_p_bucket`, `model.attenuation_pct`。
6. 权重 2：Correct VIF bucket and culprit pair.。精确检查字段：`diagnostics.max_vif_bucket`, `diagnostics.culprit_pair`。
7. 权重 1：Correct regional ICC bucket.。精确检查字段：`diagnostics.regional_icc_bucket`。
8. 权重 3：Correct high-leverage sensitivity verdict.。精确检查字段：`diagnostics.high_leverage_states`, `diagnostics.sensitivity_verdict`。
9. 权重 2：Correct final claim-support enum.。精确检查字段：`conclusion`。

