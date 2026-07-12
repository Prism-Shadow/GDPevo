# train_002 Notes

## English

Data lineage: source scenario SCN_023, especially E002's CDC stratification issue and E001's state socioeconomic adjustment. Generated portal files provide SCREEN rows and state SES values.

Task definition: the solver audits 2022 preventive screening rankings, determines whether demographic standardization is feasible, uses income as a proxy adjustment, and returns rank-shift and weighted-model fields.

Scenario fit: the work reflects public-health data audit practice where analysts must inspect stratification fields before claiming adjusted state rankings.

Material map: state-health contains SCREEN rows with intentionally blank demographic labels for this year; state-ses contains median income and poverty; source_request gives the stale-spreadsheet warning.

Solution and evaluation basis: exact checks cover measure/year, feasibility enum, bracket counts, top rank shifts, Spearman correlation, model direction, and action label. Pitfalls include treating blank labels as usable strata or ignoring sample-size weights.

Transfer design: this train task teaches through answer comparison that empty demographic labels are not valid standardization strata and that income-proxy adjustment must be made explicit.

## 中文

数据来源：来自 SCN_023，结合 E002 的 CDC 分层问题和 E001 的州级社会经济调整。门户提供 SCREEN 行和州级 SES。

任务定义：求解者审计 2022 年筛查排名，判断人口学标准化是否可行，用收入代理调整，并返回排名变化和加权模型结果。

场景适配：该任务模拟公共健康排名审计，重点是先检查分层字段再解释调整排名。

材料说明：state-health 中本年度 SCREEN 的人口学标签有意为空；state-ses 提供收入与贫困；payload 只提示旧表风险。

解答和评测：精确检查指标年份、可行性枚举、收入分组计数、排名变化、Spearman 相关、模型方向和动作标签。常见错误是把空标签当作有效分层或忽略样本量权重。

迁移设计：训练后可迁移的经验是空人口学标签不能用于直接标准化，收入代理调整需要显式说明。

## Scoring And Evaluation Details

Answer construction uses valid state Total rows, SES income quartiles, sample-size weighted state modeling, income-proxy adjusted rankings, Spearman rank correlation, and controlled action enums.

Scoring points:

1. Weight 2: Correct measure, year, state count, and priority direction. Exact checked field(s): `measure.measure_id`, `measure.analysis_year`, `measure.valid_state_count`, `measure.priority_direction`.
2. Weight 3: Correct demographic-standardization feasibility finding. Exact checked field(s): `adjustment.demographic_adjustment_feasibility`.
3. Weight 2: Correct income-proxy bracket counts. Exact checked field(s): `adjustment.income_proxy_bracket_counts`.
4. Weight 2: Correct top upward adjusted rank shifts. Exact checked field(s): `rank_shift.top_upward_shift_states`.
5. Weight 2: Correct top downward adjusted rank shifts. Exact checked field(s): `rank_shift.top_downward_shift_states`.
6. Weight 2: Correct Spearman rank correlation. Exact checked field(s): `rank_shift.spearman_crude_vs_adjusted`.
7. Weight 2: Correct weighted model poverty sign and p-value bucket. Exact checked field(s): `weighted_model.poverty_coefficient_sign`, `weighted_model.poverty_p_bucket`.
8. Weight 2: Correct final action label. Exact checked field(s): `action_label`.

## 评分与评测细节

答案构造使用有效州级 Total 行、SES 收入四分位、样本量加权州级模型、收入代理调整排名、Spearman 排名相关和受控动作枚举。

评分点：

1. 权重 2：Correct measure, year, state count, and priority direction.。精确检查字段：`measure.measure_id`, `measure.analysis_year`, `measure.valid_state_count`, `measure.priority_direction`。
2. 权重 3：Correct demographic-standardization feasibility finding.。精确检查字段：`adjustment.demographic_adjustment_feasibility`。
3. 权重 2：Correct income-proxy bracket counts.。精确检查字段：`adjustment.income_proxy_bracket_counts`。
4. 权重 2：Correct top upward adjusted rank shifts.。精确检查字段：`rank_shift.top_upward_shift_states`。
5. 权重 2：Correct top downward adjusted rank shifts.。精确检查字段：`rank_shift.top_downward_shift_states`。
6. 权重 2：Correct Spearman rank correlation.。精确检查字段：`rank_shift.spearman_crude_vs_adjusted`。
7. 权重 2：Correct weighted model poverty sign and p-value bucket.。精确检查字段：`weighted_model.poverty_coefficient_sign`, `weighted_model.poverty_p_bucket`。
8. 权重 2：Correct final action label.。精确检查字段：`action_label`。

