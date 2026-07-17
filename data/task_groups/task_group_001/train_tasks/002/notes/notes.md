# train_002 Hidden Notes

## English

This task is part of `task_group_001`, sourced from scenario `SCN_001_crm_marketing_lead_capture` and especially source example `E002` with supporting CRM hygiene and event context from `E001` and `E003`. The task design brief is the prospecting task for `MarineSense Expo 2026` (`show_id`: `marinesense_2026`) for an OEM dissolved-oxygen sensor campaign. The shared generated environment is HarborCRM, with deterministic data in `env/data/harborcrm_data.json` and public access through the API endpoints documented in `env/README.md`.

The solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt asks for a qualified lead list, excluded near misses, platform labels, priority tiers, enrichment fields, and aggregate counts. It does not expose the final answer or a step-by-step SOP. The template fixes the JSON shape, enum values, ordering expectations, and integer count precision.

The relevant public data are `/api/tradeshows/marinesense_2026`, `/api/tradeshows/marinesense_2026/exhibitors`, `/api/tradeshows/marinesense_2026/meeting_interest`, `/api/crm/accounts`, and `/api/policies`. The construction-only data show five MarineSense exhibitors. Qualified leads must build, manufacture, or OEM target platforms for dissolved-oxygen integration: AUVs, ROVs, or underwater cameras. Pure distributors, service providers, and sensor-only vendors are excluded even when their descriptions mention target platforms.

The standard answer includes two qualified exhibitors. `Abyssal Robotics` (`exh_ms_001`) is a manufacturer of compact AUVs and inspection ROVs, has demo interest, and receives platforms `AUV` and `ROV` with priority `A`. `KelpLine Cameras` (`exh_ms_002`) is an OEM underwater-camera company with demo interest and receives platform `Underwater Camera` with priority `B`. The excluded near misses are `Bluefin Dealer Group` as `distributor_only`, `HarborLab Services` as `service_only`, and `Salinity Logic` as `sensor_vendor_only`. Aggregate counts are qualified total `2`, platform counts `AUV: 1`, `ROV: 1`, `Underwater Camera: 1`, priority counts `A: 1`, `B: 1`, `C: 0`, and excluded near misses total `3`.

Evaluation uses six exact-match scoring points with raw weights `[3, 3, 2, 2, 2, 1]`. SP001 checks the qualified exhibitor set. SP002 checks platform labels for every qualified exhibitor. SP003 checks booth, country, and website enrichment for qualified leads. SP004 checks the excluded near-miss set and reason enums. SP005 checks priority tiers. SP006 checks aggregate counts. The evaluator normalizes company rows by `company_id`, trims simple text, and permits a trailing slash difference in websites, but otherwise requires exact structured results. The standard answer must score `1.0`.

This train task is meant to teach transferable prospecting judgment without being a tutorial: manufacturer/OEM qualification, reseller and service-provider exclusion, controlled platform labels, use of meeting-interest signals for priority, and preservation of import-ready enrichment fields. Likely model pitfalls include counting Bluefin as qualified because it mentions ROV/AUV, counting Salinity Logic because it sells dissolved-oxygen sensors rather than target platforms, omitting KelpLine because it is a camera OEM instead of a vehicle maker, or producing free-form platform and reason labels outside the controlled enums.

Construction record: author `task-builder train_002`; created `2026-06-01`; updated `2026-06-01`; major changes include creating the prompt, answer template, bilingual notes, standard answer, and local rule-based evaluator for the six planned scoring points.

## 中文

本任务属于 `task_group_001`，来源场景为 `SCN_001_crm_marketing_lead_capture`，主要继承源示例 `E002` 的展会获客任务形态，同时参考 `E001` 和 `E003` 中的 CRM 与数据清洗背景。任务设计目标是为 `MarineSense Expo 2026`（`show_id`: `marinesense_2026`）构建 OEM 溶解氧传感器营销活动的合格线索名单。共享环境是 HarborCRM，确定性生成数据位于 `env/data/harborcrm_data.json`，公开访问方式见 `env/README.md` 中的 API 端点。

求解器可见材料只有 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示要求输出合格参展商、被排除的近似候选、平台标签、优先级、补充字段和汇总计数，但不暴露标准答案或逐步 SOP。模板固定 JSON 结构、枚举值、排序要求和整数计数精度。

相关公开数据包括 `/api/tradeshows/marinesense_2026`、`/api/tradeshows/marinesense_2026/exhibitors`、`/api/tradeshows/marinesense_2026/meeting_interest`、`/api/crm/accounts` 和 `/api/policies`。构造数据中 MarineSense 有五家参展商。合格线索应当是制造、建造或 OEM 目标平台的公司，目标平台包括 AUV、ROV 和水下相机；纯分销商、服务商和单纯传感器供应商即使文本中提到目标平台，也应排除。

标准答案包含两家合格参展商。`Abyssal Robotics`（`exh_ms_001`）制造小型 AUV 和巡检级 ROV，且有演示兴趣，因此平台为 `AUV` 和 `ROV`，优先级为 `A`。`KelpLine Cameras`（`exh_ms_002`）是水下相机 OEM，也有演示兴趣，因此平台为 `Underwater Camera`，优先级为 `B`。被排除的近似候选为：`Bluefin Dealer Group`，原因 `distributor_only`；`HarborLab Services`，原因 `service_only`；`Salinity Logic`，原因 `sensor_vendor_only`。汇总计数为合格总数 `2`，平台计数 `AUV: 1`、`ROV: 1`、`Underwater Camera: 1`，优先级计数 `A: 1`、`B: 1`、`C: 0`，近似候选排除总数 `3`。

评估包含六个精确匹配评分点，原始权重为 `[3, 3, 2, 2, 2, 1]`。SP001 检查合格参展商集合；SP002 检查每个合格参展商的平台标签；SP003 检查合格线索的展位、国家和网站补充字段；SP004 检查被排除近似候选集合及原因枚举；SP005 检查优先级；SP006 检查汇总计数。评估器按 `company_id` 归一化公司记录，去除简单文本首尾空格，并允许网站末尾斜杠差异，其余结构化结果要求精确匹配。标准答案应得分 `1.0`。

此训练任务用于让模型通过真实任务和答案对比归纳可迁移经验，而不是作为教程：识别制造商/OEM 资格，排除转售商和服务商，使用受控平台标签，利用会议兴趣信号判断优先级，并保留可导入 CRM 的补充字段。常见错误包括因为 Bluefin 提到 ROV/AUV 就误判为合格，因为 Salinity Logic 销售溶解氧传感器就误判为目标平台厂商，遗漏作为相机 OEM 的 KelpLine，或输出不在受控枚举内的自由文本标签。

构造记录：作者 `task-builder train_002`；创建日期 `2026-06-01`；更新日期 `2026-06-01`；主要变更包括创建提示、答案模板、双语备注、标准答案，以及对应六个计划评分点的本地规则评估器。
