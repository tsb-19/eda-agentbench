**[English](commercial_tool_adapters.md) | 中文**

# 商业工具适配器

## 概述

每个适配器封装一个商业 EDA 工具的调用，负责：
- 从环境变量构建命令
- 超时控制
- 捕获退出码
- 原始日志存储（存放在 `.local_runs/` 下）
- 日志规范化（去除专有信息）
- 生成验证记录

## 适配器架构

```
validators/
  common/
    run_command.py       # 通用命令执行器，支持超时
    log_normalizer.py    # 日志清理工具
    validation_record.py # 记录创建与验证
  vcs/
    validate_rtl.py      # VCS 编译与仿真
  hspice/
    validate_spice.py    # HSPICE 仿真
  spectre/
    validate_spectre.py  # Spectre 仿真
  pt/
    parse_report.py      # PrimeTime 报告解析
```

## 环境变量

| 变量               | 说明                          | 示例 |
|------------------|-------------------------------|------|
| `EDA_VCS_CMD`    | VCS 可执行文件路径/命令          | `<设置为你的 VCS 路径>` |
| `EDA_HSPICE_CMD` | HSPICE 可执行文件路径/命令       | `<设置为你的 HSPICE 路径>` |
| `EDA_SPECTRE_CMD`| Spectre 可执行文件路径/命令      | `<设置为你的 Spectre 路径>` |
| `EDA_PT_CMD`     | PrimeTime 可执行文件路径/命令    | `<设置为你的 PrimeTime 路径>` |

## 优雅跳过行为

当环境变量未设置时：
1. 输出：`[SKIP] EDA_<TOOL>_CMD not set, skipping <tool> validation`
2. 以退出码 0 退出
3. 不创建验证记录

## 日志规范化

`log_normalizer` 模块会移除：
- 匹配许可证横幅模式的行
- 主机名引用
- 用户名引用
- 绝对路径前缀
- 工具版本横幅
- 时间戳模式

规范化在存储验证记录之前执行。SHA-256 哈希基于原始（规范化前）日志计算。
