# train_003 Notes

## English

Data lineage: source scenario SCN_023 E003. This task uses generated county_health_long, county_ses_long, and county_metadata from the Web portal.

Task definition: the solver must assemble a county complete-case dataset for CASTHMA in six states, pivot long SES attributes, compute unemployment-change terciles, compare static and dynamic models, and flag top residual outliers.

Scenario fit: it is a county warehouse and model audit directly aligned with the seed's PLACES plus ERS reconciliation workflow.

Material map: county-health supplies long health measures; county-ses supplies Attribute-Value SES fields; county metadata supplies state, county, RUCC, typology, and division.

Solution and evaluation basis: scoring checks count/exclusions, measure IDs, income-change rule, tercile means, winning model, residual FIPS set, and label. Pitfalls include treating Attribute rows as wide columns, using county-like invalid FIPS, or encoding RUCC as an unexamined continuous variable.

Transfer design: agents can infer county pivot, complete-case logging, income-change baseline, and RUCC categorical handling for later county tasks.

## 中文

数据来源：来自 SCN_023 的 E003，使用门户生成的县级健康长表、县级 SES 长表和县元数据。

任务定义：求解者需要为六个州组装 CASTHMA 完整县级数据，pivot SES 长表，计算失业变化三分组，比较静态与动态模型，并标记残差离群县。

场景适配：这是与种子任务一致的 PLACES 与 ERS 县级仓库/模型审计。

材料说明：county-health 提供健康指标长表；county-ses 提供 Attribute-Value SES 字段；metadata 提供州、县、RUCC、类型和 division。

解答和评测：评分检查样本和排除、指标 ID、收入变化规则、三分组均值、模型选择、残差 FIPS 集合和结论标签。常见错误包括把长表当宽表、使用无效 FIPS、或把 RUCC 直接当连续变量。

迁移设计：该训练任务沉淀县级 pivot、完整案例记录、收入变化基线和 RUCC 分类处理经验。

## Scoring And Evaluation Details

Answer construction pivots county health and SES long tables by FIPS, records complete-case exclusions, computes unemployment-change tercile means, compares static/dynamic AIC, and ranks residual outliers.

Scoring points:

1. Weight 2: Correct complete-case county count and exclusions. Exact checked field(s): `scope.complete_case_count`, `scope.exclusions_by_reason`.
2. Weight 2: Correct county warehouse measure id and RUCC handling. Exact checked field(s): `warehouse.measure_ids`, `warehouse.rucc_handling`.
3. Weight 2: Correct income-change rule. Exact checked field(s): `warehouse.income_change_rule`.
4. Weight 2: Correct unemployment-change tercile asthma means. Exact checked field(s): `outcomes.CASTHMA.unemployment_change_tercile_means`.
5. Weight 2: Correct static-vs-dynamic asthma model decision. Exact checked field(s): `outcomes.CASTHMA.winning_model`.
6. Weight 3: Correct asthma residual outlier FIPS set. Exact checked field(s): `outcomes.CASTHMA.top_residual_outlier_fips`.
7. Weight 1: Correct final reconciliation label. Exact checked field(s): `reconciliation_label`.

## 评分与评测细节

答案构造按 FIPS pivot 县级健康和 SES 长表，记录完整案例排除，计算失业变化三分组均值，比较静态/动态 AIC，并排序残差离群县。

评分点：

1. 权重 2：Correct complete-case county count and exclusions.。精确检查字段：`scope.complete_case_count`, `scope.exclusions_by_reason`。
2. 权重 2：Correct county warehouse measure id and RUCC handling.。精确检查字段：`warehouse.measure_ids`, `warehouse.rucc_handling`。
3. 权重 2：Correct income-change rule.。精确检查字段：`warehouse.income_change_rule`。
4. 权重 2：Correct unemployment-change tercile asthma means.。精确检查字段：`outcomes.CASTHMA.unemployment_change_tercile_means`。
5. 权重 2：Correct static-vs-dynamic asthma model decision.。精确检查字段：`outcomes.CASTHMA.winning_model`。
6. 权重 3：Correct asthma residual outlier FIPS set.。精确检查字段：`outcomes.CASTHMA.top_residual_outlier_fips`。
7. 权重 1：Correct final reconciliation label.。精确检查字段：`reconciliation_label`。

