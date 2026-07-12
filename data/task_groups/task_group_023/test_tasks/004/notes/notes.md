# test_004 Notes

## English

Data lineage: source scenario SCN_023 E001/E002 with generated state health and SES files.

Task definition: audit 2024 vaccination-completion rankings, inspect adjustment feasibility, use income-proxy adjustment, and report rank shifts plus weighted model direction.

Scenario fit: it keeps the state ranking/confounding workflow while changing the prevention outcome and year from train_002.

Material map: state-health supplies VACC_COMP Total and strata rows; state-ses supplies income and poverty; the brief defines the priority direction.

Solution and evaluation basis: exact checks cover measure/year, feasibility enum, bracket counts, rank shifts, model direction, priority states, and action label. Pitfalls include assuming the train feasibility result without inspecting this measure, reversing the priority direction, or ignoring sample-size weights.

Transfer design: anchored by train_001 and train_002. Transfer helps with portal source selection, income-proxy adjustment, and weighted ranking, but this measure has different stratification availability.

## 中文

数据来源：来自 SCN_023 的 E001/E002，使用生成的州级健康和 SES 文件。

任务定义：审计 2024 年疫苗完成率排名，检查调整可行性，使用收入代理调整，并报告排名变化和加权模型方向。

场景适配：保留州级排名/混杂审计流程，但相对 train_002 更换了预防 outcome 和年份。

材料说明：state-health 提供 VACC_COMP Total 和分层行；state-ses 提供收入和贫困；brief 定义优先方向。

解答和评测：精确检查指标年份、可行性、分组计数、排名变化、模型方向、优先州和动作标签。常见错误是机械套用训练任务的可行性、不小心反转优先方向或忽略样本量权重。

迁移设计：由 train_001 和 train_002 锚定。迁移帮助选择门户来源、做收入代理调整和加权排名，但该指标的分层可用性不同。

## Scoring And Evaluation Details

Answer construction uses valid state Total rows, SES income quartiles, sample-size weighted state modeling, income-proxy adjusted rankings, Spearman rank correlation, and controlled action enums.

Scoring points:

1. Weight 2: Correct measure/year filter and valid state count. Exact checked field(s): `measure.measure_id`, `measure.analysis_year`, `measure.valid_state_count`.
2. Weight 3: Correct demographic adjustment feasibility enum. Exact checked field(s): `adjustment.demographic_adjustment_feasibility`.
3. Weight 2: Correct income-proxy bracket counts. Exact checked field(s): `adjustment.income_proxy_bracket_counts`.
4. Weight 2: Correct top upward adjusted rank shifts. Exact checked field(s): `rank_shift.top_upward_shift_states`.
5. Weight 2: Correct top downward adjusted rank shifts. Exact checked field(s): `rank_shift.top_downward_shift_states`.
6. Weight 2: Correct poverty coefficient sign and p-value bucket. Exact checked field(s): `weighted_model.poverty_coefficient_sign`, `weighted_model.poverty_p_bucket`.
7. Weight 3: Correct priority review state set. Exact checked field(s): `rank_shift.priority_review_states`.
8. Weight 2: Correct action label. Exact checked field(s): `action_label`.

## 评分与评测细节

答案构造使用有效州级 Total 行、SES 收入四分位、样本量加权州级模型、收入代理调整排名、Spearman 排名相关和受控动作枚举。

评分点：

1. 权重 2：Correct measure/year filter and valid state count.。精确检查字段：`measure.measure_id`, `measure.analysis_year`, `measure.valid_state_count`。
2. 权重 3：Correct demographic adjustment feasibility enum.。精确检查字段：`adjustment.demographic_adjustment_feasibility`。
3. 权重 2：Correct income-proxy bracket counts.。精确检查字段：`adjustment.income_proxy_bracket_counts`。
4. 权重 2：Correct top upward adjusted rank shifts.。精确检查字段：`rank_shift.top_upward_shift_states`。
5. 权重 2：Correct top downward adjusted rank shifts.。精确检查字段：`rank_shift.top_downward_shift_states`。
6. 权重 2：Correct poverty coefficient sign and p-value bucket.。精确检查字段：`weighted_model.poverty_coefficient_sign`, `weighted_model.poverty_p_bucket`。
7. 权重 3：Correct priority review state set.。精确检查字段：`rank_shift.priority_review_states`。
8. 权重 2：Correct action label.。精确检查字段：`action_label`。

