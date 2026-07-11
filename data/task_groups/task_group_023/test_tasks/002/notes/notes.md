# test_002 Notes

## English

Data lineage: source scenario SCN_023 E003, with generated county health/SES/metadata Web data.

Task definition: assemble a Western county panel for DIABETES and DEPRESSION, pivot long SES attributes, compare static and dynamic socioeconomic models, and report outliers shared across outcome residual rankings.

Scenario fit: the task preserves county PLACES measure selection, FIPS joins, income-change construction, RUCC handling, and model comparison.

Material map: county-health supplies the two outcome measures; county-ses supplies socioeconomic levels and changes; county metadata supplies geographic fields.

Solution and evaluation basis: exact checks cover complete cases, exclusions, measure IDs, income/RUCC conventions, tercile means, winners, shared residual FIPS, and label. Pitfalls include picking wrong measure labels, treating SES long rows as already wide, or missing incomplete joins.

Transfer design: anchored by train_003 and train_005. The reusable mechanics are county pivoting, complete-case logging, income-change baseline, RUCC categorical controls, and model-choice interpretation; the outcomes and region differ.

## 中文

数据来源：来自 SCN_023 的 E003，使用生成的县级健康、SES 和元数据 Web 数据。

任务定义：为西部州县级面板组装 DIABETES 和 DEPRESSION 数据，pivot SES 长表，比较静态与动态社会经济模型，并报告两个 outcome 残差排名中的共同离群县。

场景适配：保留了县级 PLACES 指标选择、FIPS join、收入变化构造、RUCC 处理和模型比较。

材料说明：county-health 提供两个 outcome；county-ses 提供社会经济水平和变化；metadata 提供地理字段。

解答和评测：精确检查完整案例、排除、指标 ID、收入/RUCC 规则、三分组均值、模型胜者、共享残差 FIPS 和标签。常见错误是选错指标、把 SES 长表当宽表或漏记 incomplete joins。

迁移设计：由 train_003 和 train_005 锚定。可复用机制包括县级 pivot、完整案例记录、收入变化基线、RUCC 分类控制和模型选择解释；本任务改变 outcome 和地区。

## Scoring And Evaluation Details

Answer construction pivots county health and SES long tables by FIPS, records complete-case exclusions, computes unemployment-change tercile means, compares static/dynamic AIC, and ranks residual outliers.

Scoring points:

1. Weight 2: Correct complete-case county count and exclusions. Exact checked field(s): `scope.complete_case_count`, `scope.exclusions_by_reason`.
2. Weight 3: Correct diabetes and depression measure IDs. Exact checked field(s): `warehouse.measure_ids`.
3. Weight 2: Correct income-change and RUCC conventions. Exact checked field(s): `warehouse.income_change_rule`, `warehouse.rucc_handling`.
4. Weight 2: Correct diabetes unemployment-change tercile means. Exact checked field(s): `outcomes.DIABETES.unemployment_change_tercile_means`.
5. Weight 2: Correct depression unemployment-change tercile means. Exact checked field(s): `outcomes.DEPRESSION.unemployment_change_tercile_means`.
6. Weight 2: Correct winning model enum for both outcomes. Exact checked field(s): `model_winners`.
7. Weight 3: Correct shared residual outlier FIPS set. Exact checked field(s): `shared_residual_outlier_fips`.
8. Weight 2: Correct final reconciliation label. Exact checked field(s): `reconciliation_label`.

## 评分与评测细节

答案构造按 FIPS pivot 县级健康和 SES 长表，记录完整案例排除，计算失业变化三分组均值，比较静态/动态 AIC，并排序残差离群县。

评分点：

1. 权重 2：Correct complete-case county count and exclusions.。精确检查字段：`scope.complete_case_count`, `scope.exclusions_by_reason`。
2. 权重 3：Correct diabetes and depression measure IDs.。精确检查字段：`warehouse.measure_ids`。
3. 权重 2：Correct income-change and RUCC conventions.。精确检查字段：`warehouse.income_change_rule`, `warehouse.rucc_handling`。
4. 权重 2：Correct diabetes unemployment-change tercile means.。精确检查字段：`outcomes.DIABETES.unemployment_change_tercile_means`。
5. 权重 2：Correct depression unemployment-change tercile means.。精确检查字段：`outcomes.DEPRESSION.unemployment_change_tercile_means`。
6. 权重 2：Correct winning model enum for both outcomes.。精确检查字段：`model_winners`。
7. 权重 3：Correct shared residual outlier FIPS set.。精确检查字段：`shared_residual_outlier_fips`。
8. 权重 2：Correct final reconciliation label.。精确检查字段：`reconciliation_label`。

