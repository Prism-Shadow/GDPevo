# Test 003 — Q2 Maintenance Integrity

## English

### Problem and transfer basis

This test transfers the maintenance-history method from train 003 to overlapping Q2 snapshots with cross-quarter baselines and changed edge cases.

### Solution basis

Select the authoritative source and controls, retain the correct overlap representatives, classify every edge case, reconstruct reliable predecessors after unit normalization, identify exact regression cases, and compute corrected Q2 continuity, distance, risk ranking, and certification routing.

### Materials and pitfalls

The scope payload defines the quarter, baseline boundary, controlled issue and route codes, and output ordering. The environment supplies maintenance events, snapshots, conversions, and query access. Pitfalls include using provisional snapshots, comparing unnormalized readings, allowing an invalid event to become a predecessor, or counting the same defect in the wrong issue class.

### Exact evaluation

Nine disjoint exact-result bundles use weights `3,1,3,1,2,2,1,1,3`. They cover source decisions and controls, issue counts, overlap retention and route controls, invalid-event classifications, regression measurements, corrected metrics, history actions, risk ranking, and certification.

## 中文

### 问题与迁移依据

本测试把 train 003 的维修历史方法迁移到具有跨季度基线和新边界案例的第二季度重叠快照。

### 解题依据

选择权威来源及控制，保留正确的重叠代表记录，分类每个边界案例，在统一单位后重建可靠前驱，识别精确回退案例，并计算修正后的第二季度连续性、距离、风险排序和认证路由。

### 材料与易错点

范围载荷定义季度、基线边界、受控问题代码、路由代码和输出顺序；环境提供维修事件、快照、换算和查询接口。易错点包括使用临时快照、比较未统一单位的读数、让非法事件成为前驱，或把同一缺陷计入错误类别。

### 精确评测

九个互不重叠的精确结果包权重为 `3,1,3,1,2,2,1,1,3`，覆盖来源与控制、问题计数、重叠保留与路由控制、非法事件分类、回退测量、修正指标、历史动作、风险排序和认证。
