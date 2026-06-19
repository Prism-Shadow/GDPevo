# Stage 3: Quality Filtering

语言：[English](README.md) | [中文](README.zh.md)

第三阶段用于在发布前审核候选任务组。审核智能体会检查目录结构、文件完整性、隐藏规则是否正确埋入、评测器是否可复现，以及训练/测试拆分是否真的能衡量自进化能力。

本目录包含 [`review_workspace_zh/`](review_workspace_zh/)，用于执行中文质量过滤。英文镜像见 [`review_workspace/`](review_workspace/)。候选任务组应复制到工作区的 `task_group/` 目录。审核结果和临时检查材料留在工作区内，只有通过阈值的任务组才进入发布流程。
