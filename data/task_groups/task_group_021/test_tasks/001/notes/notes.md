# Test 001 — Dealer Renewal Contact Certification

## English

### Problem and transfer basis

This test applies the contact-master conventions anchored by train 001 and train 004 to dealer renewal evidence. It adds unsafe-identity graph analysis, source-withdrawal robustness, FX-budgeted two-stage evidence recovery, and all-permutation source-sequence stability.

### Solution basis

Reconstruct the canonical population and focus cases first. Keep identity, canonical contact, provenance, and readiness decisions separate. Build the unsafe graph from the final canonical population, solve the minimum containment and withdrawal cases, evaluate candidate recovery batches with certified cutoff FX, and replay every required source order with cumulative state transitions.

### Materials and pitfalls

The scope payload defines focus cases, controlled enums, business cutoffs, graph rules, budgets, and ranking rules. The shared environment supplies the large contact and reference populations. Major pitfalls are name-only merging, mixing field provenance with master selection, using non-certified FX, optimizing the wrong population, or reporting only the recommended source order instead of all permutations.

### Exact evaluation

Ten disjoint exact-result bundles use weights `3,2,1,3,1,1,1,3,1,2`. Each required answer leaf belongs to exactly one point. Every declared path in a point must match the standard answer; one wrong field makes that point zero, while unrelated points remain independently scorable.

## 中文

### 问题与迁移依据

本测试把 train 001 和 train 004 的联系人主数据约定迁移到经销商续约证据，并增加不安全身份图、来源撤回稳健性、按认证汇率预算的两阶段证据恢复，以及全部来源排列的稳定性回放。

### 解题依据

先重建规范实体群体和焦点案例，分别处理身份、规范联系方式、字段来源和续约就绪决策。基于最终规范群体建立不安全图，求最小隔离修复和来源撤回结果；使用截止日认证汇率评估恢复批次；对所有要求的来源顺序回放累计状态变化。

### 材料与易错点

范围载荷定义焦点案例、受控枚举、业务截止时间、图规则、预算和排序规则；共享环境提供大规模联系人和参考数据。主要错误包括按姓名合并、混淆字段来源与主实体选择、使用未认证汇率、优化错误群体，或只报告推荐顺序而遗漏全部排列。

### 精确评测

十个互不重叠的精确结果包权重为 `3,2,1,3,1,1,1,3,1,2`。每个必需答案叶字段只属于一个评分点；评分点中的所有声明路径都必须匹配，任一字段错误使该点归零，其他点仍可独立得分。
