# Train 002 Notes - M-NVK-219 Retention/Hold Remediation

## English Audit Notes

Task scope: train_002 asks the solver to review matter `M-NVK-219` for subpoena-retention and legal-hold remediation. Solver-visible files are English-only and do not contain the scored answer or SOP checklist. The only task-local payload is a factual hold intake memo needed to expose the off-site vendor, personal-device hold notice, and Ironvault naming facts that are not fully explicit in the generated API data.

Primary sources used:
- `matters`: `M-NVK-219` has subpoena date `2024-11-22`, hold date `2024-11-25`, deadline `2025-03-14`, and regulator notice flag true.
- `subpoena_categories`: `N-01` lab data, `N-02` communications, `N-03` audit reports, `N-05` former employee/off-site sources, and `N-06` personal devices.
- `production_logs`: `PL-0004`, `PL-0005`, and `PL-0006` identify the core lab, communications, and audit report gaps.
- `retention_rules`: `RR-0001` through `RR-0006` provide the controlling rules for 2019 lab boxes, EHS boxes, voicemail, Teams chat, executive email archive, and environmental audit reports.
- `destruction_events`: `DE-0002` is pre-hold 2019 lab data destruction; `DE-0003` is post-hold EHS correspondence box destruction.
- `collection_events`: `CE-0003` through `CE-0007` provide collection status, quantities, and missing counts.
- `input/payloads/hold_exception_memo.json`: provides off-site vendor hold omission, personal phone/SMS omission, and the Ironvault alias for the seven-year email archive.

Standard-answer rationale:
- `RC-2019-LAB`: Four 2019 lab data boxes were destroyed on `2023-01-18` under a three-year rule before the `2024-11-25` hold. This is a production gap and policy-retention issue, not post-hold spoliation.
- `RC-EHS-BOX`: Two EHS correspondence boxes were destroyed by the vendor on `2025-01-06`, after the hold. This is the critical post-hold preservation issue affecting `N-02` and `N-05`.
- `RC-TEAMS-VOICE`: Communications are incomplete because voicemail has a 90-day overwrite and Teams before February 2022 is likely lost, with `CE-0005` showing 1,300 missing Teams items.
- `RC-EMAIL-ARCHIVE` and `RS-EMAIL-IRONVAULT`: The seven-year executive email archive, named Ironvault in the memo, remains available and overrides active-server purge concerns for `N-02` and `N-05`.
- `RC-AUDIT-OCT2023` and `RS-AUDIT-VENDOR`: The October 2023 environmental audit report should still be retained under the five-year report rule and must be retrieved from the vendor portal.
- `HD-OFFSITE-VENDOR`: The off-site storage vendor was not placed on hold before the January 2025 destruction cycle.
- `HD-PERSONAL-DEVICE`: The hold notice omitted personal phones/SMS even though category `N-06` requests EHS personal-device communications.

Scoring audit:
- 9 exact-match scoring points, total 18 raw points, weights in `{1,2,3}`.
- Evaluator emits normalized `score` from 0.0 to 1.0 plus `earned_points`, `max_points`, and per-point details.
- Self-check against `output/answer.json` returns `score: 1.0`.
- The scored facts include the required lab pre-hold destruction, EHS post-hold destruction, voicemail/Teams gaps, Ironvault seven-year archive, missing October 2023 audit report retained status, personal-device/off-site hold defects, and remediation actions.

## 中文审计说明

任务范围：train_002 要求解题方审查 `M-NVK-219` 的传票留存和法律保全补救问题。解题可见文件只使用英文，且不包含标准答案或 SOP 清单。本地小负载只是事实性保全访谈备忘录，用于补充生成数据中未完全明示的场外供应商、个人设备保全通知和 Ironvault 命名事实。

主要来源：
- `matters`：`M-NVK-219` 的传票日期为 `2024-11-22`，保全日期为 `2024-11-25`，截止日期为 `2025-03-14`，并标记需要监管通知。
- `subpoena_categories`：`N-01` 实验室数据，`N-02` 通信，`N-03` 审计报告，`N-05` 离职员工和场外来源，`N-06` 个人设备。
- `production_logs`：`PL-0004`、`PL-0005`、`PL-0006` 指向实验室、通信和审计报告缺口。
- `retention_rules`：`RR-0001` 到 `RR-0006` 是 2019 实验室盒、EHS 盒、语音信箱、Teams 聊天、高管邮件归档和环境审计报告的控制性规则。
- `destruction_events`：`DE-0002` 是保全前的 2019 实验室数据销毁；`DE-0003` 是保全后的 EHS 通信盒销毁。
- `collection_events`：`CE-0003` 到 `CE-0007` 给出收集状态、数量和缺失数量。
- `input/payloads/hold_exception_memo.json`：补充场外供应商保全遗漏、个人电话/SMS 保全遗漏，以及七年邮件归档的 Ironvault 别名。

标准答案理由：
- `RC-2019-LAB`：四盒 2019 实验室数据在 `2023-01-18` 按三年规则销毁，早于 `2024-11-25` 的保全日期。这是生产缺口和政策留存问题，不是保全后毁损。
- `RC-EHS-BOX`：两盒 EHS 通信材料在保全后由供应商于 `2025-01-06` 销毁，影响 `N-02` 和 `N-05`，属于关键的保全后问题。
- `RC-TEAMS-VOICE`：通信来源不完整，因为语音信箱 90 天覆盖，2022 年 2 月前 Teams 可能丢失，`CE-0005` 显示 Teams 缺失 1,300 项。
- `RC-EMAIL-ARCHIVE` 和 `RS-EMAIL-IRONVAULT`：七年高管邮件归档仍可用，备忘录中称为 Ironvault，因此可覆盖活动服务器清除造成的风险。
- `RC-AUDIT-OCT2023` 和 `RS-AUDIT-VENDOR`：2023 年 10 月环境审计报告应按五年规则仍被保留，需要从供应商门户取回。
- `HD-OFFSITE-VENDOR`：场外存储供应商未在 2025 年 1 月销毁周期前被纳入保全。
- `HD-PERSONAL-DEVICE`：保全通知遗漏个人电话和 SMS，而 `N-06` 明确请求 EHS 个人设备通信。

评分审计：
- 共 9 个精确匹配评分点，总计 18 个原始分，权重均为 `{1,2,3}`。
- 评估器输出 0.0 到 1.0 的归一化 `score`，并包含 `earned_points`、`max_points` 和逐项细节。
- 使用 `output/answer.json` 自检时返回 `score: 1.0`。
- 评分事实覆盖要求中的 2019 实验室保全前政策销毁、2025 年 1 月保全后 EHS 盒销毁、语音信箱/Teams 缺口、Ironvault 七年归档、仍应保留的 2023 年 10 月审计报告、个人设备/场外保全缺陷，以及补救动作。
