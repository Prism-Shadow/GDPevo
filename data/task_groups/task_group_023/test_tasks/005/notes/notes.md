# test_005 Notes

## English

Data lineage: source scenario SCN_023 E003 with generated county health, SES, metadata, and state-neighbor pages.

Task definition: identify CHD and physical inactivity measure IDs, assemble complete cases, compute dynamic variables, estimate a mediation pathway, summarize residual spatial clustering and hotspot division, and flag positive residual counties.

Scenario fit: this is a test task in the same county mediation/spatial audit family as train_005, with a new outcome and geographic panel.

Material map: county-health supplies CHD and LPA; county-ses supplies poverty, income, unemployment, education, migration, and RUCC; metadata supplies division; neighbors supports Moran isolate handling.

Solution and evaluation basis: scoring checks measure IDs, complete cases, dynamic rule, indirect effect, CI enum, Moran bucket/isolate count, hotspot division, flagged FIPS, and action enum. Pitfalls include using another prevention measure as mediator, omitting TX/Western scope differences, or mishandling isolates.

Transfer design: anchored by train_003 and train_005. Transfer-dependent points use mediator lookup, long-format pivoting, dynamic variable construction, RUCC controls, and isolate handling; the CHD outcome and requested states require task-specific exploration.

## 中文

数据来源：来自 SCN_023 的 E003，使用生成的县级健康、SES、元数据和州邻接页面。

任务定义：识别 CHD 和 physical inactivity 指标 ID，组装完整案例，计算动态变量，估计中介路径，汇总残差空间聚类和 hotspot division，并标记正残差县。

场景适配：这是与 train_005 同一县级中介/空间审计族的测试任务，但 outcome 和地区不同。

材料说明：county-health 提供 CHD 与 LPA；county-ses 提供贫困、收入、失业、教育、迁移和 RUCC；metadata 提供 division；neighbors 支持 Moran isolate 处理。

解答和评测：评分检查指标 ID、完整案例、动态规则、间接效应、CI 枚举、Moran 桶和 isolate、hotspot division、FIPS 标记和动作枚举。常见错误是选错 mediator、忽略 TX/西部范围差异或错误处理 isolate。

迁移设计：由 train_003 和 train_005 锚定。迁移点是 mediator 查找、长表 pivot、动态变量、RUCC 控制和 isolate 处理；CHD outcome 和州范围需要任务内探索。

## Scoring And Evaluation Details

Answer construction identifies the outcome and physical-inactivity mediator IDs, filters complete county cases, fits the raw-value mediation models, bootstraps the indirect-effect sign bucket, aggregates residuals for spatial summaries, and ranks positive residual FIPS.

Scoring points:

1. Weight 3: Correct CHD outcome and physical-inactivity mediator IDs. Exact checked field(s): `measures.outcome_measure_id`, `measures.mediator_measure_id`, `measures.mediator_label`.
2. Weight 2: Correct complete-case county count. Exact checked field(s): `scope.complete_case_count`.
3. Weight 2: Correct dynamic socioeconomic variable rule. Exact checked field(s): `modeling.dynamic_variable_rule`.
4. Weight 3: Correct indirect effect estimate. Exact checked field(s): `modeling.indirect_effect`.
5. Weight 2: Correct bootstrap CI enum. Exact checked field(s): `modeling.bootstrap_ci_enum`.
6. Weight 2: Correct Moran's I bucket and isolate count. Exact checked field(s): `spatial.moran_i_bucket`, `spatial.isolate_state_count`.
7. Weight 2: Correct residual hotspot division. Exact checked field(s): `spatial.top_residual_hotspot_division`.
8. Weight 3: Correct flagged county FIPS set. Exact checked field(s): `flags.top_positive_residual_fips`.
9. Weight 1: Correct final action enum. Exact checked field(s): `action_label`.

## 评分与评测细节

答案构造识别 outcome 与 physical-inactivity mediator ID，筛选完整县级案例，拟合原始值中介模型，bootstrap 间接效应符号区间，汇总空间残差并排序正残差 FIPS。

评分点：

1. 权重 3：Correct CHD outcome and physical-inactivity mediator IDs.。精确检查字段：`measures.outcome_measure_id`, `measures.mediator_measure_id`, `measures.mediator_label`。
2. 权重 2：Correct complete-case county count.。精确检查字段：`scope.complete_case_count`。
3. 权重 2：Correct dynamic socioeconomic variable rule.。精确检查字段：`modeling.dynamic_variable_rule`。
4. 权重 3：Correct indirect effect estimate.。精确检查字段：`modeling.indirect_effect`。
5. 权重 2：Correct bootstrap CI enum.。精确检查字段：`modeling.bootstrap_ci_enum`。
6. 权重 2：Correct Moran's I bucket and isolate count.。精确检查字段：`spatial.moran_i_bucket`, `spatial.isolate_state_count`。
7. 权重 2：Correct residual hotspot division.。精确检查字段：`spatial.top_residual_hotspot_division`。
8. 权重 3：Correct flagged county FIPS set.。精确检查字段：`flags.top_positive_residual_fips`。
9. 权重 1：Correct final action enum.。精确检查字段：`action_label`。

