# train_001 Notes

## English

Data lineage: source scenario SCN_023 and examples E001/E003. This train task uses generated state health, state SES, and region files from the shared Web portal. The task mirrors the seed's state-level confounding audit with diabetes mortality as the outcome.

Task definition: the solver must use portal-visible state CSV downloads, filter to 2024 Total rows for OBESITY and DIAB_MORT, exclude territories, join state-level SES rows ending in 000, and compute nested regression diagnostics.

Scenario fit: this is a formal public-health statistical audit, not a tutorial. It exercises identifier harmonization, source filtering, long-format SES extraction, VIF, ICC, leverage sensitivity, and a controlled policy conclusion.

Material map: state-health provides mixed strata and survey outcomes; state-ses provides Attribute-Value socioeconomic rows; state-regions provides region nesting. The source_request payload supplies only the business context.

Solution and evaluation basis: scoring checks exact JSON fields for the state count/exclusions, Total-row filter, SES state-level flag, adjusted standardized coefficient, VIF bucket, ICC bucket, high-leverage sensitivity, and conclusion. Likely model pitfalls include using territories, stale rows, or stratified subgroup rows.

Transfer design: after comparing a blind attempt with the answer, agents can infer that public-health rows must be filtered to Total, SES rows must be restricted to state-level FIPS, and adjusted coefficients should be interpreted with VIF and leverage diagnostics.

## 中文

数据来源：本任务来自 SCN_023 的 E001/E003 风格，使用共享 Web 门户生成的州级健康、SES 与地区文件。它把原始肥胖-寿命审计改为肥胖-糖尿病死亡率审计。

任务定义：求解者需要从门户下载州级数据，筛选 2024 年 OBESITY 与 DIAB_MORT 的 Total 行，排除属地，只连接州级 SES 行，并计算嵌套回归诊断。

场景适配：这是正式的公共健康统计审计任务，覆盖标识符协调、分层筛选、长表 SES 提取、VIF、ICC、高杠杆敏感性与结论枚举。

材料说明：state-health 提供混合分层和健康指标，state-ses 提供 Attribute-Value 社会经济长表，state-regions 提供区域嵌套。payload 只给业务背景，不给步骤。

解答和评测：评测精确检查样本、筛选规则、SES 规则、调整后标准化系数、VIF、ICC、高杠杆敏感性和最终结论。常见错误是使用属地、陈旧行或分层子组行。

迁移设计：训练后可迁移的经验是 Total 行优先、州级 FIPS 过滤、调整模型要结合共线性和敏感性判断。

## Scoring And Evaluation Details

Answer construction uses portal CSV rows filtered to the requested year and Total stratum, excludes territories, pivots state-level SES rows only, and computes deterministic OLS, VIF, ICC, and leverage sensitivity summaries at the declared precision.

Scoring points:

1. Weight 2: Correct state sample and exclusions for the 2024 diabetes mortality model. Exact checked field(s): `sample.states_in_model`, `sample.excluded_states`, `sample.territories_excluded`.
2. Weight 2: Correct Total-stratum exposure and outcome filters. Exact checked field(s): `filters.exposure_measure_id`, `filters.outcome_measure_id`, `filters.stratum_type`, `filters.stratum`.
3. Weight 2: Correct state-level SES extraction convention. Exact checked field(s): `filters.state_level_ses_rows_only`.
4. Weight 3: Correct adjusted standardized obesity coefficient and p-value bucket. Exact checked field(s): `model.adjusted_std_beta`, `model.adjusted_p_bucket`.
5. Weight 2: Correct VIF bucket and collinearity culprit pair. Exact checked field(s): `diagnostics.max_vif_bucket`, `diagnostics.culprit_pair`.
6. Weight 1: Correct regional ICC bucket. Exact checked field(s): `diagnostics.regional_icc_bucket`.
7. Weight 3: Correct high-leverage sensitivity result. Exact checked field(s): `diagnostics.high_leverage_states`, `diagnostics.sensitivity_verdict`.
8. Weight 2: Correct final claim conclusion. Exact checked field(s): `conclusion`.

## 评分与评测细节

答案构造使用门户 CSV 中请求年份和 Total 分层，排除属地，只 pivot 州级 SES 行，并按声明精度计算 OLS、VIF、ICC 和杠杆敏感性。

评分点：

1. 权重 2：Correct state sample and exclusions for the 2024 diabetes mortality model.。精确检查字段：`sample.states_in_model`, `sample.excluded_states`, `sample.territories_excluded`。
2. 权重 2：Correct Total-stratum exposure and outcome filters.。精确检查字段：`filters.exposure_measure_id`, `filters.outcome_measure_id`, `filters.stratum_type`, `filters.stratum`。
3. 权重 2：Correct state-level SES extraction convention.。精确检查字段：`filters.state_level_ses_rows_only`。
4. 权重 3：Correct adjusted standardized obesity coefficient and p-value bucket.。精确检查字段：`model.adjusted_std_beta`, `model.adjusted_p_bucket`。
5. 权重 2：Correct VIF bucket and collinearity culprit pair.。精确检查字段：`diagnostics.max_vif_bucket`, `diagnostics.culprit_pair`。
6. 权重 1：Correct regional ICC bucket.。精确检查字段：`diagnostics.regional_icc_bucket`。
7. 权重 3：Correct high-leverage sensitivity result.。精确检查字段：`diagnostics.high_leverage_states`, `diagnostics.sensitivity_verdict`。
8. 权重 2：Correct final claim conclusion.。精确检查字段：`conclusion`。

