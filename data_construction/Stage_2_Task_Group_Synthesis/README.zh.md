# Stage 2: Task Group Synthesis

语言：[English](README.md) | [中文](README.zh.md)

第二阶段把场景记录扩展成完整任务组。任务工厂会为每个场景构建一个共享业务环境、5 个训练任务、5 个保留测试任务、参考答案、任务说明和基于规则的评测器。

本目录包含两个工作区：

- [`task_factory/`](task_factory/) 是英文任务组生成工作区。
- [`task_factory_zh/`](task_factory_zh/) 是中文镜像工作区。

运行前请先阅读对应工作区的 README 和 guides。生成的任务组应写入工作区的 `task_group/` 目录，然后进入第三阶段做质量过滤。
