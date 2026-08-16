**[English](incident_golden_corruption.md) | 中文**

# 事件：规范 golden 被截断为 `{}` —— 根因与修复

**状态：** 已解决，2026-08-12。**科学影响：无** —— 污染从未进入任何 commit，因此没有任何冻结实验、证据清单或投稿产物受影响。

## 概要

`tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` —— p14 受控对的规范 golden —— 反复被截断为两个字节 `{}`。有几周时间，它被认为是某个*未识别的外部进程*每隔几小时写一次。

它不是外部的。写入者是**本仓库自己的测试套件**：`tests/test_fullpath_check.py` 中有四条形如下面的语句

```python
(L2.G.TRACK / L2.REFERENCE_TASK / "solution" / "flow_config.json").write_text("{}")
```

它们解析到真实的规范路径。既没有 `tmp_path` 隔离，也没有清理，因此**每一次** `pytest` / `scripts/check` 运行都会污染该文件，并让它保持被污染的状态。

## 证据

单文件运行，不动其他任何东西：

| | sha256 | 字节数 | 内容 |
|---|---|---|---|
| 之前 | `c80812cce61d10c1…` | 249 | 有效，7 个键 |
| 运行 `pytest tests/test_fullpath_check.py` 之后 | `44136fa355b3678a…` | 2 | `{}` |

`44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a` 正是 `{}` 的 sha256。

## 这纠正了什么

1. **"每隔几小时"是观察造成的假象。** 真正的触发条件是*每次测试运行*。2026-08 仓库整理期间的五次复发，恰好对应提交 A/B/C/D/F 之前的五次 `scripts/check` 调用。
2. **看起来"精准定向"其实平淡无奇** —— 是一条硬编码路径，而不是有选择性的写入者。
3. **那次约 21 小时的"b04 宕机"就是这个 bug。** `scripts/fullpath_check.py` 钉住了 `REFERENCE_FC_HASH = c80812cc…`（健康时的哈希）。一次测试运行之后指纹不匹配，于是 `config_fingerprint_ok=False` → `healthy=False`。b04 全程都是健康的。
4. **不需要任何主机级取证。**（备忘：本主机没有免密 `sudo`，也没有 `inotifywait`/`auditctl`/`fatrace`，所以 `inotify` 时序加 Linux 审计归因本来也做不到。`inotify` 也无法指出写入进程的名字；只有审计/eBPF 路径才行。一次针对字面量 `{}` 写入的静态搜索几分钟就找到了原因。）

## 修复

`check()` 只要求参照的 `solution/flow_config.json` **存在且可解析** —— 测试本来就把 `hashlib.sha256` 打了桩并设 `REFERENCE_FC_HASH="x"`，所以它的内容无关紧要。往规范目录树里写入毫无用处。

- `fake_track` 夹具把 `G.TRACK` 重定向到一个含替身文件的 `tmp_path` 目录树；规范数据集不再被触碰。
- `stub_fingerprint` 夹具消除了哈希打桩的四处重复。
- **新增触发线** `test_canonical_golden_fingerprint_intact`：使用真实的 `G.TRACK` 与真实的 `hashlib`，断言规范 golden 仍与冻结指纹一致。此后任何写入规范数据集的测试或工具都会立即失败，而不是静默污染、几天后再以"假的工具宕机"重新冒出来。已验证它会触发：把文件弄坏后，它会带着期望/实际哈希失败。

结果：`pytest tests/test_fullpath_check.py` → 7 通过，规范 golden 逐字节不变。

## 无法就地施加的纠正

`scripts/canonical_integrity.py` 的模块 docstring 仍写着"某个未识别的外部进程不断改写冻结的 golden……（每隔几小时）"。**这句话现在已知是错的，而它必须留着。** 该文件当前的 sha256 `bd946813e9c2ee6f704f26505ae3ae4d316258ddf21611c9b1094967838e6748` 被四份冻结清单钉住：

- `reports/evidence/p14_phase4y3_c24_bridge/membership_code_manifest.json`（`committed_membership_code_sha256`）
- `reports/evidence/p14_phase4y3_c24_bridge/canonical_integrity_manifest.json`（`code_hashes`）
- `reports/evidence/phase5d_freeze/phase5d_freeze.json`（`custody_manifest.code_hashes`）
- `reports/evidence/phase5b_custody_manifest.json`（`code_hashes`）

哪怕只改一条注释，也会让这四份证明全部失效。冻结产物记录的是冻结时所相信的内容；本文档才是有案可查的纠正。

