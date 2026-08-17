# 核验记录 —— `iclr2027-artifact`

下列每一道门禁在第一次删除**之前**于 `master@cc797ffe` 上就是绿的，现在依然是绿的。
用所示命令即可全部重跑；每一项都是确定性的，不需要 EDA 工具、不联网、不调用模型。

记录于 `dd867c84`（分支 `iclr2027-artifact`），切自 `master@cc797ffe`。

**这是一份快照，其中有两行此后被有意改动。** 分支随后做了一次新的手稿冻结（v13），因此下文的 PDF 行记录的是
v12（15 页，`bbf948bf…`）而不是当前产物，pytest 计数也随同期新增的测试一起增长。这些数字按当时的测量原样保留
—— 本文件要主张的是"瘦身没有改变 `master` 的基线"，改写它的测量会毁掉这一主张。当前投稿的哈希与页数见
[`submission/FREEZE_HASHES.md`](submission/FREEZE_HASHES.md)。

英文版：[VERIFICATION.md](VERIFICATION.md)。

## G1 —— 冻结成员（`scripts/frozen_membership_verify.py`）

重新哈希 `reports/evidence/` 下运行前清单记录的每一条 `path → sha256` 钉，并要求计数与
`docs/frozen_membership_baseline.json` 完全一致。**报告非零才是对的** —— 每个计数为何合法地非零，
见该文件。

```
pinned paths : 1065
missing      : 9
    tasks/p16_spice_handoff/p16_eval_0001_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0001_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0001_typedcontract/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0002_typedcontract/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_base/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_bundles/files/circuit_built.sp
    tasks/p16_spice_handoff/p16_eval_0003_typedcontract/files/circuit_built.sp
mismatch     : 2
    generators/p15_sta_handoff_gen.py  now 2784bc1158fd  pinned e0a68acb9198
    generators/p16_spice_handoff_gen.py  now 8954b666af74  pinned 4083a9dbdde7
multi-sha    : 1
    scripts/phase5c_run.py
```

## G2+G3 —— `scripts/check`（pytest、任务结构、保管钉）

```
$ scripts/check
== [1/3] pytest (tool-free unit suite; -m 'not requires_tools') ==
482 passed, 2 skipped in 86.75s (0:01:26)

== [2/3] structural dataset validation (schema + files + golden present) ==
p13_trajectory_handoff       1     1/1
p14_workflow_handoff        27    27/27
p15_sta_handoff             46    46/46
p16_spice_handoff           10    10/10
ALL STRUCTURALLY VALID (schema + required files + golden present).
TOTAL: 84/84 valid

== [3/3] frozen membership (path->sha256 pins under reports/evidence/) ==
(the G1 output above, verbatim)
frozen membership matches the recorded baseline

CHECK PASSED
```

## G4 —— 研究 I 台账可从冻结记录重算

```
$ python3 scripts/phase7c_study1_ledger.py --check
  "correct": 41,
  "axis_binding_failure": 24,
  "role_conditioned_value_selection_failure": 5,
  "cells": 21,
  "program_primary": 58,
  "controlled_pair": 12,
  "total": 70
}
```

## G5 —— 论断统计量可从冻结记录重算

```
$ python3 scripts/phase7c_claim_statistics.py --check
{"ok": true, "sta_delta_pp": 12.5, "sta_band_pp": [-12.5, 41.7], "pilot_delta_pp": -16.7, "fisher": {"S0": 0.4, "S1": 0.4, "S2-M": 1.0}, "resolved_snapshot_retained": false}
```

## G6 —— 手稿逐字节可重建

去数 pdflatex 的**启动横幅**，而不是相信"日志存在"：`make clean` 会保留 `main.pdf`，因此其后直接
`make` 是空操作 —— 曾有一次 v9 的页数测量正因如此取自过期 PDF。

```
$ cd submission && make distclean && make
pdflatex start banners : 3
Output written on main.pdf (15 pages, 268459 bytes).
sha256                 : bbf948bfc533e3162eef4a299a1215b2664b0d3189bccc51ed65d257aba7a2e1
git status after build : clean (the rebuild is byte-identical)
```

## G7 —— 无悬空仓库路径引用（`scripts/slim_link_check.py`）

解析所有被保留文件引用到的仓库路径。`reports/evidence/**` 免检（已冻结且无法修补；改由 G1 覆盖）。
脚本内有 15 条白名单 —— 看起来像路径的散文、一个可选的人工提供输入，以及设计文档中被实现改名的
计划文件名 —— 每条都就地记录了理由。

```
scanned 4160 tracked files; 1075 references resolved
no dangling repository references
```

## G8 —— 差异只包含它应该包含的东西

```
删除 21577 个文件
新增 18 个文件
修改或重命名 35 个文件

跟踪文件：25722 -> 4164（-83.8%）
跟踪字节：43.2 MB -> 18.5 MB
```

那个已知会反复出现的污染触发线全程守住了：
`tasks/p14_workflow_handoff/workflow_handoff_0009/solution/flow_config.json` 从未变成 `{}`
（由 `test_canonical_golden_fingerprint_intact` 守卫，它在 G2 中运行）。

## 本分支复现的基线

| 门禁 | `master@cc797ffe` | 本分支 |
|---|---|---|
| 冻结成员 | 1065 / 9 / 2 / 1 | 1065 / 9 / 2 / 1 |
| pytest（无工具） | 1133 通过，0 失败 | 482 通过，0 失败（35 个测试文件随其覆盖的 track 与模块一并移除） |
| 结构性任务校验 | 2985 / 2985 | 84 / 84 |
| 台账 `--check` | 58 + 12 = 70 | 58 + 12 = 70 |
| 论断统计 `--check` | 12.5 / [-12.5, 41.7] / -16.7 | 12.5 / [-12.5, 41.7] / -16.7 |
| PDF | 15 页，268 459 B，`bbf948bf…` | 15 页，268 459 B，`bbf948bf…` |
| 悬空引用 | 50 | **0** |
