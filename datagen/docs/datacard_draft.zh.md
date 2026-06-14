**[English](datacard_draft.md) | 中文**

# EDA-AgentBench 数据卡片（草案）

## 数据集名称
EDA-AgentBench — SPICE 网表调试任务候选集

## 版本
0.1.0（datagen 模块）

## 描述
用于评估 LLM 智能体在 SPICE 电路仿真网表调试上表现的合成基准任务。（本模块早期还
曾生产 `rtl_debug` 和 `timing_report_qa` 原型；这些领域已退役，现在改由父仓库的
`generators/` 生成。）

## 任务数量
- SPICE 网表调试：100 个候选（`tasks_candidates/`）、100 个已验证（`tasks_validated/`）、10 个已打包公开发布（`tasks_public/`）
- **合计：100 个 SPICE 网表调试任务**

## 领域
| 领域                | 描述 |
|---------------------|------|
| `spice_deck_debug`  | 调试 SPICE 电路仿真网表 |

## 生成方式
所有任务均为合成生成。不包含任何专有电路数据或商业基准内容。

## 验证
- 所有任务均通过静态检查（模式、结构、确定性）验证
- 可选的商业验证支持 VCS、HSPICE、Spectre 和 PrimeTime

## 许可证
Apache-2.0

## 安全性
- 不包含专有 PDK 数据
- 不包含商业工具日志
- 不包含许可证服务器信息
- 所有任务均标记为 `public_release_safe: true`

## 用途
- 评估 LLM 智能体在 EDA 任务上的能力
- AI 辅助硬件设计验证研究
- 在特定领域场景中对智能体推理能力进行基准测试

## 局限性
- 任务为合成生成，可能无法完全代表真实场景的复杂度
- 商业验证需要已授权的 EDA 工具
- 尚未实现开源工具验证
