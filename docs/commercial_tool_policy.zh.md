**[English](commercial_tool_policy.md) | 中文**

# 商业工具政策

## 概述

这些任务家族专为商业 EDA 工具设计。没有开源 EDA 替代方案可以顶替，理由是具体的而非偏好：被研究的构念是一个**能被真实工具签核为绿**的绑定。没有商业签核，类型化 oracle 就无从与之相左，论文所测量的那一整类失败也就不存在了。

## 这些家族需要的工具

| 工具 | 供应商 | 使用者 | 在测量中的角色 |
|------|--------|---------|-------------------------|
| PrimeTime | Synopsys | p14 workflow、p15 STA（家族 A） | 对设计做时序分析并签核证据链；错绑定的包同样会签核为绿 |
| HSPICE | Synopsys | p16 SPICE（家族 B） | 仿真 deck 并产出数值；错绑定同样能产出这些数值 |

除此之外别无所需。`master` 上另外还用 VCS、Spectre、Design Compiler、SpyGlass、ICC2、Innovus、StarRC、Sentaurus、Xcelium 与 Verdi 服务 P1–P9 基准 track，这些不在本分支上（见 [REMOVED.zh.md](REMOVED.zh.md)）。

## 工具检测

基准测试在运行时探测文件系统中的工具。任务定义中不硬编码任何工具路径。

```bash
eda-bench detect-tools
```

预期安装位置（探测而非硬编码）：

```
Synopsys: /EDA/soft2/synopsys/
Cadence:  /EDA/soft2/cadence/
```

检测脚本在这些根目录下搜索工具二进制文件并报告可用性。需要不可用工具的任务在评估时会被跳过。

## 许可

所有受支持的工具都需要商业许可证。基准测试：

- 不打包或重新分发任何 EDA 工具二进制文件
- 不包含许可证文件或许可证服务器配置
- 不在任务文件中存储许可证服务器名称（已从日志中清理）
- 假设主机环境具有被评估工具的有效许可证

用户在运行评估前必须确保拥有适当的许可证。

## 日志清理

EDA 工具输出通常包含环境特定信息。在存储或共享任何日志之前，清理器会替换：

| 模式 | 替换 | 示例 |
|---------|-------------|---------|
| 用户名 | `<USER>` | `/home/jdoe/project` → `/home/<USER>/project` |
| 主机名 | `<HOST>` | `server01.company.com` → `<HOST>` |
| 绝对路径 | `<PROJECT_ROOT>`、`<EDA_ROOT>` | `/EDA/soft2/synopsys/vcs/...` → `<EDA_ROOT>/vcs/...` |
| 许可证服务器 | `<LICENSE_SERVER>` | `license.company.com` → `<LICENSE_SERVER>` |
| 机器名 | `<HOST>` | 工具输出中的 `hostname` → `<HOST>` |

这使得评估日志可以公开共享而不会泄漏基础设施详情。

## 无开源替代方案

基准测试有意不支持开源 EDA 工具（如 Icarus Verilog、Ngspice、Xyce）。理由如下：

1. 基准测试评估的是使用商业工具链的能力，商业工具在工业 EDA 工作流程中占主导地位。
2. 商业工具与开源替代方案在错误信息、行为和功能上有所不同。
3. 任务生成器和评估器针对商业工具输出格式进行了调优。
4. 支持开源工具需要单独的评估器，并会削弱基准测试的工业相关性。

## 环境设置

用户应当：

1. 在预期根目录下安装商业 EDA 工具（`/EDA/soft2/synopsys/`、`/EDA/soft2/cadence/`）。
2. 按工具供应商要求设置许可证环境变量。
3. 运行 `eda-bench detect-tools` 验证可用性。
4. 运行冒烟测试确认工具端到端正常工作。
