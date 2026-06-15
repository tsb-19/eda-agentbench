**[English](roadmap.md) | 中文**

# 路线图

## 已完成

- **阶段 0 (P0)**：统一基准测试框架、CLI、schema、评估器
- **阶段 1 (P1)**：RTL 调试（1001 个任务：1 个手工制作 + 1000 个生成）
- **阶段 2A–E**：HSPICE/Spectre 冒烟、SPICE 评估器、数据集 + 报告 CLI、受控扩展
- **阶段 4A–F**：P2 测试平台/SVA 生成、P3 时序报告问答、文档/数据卡/发布政策、集成审计、P2 命名清理、采样评估模式
- **阶段 5A/B/E/F**：P3 扩展至 1008、P2 扩展至 101、PrimeTime 原型（8 个任务）、P5 扩展至 100
- **阶段 6A/B/C/D**：P4 扩展至 302（RC 上升/下降 + RLC）、P6 DC 综合问答（51）、P6 DC 约束调试（13）、基线运行器 + 排行榜
- **阶段 7A/B/C**：P7 SpyGlass Lint 调试（16）、P7 PrimeTime STA 调试（17）、Agent 运行器 MVP
- **阶段 8A**：P8 PnR 报告问答原型（101 个任务）
- **阶段 8B**：规模化真实工具调试赛道 — P6 DC 约束 13→61、P7 SpyGlass 16→50、P7 PrimeTime 17→53（均在真实工具上经 b04 验证）

合计：**10 条 track 共 2828 个任务**。实时清单参见 [current_status.md](current_status.md)。

## 后续阶段

### P5 Spectre 方言
- Spectre 方言的 SPICE 网表修复（P5 当前仅支持 HSPICE）

### 专家级物理设计 track
- ICC2 / Innovus 布局布线执行任务（超越 P8 报告问答）
- StarRC 寄生参数提取
- Sentaurus TCAD

### Agent 与评分基础设施
- 带逐次工具调用记录的交互式 agent 循环（超越当前 MVP）
- LLM 评判的解释评分（当前在提交模式下默认为 1.0）
- 排行榜 / API 提交基础设施
