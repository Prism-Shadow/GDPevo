# train_005 Notes

## English

Data lineage: source scenario SCN_023 E003 with the mediation component emphasized. Generated county health, SES, metadata, and neighbor files are used.

Task definition: identify the correct physical inactivity mediator, assemble complete county records, estimate a poverty-to-mediator and mediator-to-outcome path, bootstrap the indirect effect, aggregate residuals spatially, and flag positive residual counties.

Scenario fit: this mirrors the seed's county mediation and residual clustering analysis while keeping the output structured and exactly scored.

Material map: county-health contains OBESITY and LPA measures; county-ses supplies poverty, income, unemployment, education, migration, and RUCC; county-neighbors supports Moran-style state residual summaries.

Solution and evaluation basis: scoring checks measure IDs, counts, dynamic/RUCC rules, indirect effect, bootstrap enum, Moran bucket/isolate count, residual flags, and action label. Pitfalls include choosing a prevention measure instead of LPA, using the wrong income-change baseline, or including isolates as ordinary neighbors.

Transfer design: this train task anchors the mediator lookup, dynamic variable convention, RUCC dummy treatment, and isolate handling for spatial summaries.

## 中文

数据来源：来自 SCN_023 的 E003，并突出中介分析部分。使用生成的县级健康、SES、元数据和邻接文件。

任务定义：识别 physical inactivity 对应的 mediator，组装完整县级记录，估计贫困到 mediator 和 mediator 到 outcome 的路径，bootstrap 间接效应，汇总空间残差并标记正残差县。

场景适配：该任务对应种子中的县级中介和残差空间聚类分析，同时把结果固定为结构化 JSON。

材料说明：county-health 包含 OBESITY 与 LPA；county-ses 提供贫困、收入、失业、教育、迁移和 RUCC；county-neighbors 支持州级残差 Moran 摘要。

解答和评测：评分检查指标 ID、样本、动态/RUCC 规则、间接效应、bootstrap 枚举、Moran 桶和 isolate 数、残差标记及动作标签。常见错误是选错 mediator、用错收入变化基线或把 isolate 当普通邻居。

迁移设计：该训练任务锚定 mediator 查找、动态变量、RUCC dummy 和空间 isolate 处理经验。

## Scoring And Evaluation Details

Answer construction identifies the outcome and physical-inactivity mediator IDs, filters complete county cases, fits the raw-value mediation models, bootstraps the indirect-effect sign bucket, aggregates residuals for spatial summaries, and ranks positive residual FIPS.

Scoring points:

1. Weight 3: Correct outcome and mediator measure ids. Exact checked field(s): `measures.outcome_measure_id`, `measures.mediator_measure_id`, `measures.mediator_label`.
2. Weight 2: Correct complete-case count and exclusions. Exact checked field(s): `scope.complete_case_count`, `scope.exclusions_by_reason`.
3. Weight 2: Correct dynamic variable and RUCC conventions. Exact checked field(s): `modeling.dynamic_variable_rule`, `modeling.rucc_handling`.
4. Weight 3: Correct indirect effect estimate. Exact checked field(s): `modeling.indirect_effect`.
5. Weight 2: Correct bootstrap confidence interval enum. Exact checked field(s): `modeling.bootstrap_ci_enum`.
6. Weight 2: Correct Moran's I bucket and isolate count. Exact checked field(s): `spatial.moran_i_bucket`, `spatial.isolate_state_count`.
7. Weight 2: Correct positive residual FIPS set. Exact checked field(s): `flags.top_positive_residual_fips`.
8. Weight 2: Correct action label. Exact checked field(s): `action_label`.

## 评分与评测细节

答案构造识别 outcome 与 physical-inactivity mediator ID，筛选完整县级案例，拟合原始值中介模型，bootstrap 间接效应符号区间，汇总空间残差并排序正残差 FIPS。

评分点：

1. 权重 3：Correct outcome and mediator measure ids.。精确检查字段：`measures.outcome_measure_id`, `measures.mediator_measure_id`, `measures.mediator_label`。
2. 权重 2：Correct complete-case count and exclusions.。精确检查字段：`scope.complete_case_count`, `scope.exclusions_by_reason`。
3. 权重 2：Correct dynamic variable and RUCC conventions.。精确检查字段：`modeling.dynamic_variable_rule`, `modeling.rucc_handling`。
4. 权重 3：Correct indirect effect estimate.。精确检查字段：`modeling.indirect_effect`。
5. 权重 2：Correct bootstrap confidence interval enum.。精确检查字段：`modeling.bootstrap_ci_enum`。
6. 权重 2：Correct Moran's I bucket and isolate count.。精确检查字段：`spatial.moran_i_bucket`, `spatial.isolate_state_count`。
7. 权重 2：Correct positive residual FIPS set.。精确检查字段：`flags.top_positive_residual_fips`。
8. 权重 2：Correct action label.。精确检查字段：`action_label`。

