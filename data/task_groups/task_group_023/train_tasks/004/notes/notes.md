# train_004 Notes

## English

Data lineage: source scenario SCN_023 E002. Generated country panel, country metadata, and name-variant downloads are used.

Task definition: reconcile country names, detect scale and missingness anomalies, standardize retained PCA variables, compute a first burden component, summarize clusters, and compare income-group structure with pooled interpretation.

Scenario fit: this preserves the seed's WHO/World Bank harmonization, PCA preprocessing, anomaly detection, and income-group modeling difficulty.

Material map: country-indicators supplies panel values; country-metadata supplies ISO3/income groups; name-reconciliation supplies variant mappings.

Solution and evaluation basis: exact fields cover mapping counts, anomaly sets, PCA retained variables, variance share, loading leaders, join coverage, model decision, and clusters. Pitfalls include ignoring anomalies, failing to standardize variables, or treating name variants as unmatched countries.

Transfer design: answer comparison should teach country-name reconciliation, anomaly logging, missingness screening, standardized PCA, and income-group model interpretation.

## 中文

数据来源：来自 SCN_023 的 E002，使用生成的国家指标面板、国家元数据和名称变体文件。

任务定义：协调国家名称，识别尺度和缺失异常，对保留变量做标准化 PCA，汇总负担聚类，并判断收入组结构是否支持分组模型。

场景适配：保留了种子任务中的 WHO/World Bank 对齐、PCA 预处理、异常检测和收入组建模难点。

材料说明：country-indicators 提供面板值；country-metadata 提供 ISO3 和收入组；name-reconciliation 提供变体映射。

解答和评测：精确检查映射数量、异常集合、PCA 变量、方差份额、loading 变量、join 覆盖、模型决定和聚类计数。常见错误是忽略异常、不标准化或把名称变体当作无法匹配。

迁移设计：训练后可迁移名称协调、异常记录、缺失筛选、标准化 PCA 与收入组模型解释经验。

## Scoring And Evaluation Details

Answer construction reconciles ISO3/name variants, logs scale and GDP anomalies, retains the declared burden variables, imputes missing retained values before standardized PCA, and compares income-group structure.

Scoring points:

1. Weight 2: Correct country-name reconciliation counts. Exact checked field(s): `reconciliation.variant_rows`, `reconciliation.resolved_variant_rows`, `reconciliation.unresolved_variant_rows`.
2. Weight 3: Correct anomaly sets for BMI, adult mortality, and GDP gaps. Exact checked field(s): `anomalies.bmi_scaled_country_years`, `anomalies.adult_mortality_scaled_country_years`, `anomalies.complete_gdp_gap_iso3`.
3. Weight 2: Correct retained PCA variable count. Exact checked field(s): `pca.variable_count`, `pca.variables_retained`.
4. Weight 2: Correct first component variance share. Exact checked field(s): `pca.pc1_variance_share`.
5. Weight 2: Correct top positive PC1 loading variables. Exact checked field(s): `pca.top_positive_loadings`.
6. Weight 1: Correct income-group join coverage. Exact checked field(s): `model.income_group_join_coverage`.
7. Weight 2: Correct income-group model decision. Exact checked field(s): `model.random_intercept_variance_bucket`, `model.lr_decision`.
8. Weight 2: Correct burden cluster counts. Exact checked field(s): `pca.cluster_counts`.

## 评分与评测细节

答案构造协调 ISO3/名称变体，记录尺度和 GDP 异常，保留声明的负担变量，在标准化 PCA 前填补保留变量缺失，并比较收入组结构。

评分点：

1. 权重 2：Correct country-name reconciliation counts.。精确检查字段：`reconciliation.variant_rows`, `reconciliation.resolved_variant_rows`, `reconciliation.unresolved_variant_rows`。
2. 权重 3：Correct anomaly sets for BMI, adult mortality, and GDP gaps.。精确检查字段：`anomalies.bmi_scaled_country_years`, `anomalies.adult_mortality_scaled_country_years`, `anomalies.complete_gdp_gap_iso3`。
3. 权重 2：Correct retained PCA variable count.。精确检查字段：`pca.variable_count`, `pca.variables_retained`。
4. 权重 2：Correct first component variance share.。精确检查字段：`pca.pc1_variance_share`。
5. 权重 2：Correct top positive PC1 loading variables.。精确检查字段：`pca.top_positive_loadings`。
6. 权重 1：Correct income-group join coverage.。精确检查字段：`model.income_group_join_coverage`。
7. 权重 2：Correct income-group model decision.。精确检查字段：`model.random_intercept_variance_bucket`, `model.lr_decision`。
8. 权重 2：Correct burden cluster counts.。精确检查字段：`pca.cluster_counts`。

