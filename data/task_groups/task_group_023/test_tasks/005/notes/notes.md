# Test 005 notes / 测试 005 说明

## Current whole-point evaluation boundary / 当前整点评分边界

The final eight binary points use raw weights `[1,3,3,3,3,3,3,2]` and score the complete cohort/census, GMM fit and jackknife summary, validation design/grid, bootstrap inference, conformal coverage summary, trajectory stability summary, source-deletion contract, and deployment decision. Each point earns its full `weight/21` only when every declared required module passes; otherwise zero. Module fractions are unscored diagnostics.

最终八个二元评分点的原始权重为 `[1,3,3,3,3,3,3,2]`，依次评估完整队列与州清单、GMM 拟合与 jackknife 摘要、验证设计与网格、bootstrap 推断、conformal 覆盖率摘要、轨迹稳定性摘要、来源删除契约和部署决策。每点只有在全部声明的必需模块通过时才获得完整 `weight/21`，否则为零；模块比例只是不计分诊断。

## English

### Objective and protocol dependency

This held-out task audits a balanced Midwest/West county COPD dynamics model for a 2026 briefing. It requires the complete ordered outputs of delete-state two-step GMM, state-blocked nested elastic net, wild-cluster bootstrap-t, grouped conformal calibration, trajectory PCA/clustering stability, and source-group perturbation.

The solver-facing request now registers `PHO_COUNTY_PANEL_TRANSPORT_V1` and intentionally contains overrides rather than a second copy of its SOP. The paired `train_005` task is the full training carrier for that protocol: it teaches publication reconciliation and balanced-panel construction; the clustered GMM and jackknife definitions; elastic-net objective, preprocessing, fold allocation, grid traversal, solver, selection, and OOF aggregation; the null-restricted bootstrap and continuous XORSHIFT32 accounting; split-conformal rank and calibration conventions; population PCA, deterministic k-means, silhouette, and delete-state ARI; and no-retune perturbation aggregation and ranking. This establishes a genuine train-to-test procedural dependency instead of rewarding a test-only procedural recipe.

### Held-out evidence and task-specific overrides

The evidence remains independent of the training scenario. Test 005 uses Midwest and West counties in 2021-2024, COPD and adult-smoking health releases, and poverty, unemployment, and net-migration releases. The filters remain FINAL/CRUDE, highest-final-revision, nonsuppressed/nonmissing health, complete socioeconomic values, and integer RUCC 1-9. The balanced test cohort still resolves to 258 counties, 774 adjacent-year rows, and 25 states.

All answer-determining test-specific inputs remain explicit: outcome and ordered terms, instrument and coefficient order, the test alpha and l1-ratio values and fold counts, smoking target, seed `6022026`, 499 replicates, the nine test checkpoints, ordered trajectory variables, six ordered source groups, numeric precision, and all six decision thresholds and controlled outcomes. The request removes only transferable mechanics already defined by the registered protocol.

### Fairness and leakage boundary

The training protocol supplies reusable method knowledge, not held-out evidence. `train_005` uses a different West/Northeast diabetes cohort, different health/economic variables, independent fitted values, a different hyperparameter grid, a different bootstrap seed and checkpoints, different source groups, different thresholds, and a different decision vocabulary. It does not expose this test task's 25-state census, fitted coefficients, fold surfaces, bootstrap stream, coverage table, PCA/clustering results, perturbation ranks, or final decision.

This split is fair because a solver with the paired training material has one authoritative SOP and every test-specific override needed to reproduce the gold result. A base solver can still recognize the registered dependency and reason about the task, but cannot recover the held-out numeric evidence without navigating the portal and executing the analysis. The answer template is only a typed output contract; it does not restate protocol algorithms.

### Contract and evaluator checks

The answer template retains exactly the same eight required top-level keys and all existing nested field keys, types, orders, and precision rules. Gold and evaluator files are unchanged. The semantic-module evaluator still has exactly eight rubric points with raw weights `[1,3,3,3,3,3,3,2]`; the unchanged gold response scores `1.0`.

## 中文

### 目标与协议依赖

本留出题审计 Midwest/West 平衡县级 COPD 动态模型能否用于 2026 年简报。题目要求完整、有序地提交六类方法的结果：删州两步 GMM、按州分块的嵌套 elastic net、wild-cluster bootstrap-t、分组 conformal 校准、轨迹 PCA/聚类稳定性，以及来源组扰动。