另有两处沿用了已被取代的归因，理由相同，或作为历史保留：

- `reports/synthetic_p14_phase4z_synthesis.md` §7 第 8 项（"未解决的外部写入者……未根因定位"）。它同样**被哈希钉住**：其 sha256 `92ed19d26e8ca62d…` 记录在 `reports/synthetic_p14_phase4z_freeze_manifest.json` 中。原样不动；由本文档取代。
- 一份历史 Phase-6 手稿草稿，重复了同样的归因。它随研究编年史的其余部分在本分支上被移除（见 `docs/REMOVED.zh.md`）；它在 `master` 上留存，作为那份草稿曾经如何叙述的记录。

**已投稿的手稿无需改动。** 它从未依赖"外部进程"这一解释：审计表的行文是*"规范源被改写（产物层）"*与*"golden 被改写读作工具宕机"*，§6 说的是*"一次静默的 golden 改写会伪装成长达一天的工具宕机"*。这些陈述不含归因，且依然为真 —— 变的只是写入者的身份，而抓住它的那个控制措施与所描述的完全一致。已通过对 `submission/main.pdf` 抽取文本核实："unidentified"与"external process"出现次数均为零。

**完整性守卫本身依然完全站得住。** 它的目的从来不限于这一个写入者：它防御的是对规范目录树的*任何*写入，包括某个 agent 用混淆过的绝对路径发起的 `RUN`；而且它在发生改动时中止整条链，而不是静默恢复后继续。错的只是它自述的动机。

## 对象数据库

`git fsck --full --strict` → 退出码 0；32 个悬空 commit 与 1 个悬空 tree（此前程序中被删除的 worktree 与分支的残留），没有损坏也没有缺失对象。这是预期状态，且*不是*关于本事件的证据：对一个已经 checkout 出来的文件做外部写入，对象数据库完好无损。`git fsck` 检查的是对象连通性与有效性；工作树指纹守卫检查的是完全不同的东西。两者都需要。

## 可推广的教训

**1. 一个健康检查的可信度，不超过其参照标准被隔离的程度。**
工具健康哨兵的行为完全符合设计：它把参照产物与冻结指纹比对，发现不匹配，报告 `healthy=False`。它是*正确的*，却仍然给出了错误诊断，因为它所比对的那个产物，被它本应独立于其外的测试脚手架改写了。失效不在监控器的逻辑，而在其参照物的保管。一般性地说：

> 一个把系统与参照标准相比对的监控器，只有在该参照标准本身与测试脚手架相隔离时才可被信任。否则监控器会如实报告一次真实的不匹配，却把它归因于错误的子系统 —— 在这里，是约 21 小时的排查指向了一台全程健康的远端工具服务器。

这比"某个外部进程写了一个文件"是更强、更一般的论断，也是值得带进这个基准测量效度装置未来任何扩展中的那一部分：*参照标准的保管是一等的效度层，不是实现细节。*

**2. 当被污染的内容是一个有辨识度的字面量时，先搜那个字面量。**
`{}` 几乎是唯一的指纹。grep `write_text("{}")` / `json.dump({}` 大约两分钟就找到了原因，胜过一整套主机级取证方案（`inotify` 时序、`/proc/*/fd` 快照、定向 `strace`）—— 那套方案要花几小时，而且在本主机上（无免密 `sudo`，无 `inotifywait`/`auditctl`/`fatrace`）根本无法把写入归因到某个进程。先内容，再进程。

**3. "之前已排除"不是证据。** 早前的排查凭一条一般化陈述明确排除了真正的原因：*"所有测试都用 `tmp_path`；`scripts/check` 是无辜的。"* 那条一般化从未针对这一个文件核对过。要问：究竟核实了什么，在哪个具体产物与代码路径上 —— 一个结论只支撑它被检验过的范围，而这正是配套论文以其论断范围格所主张的同一条纪律。（论文刻意**不**把那个结构称作阶梯：要点恰恰在于范围坐标是偏序的，所以拓宽其一与拓宽其二不可比。）

## 长期守则

- 触发线是首要控制。若它触发：用 `git checkout -- tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` 恢复，然后去找新的写入者。绝不提交污染。
- 付费或冻结证据的运行仍然要走精确 commit 的隔离 worktree 与 `scripts/canonical_integrity.py`（每个 episode 前后的哈希核验，`FAILED_INTEGRITY` 停机）。
- 测试绝不允许写入 `tasks/`。改为搭建一份 `tmp_path` 副本，并重定向该模块的 track 根目录。
