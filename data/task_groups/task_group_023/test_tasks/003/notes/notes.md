# test_003 Notes

## English

Data lineage: source scenario SCN_023 E002 using generated country panel, metadata, and name variants.

Task definition: for 2019-2024, reconcile names, log anomalies, screen missingness, standardize retained variables, compute first-component burden summaries, and evaluate income-group structure.

Scenario fit: the task is a test counterpart to the WHO/World Bank PCA and mixed-model audit.

Material map: country-indicators supplies panel fields; metadata supplies ISO3 and income groups; name-reconciliation supplies variants.

Solution and evaluation basis: scoring checks mapping counts, anomaly sets, PCA rows/variables, variance share, top absolute loadings, high-burden cluster count, income variance bucket, model decision, and readiness. Pitfalls include letting anomalies drive PCA or ignoring name variants.

Transfer design: anchored by train_004. The SOP transfers, but the later time window changes row counts, anomaly year sets, and PCA summaries.

## 中文

数据来源：来自 SCN_023 的 E002，使用生成的国家面板、元数据和名称变体。

任务定义：针对 2019-2024，协调名称、记录异常、筛选缺失、标准化保留变量、计算第一主成分负担摘要，并评估收入组结构。

场景适配：这是 WHO/World Bank PCA 与混合模型审计的测试对应任务。

材料说明：country-indicators 提供面板字段；metadata 提供 ISO3 和收入组；name-reconciliation 提供变体。

解答和评测：评分检查映射数量、异常集合、PCA 行/变量、方差份额、绝对 loading、high-burden 计数、收入方差桶、模型决定和 readiness。常见错误是让异常主导 PCA 或忽略名称变体。

迁移设计：由 train_004 锚定。SOP 可迁移，但时间窗口改变了行数、异常年份集合和 PCA 摘要。

## Scoring And Evaluation Details

Answer construction reconciles ISO3/name variants, logs scale and GDP anomalies, retains the declared burden variables, imputes missing retained values before standardized PCA, and compares income-group structure.

Scoring points:

1. Weight 2: Correct resolved and unresolved country-name counts. Exact checked field(s): `reconciliation.resolved_variant_rows`, `reconciliation.unresolved_variant_rows`.
2. Weight 3: Correct country-year anomaly sets. Exact checked field(s): `anomalies.bmi_scaled_country_years`, `anomalies.adult_mortality_scaled_country_years`, `anomalies.complete_gdp_gap_iso3`.
3. Weight 2: Correct retained PCA rows and variables. Exact checked field(s): `pca.rows_used`, `pca.variables_retained`, `pca.variable_count`.
4. Weight 2: Correct PC1 variance share. Exact checked field(s): `pca.pc1_variance_share`.
5. Weight 2: Correct top absolute PC1 loading variables. Exact checked field(s): `pca.top_absolute_loadings`.
6. Weight 2: Correct high-burden cluster count. Exact checked field(s): `pca.high_burden_cluster_count`.
7. Weight 2: Correct income-group random-intercept variance bucket. Exact checked field(s): `model.random_intercept_variance_bucket`.
8. Weight 2: Correct LR-style model decision. Exact checked field(s): `model.lr_decision`.
9. Weight 1: Correct final readiness enum. Exact checked field(s): `final_readiness`.

## 评分与评测细节

答案构造协调 ISO3/名称变体，记录尺度和 GDP 异常，保留声明的负担变量，在标准化 PCA 前填补保留变量缺失，并比较收入组结构。

评分点：

1. 权重 2：Correct resolved and unresolved country-name counts.。精确检查字段：`reconciliation.resolved_variant_rows`, `reconciliation.unresolved_variant_rows`。
2. 权重 3：Correct country-year anomaly sets.。精确检查字段：`anomalies.bmi_scaled_country_years`, `anomalies.adult_mortality_scaled_country_years`, `anomalies.complete_gdp_gap_iso3`。
3. 权重 2：Correct retained PCA rows and variables.。精确检查字段：`pca.rows_used`, `pca.variables_retained`, `pca.variable_count`。
4. 权重 2：Correct PC1 variance share.。精确检查字段：`pca.pc1_variance_share`。
5. 权重 2：Correct top absolute PC1 loading variables.。精确检查字段：`pca.top_absolute_loadings`。
6. 权重 2：Correct high-burden cluster count.。精确检查字段：`pca.high_burden_cluster_count`。
7. 权重 2：Correct income-group random-intercept variance bucket.。精确检查字段：`model.random_intercept_variance_bucket`。
8. 权重 2：Correct LR-style model decision.。精确检查字段：`model.lr_decision`。
9. 权重 1：Correct final readiness enum.。精确检查字段：`final_readiness`。