求解输入现已注册 `PHO_COUNTY_PANEL_TRANSPORT_V1`，并有意只保留覆盖项，而不再复制整套 SOP。配对的 `train_005` 是该协议的完整训练载体，覆盖：发布记录归并和平衡面板构造；聚类 GMM 与 jackknife 定义；elastic-net 目标、预处理、折分配、网格遍历、求解、选择与 OOF 汇总；受限零假设 bootstrap 和连续 XORSHIFT32 记账；split-conformal 的秩与校准约定；总体 PCA、确定性 k-means、silhouette 与删州 ARI；以及不重新调参的扰动汇总和排序。因此，本题形成真实的训练到测试流程依赖，而不是在测试输入中直接提供操作手册。

### 留出证据与题目专属覆盖项

测试证据与训练场景保持独立。测试 005 使用 2021-2024 年 Midwest/West 县，健康指标为 COPD 与成人吸烟，社会经济指标为贫困、失业和净迁移。筛选条件仍为 FINAL/CRUDE、最高 FINAL 修订、健康值未抑制且非空、社会经济值完整、RUCC 为 1-9 整数。测试平衡队列仍为 258 县、774 条相邻年度面板行和 25 州。

所有会改变答案的测试专属输入均继续显式存在：结局和有序变量、工具变量和系数顺序、测试 alpha/l1-ratio 值及折数、吸烟目标、种子 `6022026`、499 次重复、九个测试检查点、有序轨迹变量、六个有序来源组、数值精度，以及六项决策阈值和受控结论。请求删除的仅是已由注册协议定义的可迁移方法机制。

### 公平性与防泄漏边界

训练协议提供的是可复用方法知识，不是留出证据。`train_005` 使用不同的 West/Northeast 糖尿病队列、不同健康和经济变量、独立拟合值、不同超参数网格、不同 bootstrap 种子与检查点、不同来源组、不同阈值和不同决策枚举。训练题不会泄露本测试题的 25 州清单、拟合系数、折面、bootstrap 随机流、覆盖率表、PCA/聚类结果、扰动排名或最终决策。

这种拆分是公平的：获得配对训练材料的求解者拥有一份权威 SOP，以及复现金标所需的全部测试专属覆盖项。基础求解者仍可识别注册协议依赖并分析题意，但无法脱离门户检索和实际计算恢复留出数值证据。答案模板仅定义带类型输出契约，不复述协议算法。

### 契约与评测核验

答案模板仍保留完全相同的八个必需顶层键，以及全部既有嵌套字段键、类型、顺序和精度规则。金标与评测器文件均未修改。语义模块评测器仍严格包含八个评分点，原始权重为 `[1,3,3,3,3,3,3,2]`；未修改金标得分仍为 `1.0`。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source relevance: `E003` provides the primary county long-table, FIPS/RUCC, panel, and dynamic-model lineage; `E001` contributes clustered regression, confounder, sensitivity, and controlled claim-audit practices; `E002` contributes standardized trajectory PCA, clustering, and cross-source audit discipline.
- Task brief: audit a held-out Midwest/West county COPD panel through GMM, nested prediction, bootstrap, conformal, trajectory, and source-group perturbation modules before issuing a controlled deployment decision.
- Environment lineage: the task reads shared seeded county health and socioeconomic publications only through Public Health Observatory Web endpoints. The internal SQLite database, generator, manifests, seeds, source code, and judge remain unavailable to solvers.
- Payload lineage: the analysis request provides held-out filters, entities, orders, grids, seed/checkpoints, thresholds, and protocol overrides; the answer template provides only the typed schema. Reusable mechanics come from the paired solved training answer and no held-out result is copied from it.
- Author: independent task-builder agent `/root/build_test_005`.
- Created: 2026-07-15.
- Updated: 2026-07-15.
- Major changes: long-horizon algorithm expansion; procedural leakage removal; semantic evaluator hardening; registered-protocol transfer; final lineage completion.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源关联：`E003` 提供主要的县级长表、FIPS/RUCC、面板与动态模型沿袭；`E001` 提供聚类回归、混杂、敏感性和受控主张审计；`E002` 提供标准化轨迹 PCA、聚类和跨来源审计纪律。
- 任务简述：在给出受控部署结论前，通过 GMM、嵌套预测、bootstrap、conformal、轨迹和来源组扰动模块，审计留出的 Midwest/West 县级 COPD 面板。
- 环境沿袭：任务仅通过公共卫生观测站 Web 端点读取共享、固定种子的县级健康和社会经济发布；内部 SQLite、生成程序、清单、种子、源码和裁判均不向求解者开放。
- 载荷沿袭：分析请求提供留出筛选、实体、顺序、网格、种子/检查点、门槛和协议覆盖项；答案模板只提供带类型 schema。可复用机制来自配对训练标准答案，不从中复制任何留出结果。
- 作者：独立任务构建代理 `/root/build_test_005`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-15。
- 主要变更：扩展长程算法；移除程序化泄漏；强化语义评分器；建立注册协议迁移；补齐最终沿袭记录。
