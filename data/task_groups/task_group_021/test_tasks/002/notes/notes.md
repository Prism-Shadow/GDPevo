# Test 002 — March Fuel Compliance Reconciliation

## English

### Problem and transfer basis

This test transfers effective-reference, recognition, source-retention, unit/FX, and ledger conventions from train 002 and train 005 to a larger March fuel ledger with changed aliases and overlap cases.

### Solution basis

Select the authoritative source population, reconstruct logical transactions, resolve every requested reference case, and produce complete transaction adjudications including public semantics and internal controls. Keep exception populations separate from valid mismatches. Compute exact volume and spend totals, focus-asset results, merchant ranking, and final routing from the same accepted ledger.

### Materials and pitfalls

The scope payload supplies controlled cases and output rules; the shared environment supplies transactions, snapshots, aliases, units, FX, and query access. Pitfalls include using ingest time for effective references, treating mismatches as quarantine, omitting internal codes, mixing volume and spend eligibility, or ranking merchants before final exception reconstruction.

### Exact evaluation

Nine disjoint exact-result bundles use weights `3,1,3,2,1,2,2,2,3`: source scope; exception accounting; effective references; transaction adjudications; volume; spend; focus assets; merchant ranking; and status/action. Every path in a bundle must be exact.

## 中文

### 问题与迁移依据

本测试把 train 002 和 train 005 的生效参考、类别识别、来源保留、单位/汇率和台账约定迁移到更大的三月份燃油台账，其中别名和重叠来源均已变化。

### 解题依据

选择权威来源群体，重建逻辑交易，解析所有指定参考案例，并输出包含公开语义和内部控制的完整交易裁决。将有效类别不匹配与隔离异常分开；基于同一合格台账计算精确体积、金额、焦点资产、商户排序和最终路由。

### 材料与易错点

范围载荷提供受控案例和输出规则；共享环境提供交易、快照、别名、单位、汇率和查询接口。易错点包括按摄取时间选生效参考、把不匹配当隔离、遗漏内部代码、混淆体积与金额资格，或在最终异常重建前排序商户。

### 精确评测

九个互不重叠的精确结果包权重为 `3,1,3,2,1,2,2,2,3`，分别覆盖来源范围、异常核算、有效参考、交易裁决、体积、金额、焦点资产、商户排序和状态/动作。结果包内每条路径都必须精确匹配。
