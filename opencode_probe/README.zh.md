**[English](README.md) | 中文**

# `opencode_probe/` —— 外部 scaffold 臂自己的根目录

本目录存放 OpenCode 外部 scaffold probe 产出的一切。它位于仓库根下，刻意**不**放在 `reports/` 里面，
理由与 [`phase8a/`](../phase8a/README.zh.md) 相同：`scripts/frozen_membership_verify.py` 会扫描整个
`reports/` 寻找 `path → sha256` 对，因此写在那里会改变冻结的钉数。Phase-8A 的一份早期稿本曾写进
`reports/`，把计数从 1065 推到 1979，还悄悄把两处预期不匹配之一"解决"掉了。

## 这个臂是什么，不是什么

它是一项**单独命名的研究**，由 `CLAUDE.md` 硬约束 1 在 `a89e084` 冻结之后授权。那个程序保持关闭；
本目录中的任何东西都不得与论文报告的任何数字求和、求均值或相减。

它**不是**对"scaffold effect"的测量。OpenCode 必然会替换动作面与提示框架，而论文 §2 把这两项都算作
task information，所以 `OpenCode − 受控 runner` 不是 scaffold effect，也从不被计算。被估计量是
**OpenCode 内部的处理效应**。见
[`docs/opencode_probe_analysis_plan.zh.md`](../docs/opencode_probe_analysis_plan.zh.md)（它在任何 outcome
存在之前就固定了问题），以及
[`docs/opencode_scaffold_probe_scope.zh.md`](../docs/opencode_scaffold_probe_scope.zh.md)（接入面）。

## 布局

```
config/opencode.json     被钉住的 OpenCode 配置；每一个值都靠读回来断言
evidence/preflight.json  零调用 preflight 记录 —— 配置、文件系统与沙箱检查
```

`config/opencode.json` **不含任何密钥**。provider 通过 OpenCode 的 `env` 字段从 `API_KEY` 环境变量取
密钥，因此密钥从不写入此处任何文件，而 preflight 会断言解析后的 provider 块中不含字面密钥。

## 状态

**什么都还没跑。** 没有模型调用，没有 episode。零调用 preflight 五项检查中通过四项；第五项 ——
oracle 的文件系统隔离 —— 被阻塞，因为 `bwrap` 在本机无法创建 user namespace
（`kernel.apparmor_restrict_unprivileged_userns=1`，且 `bwrap` 不是 setuid）。那一项属于 probe 不可缺少
的三项之一，因此本臂就此停住，等待范围审计 §8 中所记录的那个决定。

## 复现 preflight

```bash
export PATH="$HOME/.opencode/bin:$PATH"
python3 scripts/opencode_probe_preflight.py          # 零模型调用
python3 scripts/opencode_probe_preflight.py --json   # 机器可读
python3 -m pytest tests/test_opencode_probe.py -q    # 方案与结论范围守卫
```
