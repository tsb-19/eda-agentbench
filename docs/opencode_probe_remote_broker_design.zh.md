**[English](opencode_probe_remote_broker_design.md) | 中文**

# 用于 OpenCode probe 的受限 SSH EDA broker

**状态：设计稿，日期 2026-08-21。本文不授权正式的 48 episode 实验臂。** 它只处理该实验臂无法启动的其中
一个原因——即 [`opencode_probe_dry_run_report.zh.md`](opencode_probe_dry_run_report.zh.md) §5 记录的那
个阻塞项——其余原因原样保留。Check 7 仍为 UNSETTLED。Check 5 **不继承**先前的 PASS：那次 PASS 是在
"工具不挂载"的配置下取得的，而本设计改变了该配置，因此 check 5 必须在新配置下重新建立。在零调用的
remote-broker preflight 通过之前，不得花费任何模型调用。

治理文件维持不变，也不作重新解释：
[`opencode_probe_analysis_plan.zh.md`](opencode_probe_analysis_plan.zh.md)（预注册）与
[`opencode_scaffold_probe_scope.zh.md`](opencode_scaffold_probe_scope.zh.md)（接入范围，九项结构性检
查）。下文任何内容都不触碰 `a89e084` 实验计划。

## 1. 问题

本机上的 EDA 工具是远程的。一个私有 forwarder 通过 `rsync` 把 `$PWD` 镜像到 `tsb@b04`，在那边的 login
shell 下运行工具，再把结果同步回来。若要让 OpenCode agent 拿到真实的 public 工具反馈，就必须把该
forwarder 和 `~/.ssh` 挂进沙箱——而这等于把 `ssh tsb@b04` 交给 agent，也就是在"评分会把 oracle 落盘到
那台机器上"的主机上获得任意命令执行能力。

因此两项要求直接冲突，dry run 把冲突的两侧都测到了：

| 配置 | Check 2（工具反馈） | Check 5（oracle 隔离） |
|---|---|---|
| 工具不挂载——即 dry run 采用的配置 | **失败**：`run_public.sh` 返回 `SKIP` | **通过** |
| 工具挂载，forwarder 保持原样 | 会通过 | **失败**：可经 ssh `cat /tmp/eda_shim_*/signoff_intent_truth.json` |

这个泄漏是**跨 episode** 的，不只是 episode 内部的：给 episode *N* 评分会把该 instance 的 truth 文件
留在远端，同一 instance 的 episode *N+1* 就能读到。dry run 当时 b04 上留有 1501 个 `eda_shim_*` 工作
目录，其中含 1049 份 `run_hidden` 脚本、1049 份 grader 副本与 1049 份 truth 文件。这些现已清除，但
**清理 `/tmp` 是必要而不充分的**——下一次评分又会重新生成，所以真正的修法必须是：agent 可达的任何操作
都无法读到它们。

## 2. broker 是什么

它是一种**能力（capability）**，而不是一条通道。我们不是先给 agent 一条到 b04 的路再去限制它，而是只给
它两个具名操作，并且不留下表达其他任何东西的语法。

三种凭据，三种作用域：

| 谁 | 凭据 | 能做什么 |
|---|---|---|
| 宿主机，沙箱之外 | 正常的 `~/.ssh` | 一切；负责 episode 的开通与拆除 |
| Agent，沙箱之内 | 每 episode 一把 ed25519 probe key | 两个具名操作，且只对一个 episode 有效 |
| Grader，沙箱之外 | 正常凭据，冻结路径不变 | 不变 |

### 2.1 密钥即 episode

probe key 每 episode 生成一把，拆除时销毁。它在 `authorized_keys` 里的那一行把 episode id 写进
**forced command 内部**，因此 agent 无法选择 episode——根本没有可以填写 episode 的字段：

```
restrict,from="<host-ip>",command="/home/tsb/eda-probe-broker/broker.sh <episode_id>" ssh-ed25519 AAAA… probe-<episode_id>
```

`restrict`（OpenSSH ≥ 7.2）蕴含 `no-pty`、`no-X11-forwarding`、`no-port-forwarding`、
`no-agent-forwarding` 与 `no-user-rc`。之所以用它而不是逐项列出这五个选项，是因为它**默认拒绝**：未来
OpenSSH 新增的选项默认被拒，除非这一行显式重新开启；而逐项枚举则会悄悄获得后来发明的任何能力。

真正干掉 `scp`、`sftp` 与 `rsync` 的是 `command=`。这三者都需要在远端启动自己的服务端程序
（`scp -t`、`sftp-server`、`rsync --server`），而它们永远得不到启动的机会。`from=` 用于钉住来源地址，
属于纵深防御，不承担主要防护职责。

吊销是精确的：删掉那一行，密钥即刻失效。并发的 episode 各自拥有独立的行、独立的密钥与独立的 id。

**这一行位于一个带定界符的受管区块内，区块之外的任何内容永远不会被重写。**

```
# BEGIN EDA-OPENCODE-PROBE
# probe-entry {"episode": "…", "added": "…"}
restrict,command="/home/tsb/eda-probe-broker/broker.sh …" ssh-ed25519 AAAA… probe-…
# END EDA-OPENCODE-PROBE
```

这件事之所以重要，是因为 b04 的 `~/.ssh/authorized_keys` 里有**两把真实的用户密钥，共 687 字节**——一把
`ssh-rsa`、一把 `ssh-ed25519`，以及一个末尾空行。在那里写坏一半，就会把操作者锁在运行全部 EDA 工具的那
台主机之外。因此每一次改动都是：取互斥锁 → 读取 → 写同目录临时文件 → `fsync` → `os.replace` → 对目录
`fsync` → 释放。失败的改动会让先前的文件保持逐字节不变，并清掉自己的临时文件；拆除 episode A 也永远不会
移除 episode B 的那一行。`audit --reap` 会移除其 episode 已不再存活的受管条目——一把活过了自己 episode
的 probe 密钥，是一份没有任何人持有的能力。

末尾那个空行不是可以顺手"整理掉"的细节：一个把它吃掉的渲染器，会改变操作者唯一真正在意的那块区域。往返
是在那个确切形状上验证的——两把密钥、一个空行、末尾换行——文件回来时逐字节一致。

互斥锁用的是 `mkdir` 而不是 `flock`：b04 上的 `$HOME` 是 NFS（`qhdx.inspurnfs.com:/data/home/b04`），
那里的 `flock(2)` 经由 lock manager 模拟，而 `nfs(5)` 明确声明它既不提供集群一致的缓存，也不保证锁能在
网络分区中存活。

### 2.2 正式实验臂一次性装入全部 48 把密钥

按 episode 的 `add_entry` / `remove_entry` 仍然存在，供 preflight 和任何单 episode 的 dry run 使用——
那些场景只有一个 episode，且有操作者在旁看着。**正式实验臂不使用它们。** 全部 48 把公钥在实验臂开始前
以**一次**原子重写、在**一把**锁的保护下装入，结束后再以一次重写整体移除，因此在整个实验臂期间
`authorized_keys` 是逐字节静止的。每个 episode 的沙箱只挂载属于它自己的那一把私钥。

理由不是"更整洁"。按 episode 的设计需要针对一个其手册本身都不肯为该原语背书的存储层，完成 96 次正确的
互斥操作（48 次装入、48 次移除），而赌注是操作者真实的登录密钥。批量化把它降到两次取锁，且都位于实验臂
的边界——在那里，失败在任何 episode 开跑之前、以及在全部 episode 跑完之后都是可见的。

而且什么都没有牺牲。实验臂需要的性质是

> 持有 episode *i* 的密钥，就只能运行 episode *i*，

这条性质活在每一行的 `command=` 里，而不在这一行**何时**被写入。跨 episode 选择依然无法表达，并发
episode 依然可行，改变的只是行数。

让失败保持安全的是顺序。先校验整份计划，然后生成密钥，然后构造 manifest，然后建立远端 episode 目录——
在这一切之后，才有那唯一一次 `add_entries` 调用。该调用之前的任何失败，都会让**零**把 probe 密钥处于
授权状态。该调用之后**校验**环节的失败，则会回滚这些密钥并拒绝写出 batch 记录——因为"48 把密钥而没有
记录"比"没有密钥"或"48 把密钥并有记录"都更糟。

校验不会重写它正在检查的那个文件。它把受管区块读回来，并要求三件事同时成立：条目集合一致；每一行的
`command=` 只指名它自己的 episode 而非任何别的；以及**非受管区域**的 sha256 与之前相等。最后这个量正是
操作者真正在意的东西，preflight 会对它采样**三次**——批量装入之前、48 把密钥全部在位期间、以及拆除之
后。在批量期间比较整个文件毫无意义；而只比较前后两次，会放过一类 bug：它在整个实验臂期间丢掉了一把用户
密钥，却在结束时又放了回去。

只要 `opencode_probe/broker/batch.json` 存在，`provision` 与 `teardown` 就会拒绝运行。这就是让
"实验臂期间 `authorized_keys` 保持静止"成为一条**机械性质**而非一项意图的东西：没有任何重试循环或临时
辅助脚本能悄悄把那 48 次重写重新引入。

### 2.3 互斥锁绝不仅凭时间就打破一把锁

`mkdir(2)` 在其创建这一步上是原子的，而这正是互斥锁所需要的。它**不是**一个正确的分布式锁，而且
`mkdir(2)` 自己也记录了若干 NFS 上的怪异之处，所以过期规则是按"当该原语不成立时仍然安全"来写的。owner
记录携带 `owner_host`、`owner_pid`、`owner_nonce`、`created_at` 与 `heartbeat`，过期时间从 heartbeat 起
算，因此一个合法的长时间操作永远不会被误判为已死。

| 情形 | 处理 |
|---|---|
| 年龄 ≤ `stale_sec` | 等待。绝不打破，即使 owner 可验证地已死。 |
| 年龄 > `stale_sec`，owner 在**本机**且 pid 存活 | 等待。慢不等于死。 |
| 年龄 > `stale_sec`，owner 在**本机**且 pid 已不存在 | 已验证死亡——隔离，然后重新争锁。 |
| 年龄 > `stale_sec`，owner 在别的主机，或记录不可读 | 存活性**无法验证**——用原子 `rename` 隔离，然后重新争锁。绝不就地 `rm`。 |

"年龄超过阈值 ⇒ 删除锁"这条规则被明确否决。它存在竞态：A 仍然活着但很慢，B 仅凭时钟判定 A 已过期，
B 删除了锁，随后 A 与 B 并发重写 `authorized_keys`。隔离堵住了这一点：rename 是原子的，因此恰好只有一个
打破者获胜；而如果旧 owner 其实还活着，它释放时会读取 owner 记录、发现 nonce 不是自己的，于是**什么都
不释放**。被隔离的锁由 `audit` 报告，且永不自动删除——每一个都是"某人的锁被别人夺走了"的记录。

### 2.4 永不读取 `SSH_ORIGINAL_COMMAND`

broker 完全不引用这个变量——不解析、不校验、也不记录。一个会检查 `SSH_ORIGINAL_COMMAND` 的 forced
command，实质上是把任意命令通道重建了出来、只是在前面加了个过滤器；而任何这样的过滤器，都离"被一个引号
转义 bug 绕过"只有一步之遥。操作的选择改为来自 **stdin** 上的结构化请求，于是攻击者能控制的只剩一份必
须满足白名单的 JSON 文档。

## 3. 协议

每个连接一个请求，走 stdin，带长度分帧并设有上界。帧格式为 `EDABROKER1 <n>\n<n 字节 JSON>\n`：b04 的
登录 shell 自己会写出 banner 和一句 `lsof: command not found`，分帧让被污染的流成为一次**被检测到的**
传输失败，而不是一个无从解释的解析错误。对付 banner 噪声的正确手段是协议层，不是 grep。

```json
{"op": "sta_public",
 "inputs": {"exception_config.json": "<base64>", "run_public.tcl": "<base64>", "…": "…"}}
```

响应走 stdout，同样带分帧：

```json
{"op": "sta_public", "rc": 0, "stdout": "…", "stderr": "…",
 "artifacts": {}, "invocation": 3, "elapsed_s": 41.2}
```

**客户端提供的文件名永远不会被当作路径使用。** broker 校验输入的键集合与该操作声明的集合**完全相等**
——不是超集，也不是子集——每个键都必须匹配 `^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$`，并且 `.` 与 `..` 被显式
排除，因为它们是合法的 basename 却不是文件。随后每个被接受的输入都被写到 broker 自己表里早已知道的名字
下。路径穿越不是靠清洗 `../` 来防御的，而是**根本无法表达**，因为客户端的字符串从不抵达文件系统。

**不存在任何形式的归档解包。** `tar xf -` 是被"没有"，而不是被"加固"，这个设计决定值得明说：一个由
agent 控制的归档可以携带 `../`、绝对路径、符号链接和硬链接，而这每一种形态，一份裸文件名的白名单根本就
不具备。加固解包器意味着穷举各种花招；不具备解包器意味着根本没有可穷举的东西。

### 3.1 输入分类

每个 public 文件恰好落入以下三类之一，类别决定 broker 的处理方式：

| 类别 | 例子 | broker 行为 |
|---|---|---|
| **editable** | `exception_config.json`、`meas_config.json` | 原样接受 agent 的字节——这正是干预本身 |
| **canonical** | `run_public.tcl`、`build_applied_sdc.py`、`design.v`、`tiny.db`、`circuit_core.sp` | 对照钉死的 manifest 校验 sha256；**不一致即拒绝** |
| **generated** | `agent_applied.sdc`、`circuit_built.sp` | 根本不上传；由 canonical 脚本在远端重新生成 |

每个 family 的 editable 集合只有一个文件。工具会读取的其余一切都是 canonical，并由 manifest 钉住。
`tiny.lib` **不是** `sta_public` 的输入：`run_public.tcl` 设置 `link_path "* tiny.db"` 并读取
`tiny.db`。`parse_measure.py` 同样不是 `spice_public` 的输入——它在本地对返回的 `.lis` 运行。

### 3.2 不一致在执行期被拒绝，并被记录

```
broker: REFUSED op=sta_public reason=NON_EDITABLE_DIVERGENCE
        file=run_public.tcl canonical=sha256:9f2c… supplied=sha256:41ab…
```

没有任何东西被送到 b04，而该次尝试会写入 episode 记录。这**比冻结 runner 更严格**：后者把 `$PWD` 里的
一切照单上传，靠 `check_tcl_injection` 与 `detect_forbidden_modifications` 在*评分期*抓篡改。当后果只是
分数变差时，事后检测是够用的；当后果是 agent 读到了 oracle 时就不够用了，因为事后检测到"读过"并不能把
它"读回去"。

评分期的反作弊未作改动，仍然运行。broker 的拒绝是一个额外的、独立的事件，并按独立事件记录。

### 3.3 manifest 从哪里来

沙箱不挂载任何 task 树——这正是 check 5——所以客户端无从知道 canonical 字节，也不应被信任去知道。
manifest 由**宿主机**用宿主机的正常凭据、在沙箱启动之前安装到 b04 上。它只包含若干 sha256 值和一个操作
名；不含 oracle，也不含 task 内容，因此它出现在 b04 上本身并不构成泄露。

### 3.4 这种钉住付出了什么代价——明说而非留待推断

broker **把工具权威的输入钉到它们的规范任务版本上**。冻结 runner 并不这样做：它把 `$PWD` 里的一切照单
上传，在评分期才抓篡改。这是动作面上的一处真实差异；既然论文 §2 把动作面本身算作 task information，那
它就应当写在这里，而不是留给读者自己去发现。

因此：**本设计不主张与冻结 runner 之间存在逐字节的动作面 parity。** 在 broker 下，工具调用契约比在
forwarder 下**更加明确**。由此有两个结论，且都按这一强度陈述：

- broker 所禁止的并不是 grader 所禁止的超集，两者也不是同一份清单。对 p15，实测的 `metadata.json`
  `forbidden` 清单是
  `["design.v", "constraints.sdc", "run_public.sh", "run_public.tcl", "tiny.db", "tiny.lib", …]`——
  它**遗漏了** `build_applied_sdc.py`、`partition_pins.json` 与 `intent_exception.json`，而这三者都会被
  `build_applied_sdc.py` 读取，也都会改变真实的 PrimeTime 结果。在冻结 runner 下，一个修改
  `partition_pins.json` 的 agent 会改变工具反馈并且通过反作弊。broker 在执行期就拒绝它。对 p16，
  forbidden 清单本来就是完整的；broker 仍然对两个 family 一视同仁地钉住，因为"grader 恰好禁止了它"与
  "工具根本拿不到它"是两种不同的保证。
- 当后果只是分数变差时，事后检测是够用的；当后果是 oracle 被读到时就不够用了，因为事后检测到"读过"并不
  能把它"读回去"。

评分期的反作弊未作改动，仍然运行。broker 的拒绝是一个额外的、独立的事件，并按独立事件记录。

## 4. 两个操作

操作边界落在 **EDA 工具处**，这样两个 family 的 `run_public.sh` 都能逐字执行，也不必为了迁就 broker 去
改动任何 sha256 钉死的 canonical 文件。

| op | 远端执行，全部为 canonical | 返回 |
|---|---|---|
| `sta_public` | `build_applied_sdc.py` → `pt_shell -f run_public.tcl` | 有界的 stdout/stderr |
| `spice_public` | `build_deck.py` → `hspice -i circuit_built.sp -o hspice_run` | 有界的 stdout/stderr **+ `hspice_run.lis`** |

`parse_measure.py` 被有意排除在 `spice_public` **之外**。它在操作返回之后，用 canonical 字节在本地运行
——这正是 `run_public.sh` 本来就在做的事。把它放进操作内部，就只能二选一：要么解析两次，要么去改一个被
钉死的脚本。

返回的 artifact 按操作逐个白名单化，限定名字与大小上限。`hspice_run.lis` 是原始仿真输出：它已在
`.gitignore` 中，永不入库。

### 4.1 这些上界的具体数值

"有界"若不给出数值就等于没说，因此在此固定下来——而且每一项都由一次**实测**来支撑，记录在
`opencode_probe/evidence/raw_output_audit.json` 中。

| 上界 | 数值 | 实测最大值 | 余量 | 为何取这个值 |
|---|---|---|---|---|
| stdin 上的请求 | 2 MiB | 50 642 B | 41× | 对每个校准目录取上界：整个 `files/` 按 4/3 膨胀 |
| 返回的 `stdout` | 1 MiB | 3 205 B | 327× | 实测的、未经截断的原始 PrimeTime 输出 |
| 返回的 `stderr` | 1 MiB | 0 B | — | 两个 `run_public.sh` 都用 `2>&1` 把 stderr 并入 stdout |
| `hspice_run.lis` artifact | 8 MiB | 4 695 B | 1787× | 实测的原始仿真输出 |
| 远端墙钟 | 180 s | — | — | 与冻结的单命令超时保持 parity |

校准集是两个 family 中每一个含有 `files/run_public.sh` 的 instance 目录——共 56 个——而且**覆盖正式面板
会用到的那 24 个目录是给出结论的前提条件**，不是一项汇总统计。取"恰好跑起来的那些 instance"上的最大值，
与取"恰好跑完的那些 episode"上的聚合，是同一种缺陷。

> 传输上限与观测上限是两个不同层面上的不同量。4000 字节是模型在**一次观测**中能看到多少；传输上限是
> broker **总共**可以返回多少。冻结 runner 允许 agent 把大输出重定向到文件再分页读回，因此一个低于真实
> 输出体量的传输上限，会让 probe 的动作面比对照组**更弱**。这个界因此取自实测的原始输出——在完整校准集
> 上留有 ≥ 8× 余量——而不是取自 `64 KiB / 4000 B = 16`。

这次实测对被取代的那套理由的处置，比反对意见本身还要彻底。真实的 PrimeTime 输出是 3 205 字节，**低于**
冻结 runner 的 4000 字节观测上限。所以"64 KiB 是 4000 B 的 16 倍"不只是在错误的层面上推理：它所依据的那
个观测上限在这些任务上几乎从未起过约束作用，而它本欲论证的那个传输量则从未被测量过。

**以及这套理由的边界，就写在同一个地方。** 在一个有限校准集上的余量**并不**证明某个上限永远不会成为约
束，而本设计也不依赖这样的证明。`1 MiB > 8 × 3 205 B` 是关于 56 个被测目录的事实，不是关于未来每一次
PrimeTime 调用的事实。填补这个缺口的是 §4.2 的运行期行为，它不依赖本次审计是否穷尽。

### 4.2 错误分类，以及为何超限是 fail-closed

六种状态，刻意彼此分开。把其中任意两种合并，都会让一次基础设施故障被记成模型行为，而这正是本项目存在
所要捍卫的测量有效性规则。

| 状态 | 含义 | 客户端退出码 | 是否测量无效 |
|---|---|---|---|
| `ok` | 工具跑了；`rc` 是工具自己的 | 工具的 `rc` | 否 |
| `tool_timeout` | 工具跑了并超出墙钟 | 124 | 否——这是工具事实 |
| `refused` | 请求非法；没有任何东西送到远端 | 126 | 否——这是 agent 事实 |
| `broker_error` | broker 自身失败 | 125 | **是** |
| `transport_error` | ssh 或分帧失败；不是工具结果 | 125 | **是** |
| `transport_output_limit` | 某项输出超过传输上限 | 125 | **是** |

**`transport_output_limit` 是 fail-closed 的，并且根本不存在截断路径。** 超限时响应不携带 `stdout`、不
携带 `stderr`、也不携带 `artifacts`；客户端在 stdout 上什么都不打印，在 stderr 上写
`eda-broker: MEASUREMENT_INVALID transport_output_limit: …`，并以 125 退出。该 episode 作废。

截断方案被考虑过并被否决。它会构成**第二个**观测上限——对 agent 不可见，在冻结实验臂中并不存在，且在日
志里与真实工具输出无法区分。fail-closed 的代价是作废一个 episode；截断的代价是一次看起来干净的、被污染
的测量。这一不对称就是全部论证。

**一处限制，是继承来的而非选择的。** 两个 `run_public.sh` 都是 sha256 钉死的 task 文件，都以 `exit 0`
结尾，并用 `2>&1` 把 stderr 并入 stdout。因此客户端的退出码 125 **不会**传递给调用 `run_public.sh` 的那
一方——唯一能存活下来的载体，是合并文本中的 `eda-broker: MEASUREMENT_INVALID <status>:` 标记，这也正是
它被写成与冻结 forwarder 自己的 `eda-shim: remote execution … failed` 惯例相匹配的原因。任何要对
episode 分类的消费方都必须以该标记为准，而不是以返回码为准。修改 `run_public.sh` 既不可行也不应被想要：
它是那 1020 个 sha256 钉死的 task 文件之一。

**agent 无法影响任何 argv。** 客户端以 `pt_shell` 或 `hspice` 的 shim 身份被调用，完全忽略自己的参数，
并根据被调用时的名字来选择操作。`run_public.sh` 中的参数是 canonical 的，broker 早已知晓。

## 5. 工作目录的生命周期

```
~/eda-probe-broker/ep/<episode_id>/          0700，开通时由宿主机创建
~/eda-probe-broker/ep/<episode_id>/inv-<n>/  0700，每次调用创建并销毁
```

刻意**不放在 `/tmp` 下**。`/tmp` 正是那些残留的 evaluator 镜像不断堆积的地方，也是共享主机上其他所有工
具的写入地；把私有根目录放在 `$HOME` 下正是要点所在。

清理在**每一条**退出路径上执行——成功、协议错误、校验拒绝、工具失败、超时与信号。每一步都在自己的会话中
运行（`start_new_session=True`），超过墙钟时限时先向整个**进程组**发 `SIGTERM`，等满 10 秒宽限期，再发
`SIGKILL`。

进程组是关键，而 `subprocess` 自带的超时并不够。只杀直接子进程会留下孤儿 `pt_shell` 后代，它们占着
licence，并继续往后续运行的任何东西里写——在共享 EDA 主机上，那意味着下一个 episode 的工作目录。因此
broker 会报告它所杀掉的进程**组**（`killed_pgid`）以及是哪一步超时（`timed_out_step`），而 preflight 是
在真实进程上观测这一性质而非断言它：它通过 manifest 缩短墙钟、启动真实的 PrimeTime，然后用
`ps -g <pgid>` 去问还剩下什么。

这项检查的两半在正确之前都曾是错的，而且错法同源——一项检查说不出它看起来在说的那件事：

- **它可能空洞地通过。** 墙钟设为 5 秒时 PrimeTime 跑完了，响应回来是 `ok`，于是"没有孤儿存活"之所以为
  真，只是因为什么都没被杀过。现在该检查要求这次杀确实发生过，**并且**落在 `TOOL` 这一步而不是那个小小的
  Python 构建脚本上——否则观测的是错误的进程。
- **它只可能失败。** 第一版问的是 `pgrep -u $USER -f pt_shell`，而它会匹配到**正在运行这条 pgrep 的那个
  shell**，因为该 shell 自己的命令行里就含有字符串 `pt_shell`。于是它在每一次运行中都报告恰好一个幸存者，
  包括那次什么都没被杀的运行。改问进程组则不可能自匹配：探测用的 shell 处在另一个组里。
- **接着它又在一个列标题上失败了。** `ps -o pid=,args=` 会被 procps 解析成"列 `pid`，标题为 `,args=`"，
  于是一个**空**进程组仍会打印一行——那个标题——而检查又把它读成了幸存者。分开写两个 `-o` 就什么都不打印，
  而且现在解析还额外要求每一行必须以 pid 开头。

连续三次失败，没有一次关于 broker，每一次都关于测量仪器本身。这一点值得写下来而不是收拾掉：一件没有在
"已知为空"和"已知非空"两种情形下都校验过的仪器，还不算一次测量。现在单元测试两者都做——它断言被杀的进程组
被报告出来且为空，也断言一个**正常结束**的步骤根本不报告任何被杀的进程组，于是"什么都没被杀"永远不会被读
成"这次杀什么都没留下"。

清理是被验证的，而不是被假定的：preflight 断言每次调用之后调用目录已不存在，并断言拆除之后 episode 目录
与密钥行都不再存在。

## 6. 沙箱凭据隔离

其中三项在 dry run 所用的沙箱里已经成立，因此是**被断言而非被新建**的；第四项是新增的。

| 性质 | 状态 |
|---|---|
| 沙箱内不存在 `~/.ssh` | 已成立——只绑定了 `~/.opencode/bin` |
| `SSH_AUTH_SOCK` 未设置 | 已成立——`SSH_` 在 `SCRUB_PREFIXES` 中 |
| 无可达的 agent socket | 已成立——`/run` 未挂载 |
| 只有 probe key 与钉死的 `known_hosts`，别无其他 | 新增 |

客户端调用 ssh 时带 `-o IdentitiesOnly=yes -o IdentityAgent=none -o BatchMode=yes -o
StrictHostKeyChecking=yes -o UserKnownHostsFile=<pinned> -o ControlMaster=no`，因此它无法回落到任何未被
显式给定的密钥或主机密钥。

### 6.1 启动器的文件名是接口的一部分

`run_public.sh` 经由 `EDA_PT_CMD` / `EDA_HSPICE_CMD` 分发，而客户端从 `argv[0]` 选择操作——因此两个启动器
是两个名字不同的可执行文件，而这个**名字是承载语义的**。它们是带 shebang 的 Python 脚本，而不是 shell
包装器，这个区别并非装饰性的：

```sh
#!/bin/sh
exec python3 .../broker_client.py "$@"      # 错误：argv[0] 变成了 broker_client.py
```

Python 会把 `sys.argv[0]` 设为它被交付的那个脚本，所以 shell 包装器会摧毁这个名字，每一次调用都会以
`argv0=broker_client.py` 抵达并被 `UNKNOWN_SHIM` 拒绝。带 shebang 时，内核交给 Python 的是启动器自身的
路径，`argv[0]` 就是 `.../pt_shell`。

这是一个真实缺陷，而它被抓住的方式才是更值得留下的部分。单元测试原本断言启动器的**源文本**中提到了
`broker_client.py`，那个坏掉的包装器完全满足这一点，同时破坏了唯一要紧的性质；抓住它的是 preflight，因为
preflight 会真的把工具跑起来。现在该测试会**执行**每个启动器，并读回解析出来的是哪个操作。一项检视产物而
不是驱动产物的测试，可以与一个缺陷无限期地相互认可。

### 6.2 每条远端命令都作为一个词被引用

`ssh host bash -lc <script>` 并不透传 argv。ssh 把其余参数用空格拼起来交给**远端**shell，后者会再解析一
遍——因此未加引号的 `bash -lc 'a; b'` 只把 `a` 送给了 `bash -lc`，而让远端登录 shell 去执行 `b`。冻结的
forwarder 正是为此加引号（`ssh "$HOST" "bash -lc '...'"`）。

不加引号时，这种失败是安静且误导性的，而不是响亮的。它造成过一次部署：报告"远端登录 PATH 上没有
python3"，而在同一份输出里却打印出它刚刚解析到的 `pt_shell` 与 `hspice`；也造成过一次
`ls .../inv-* | wc -l` 去统计远端 home 目录，报告有 19 个残留的调用目录，而实际上一个都没有。现在只有一份
引用实现，位于 `broker_admin._ssh`，preflight 走的是它，而不是自己另有一份。

## 7. 负控制

以下每一项都必须失败，任一成功则 preflight 失败。这沿用 dry run 之后 check 5 所获得的处理方式：一组具名
的绕过尝试，而不是一串猜出来的"不存在的路径"。

| # | 尝试 | 期望 |
|---|---|---|
| 1 | 任意命令——`ssh -i probe_key tsb@b04 'cat /etc/passwd'` | forced command 运行、忽略该命令，stdin 上无合法分帧请求 → `REFUSED FRAMING` |
| 2 | 未知操作——`{"op":"ls"}` | `REFUSED UNKNOWN_OP` |
| 3 | 输入键集合多出一个名字 | `REFUSED INPUT_SET_MISMATCH` |
| 4 | 表达路径的输入名——`../hidden/signoff_intent_truth.json` | `REFUSED ILLEGAL_INPUT_NAME` |
| 5 | `scp -i probe_key file tsb@b04:/tmp/` | 失败，无 `scp -t` 服务端 |
| 6 | `sftp -i probe_key tsb@b04` | 失败，无 `sftp-server` |
| 7 | PTY——`ssh -tt -i probe_key tsb@b04` | PTY 分配被拒 |
| 8 | 端口转发——`ssh -L 9999:localhost:22` | 被拒，且没有建立起监听 |
| 9 | agent 转发——`ssh -A` | 被拒，且不存在可转发的 socket |
| 10 | **跨 episode**——用 episode A 的密钥，在每一个 JSON 字段、在 argv、以及经 `SendEnv` 指名 episode B | 按 A 服务或被拒；B 的目录从未被触及 |
| 11 | **植入诱饵**——把一个唯一 sentinel 写入 `/tmp/eda_shim_PREFLIGHT/signoff_intent_truth.json`，再经每个操作与每个字段去读它 | 该 sentinel 从不出现在任何响应中 |
| 12 | 沙箱凭据隔离 | `~/.ssh` 不存在，`SSH_AUTH_SOCK` 未设置，`/tmp/eda-probe` 下只有 `key`/`known_hosts`/`bin`，密钥只读，PATH 上没有 forwarder |
| 13 | **全尺寸批量**——一次重写装入 48 把 episode 密钥，再一次重写拆除 | 非受管区域在之前、期间、之后逐字节一致；期间 48 条、之后 0 条；每一行只强制它自己的 episode；批量在位期间操作者本人的密钥仍能认证 |
| 14 | **超限命中**——把 stdout 上限调到实测 3 205 B 以下，再跑真实 PrimeTime | `transport_output_limit`；响应中没有 `stdout`/`stderr`/`artifacts`；客户端以 125 退出且 stdout 为空 |

第 1–11 与 13–14 项是远端配置的性质，第 12 项是沙箱的性质。十四项全部零模型调用。

**第 11 项就是它胜过 `find /tmp` 的原因。** broker 的正确性不可以依赖 b04 的 `/tmp` 是干净的：dry run
报告实测到 1492 个 `eda_shim_*` 目录，里面装着两个 family 的 truth 文件；它们被清掉了，而下一次评分运行
又会重建它们。证明这棵树是空的，对下一个 episode 什么也证明不了。因此该性质是针对一个**故意植入**的
truth 文件来建立的——被检验的是能力隔离，不是文件系统的清洁度。

**第 13 项是那个可能把操作者锁在 EDA 主机之外的控制**，因此写得最为小心。它使用正式实验臂会装入的那 48
个 episode *id*——48 正是批量化所要消除的 NFS 暴露所对应的数量——但给每个 id 加上 `PREFLIGHT__` 前缀，
并把它们全部指向 `p15_dev_0000` 的文件。于是 `authorized_keys` 的写入规模与实验臂将要执行的完全一致，
preflight 不会开通任何被研究的 instance，任何残留也不会被误认成一次真实的实验臂。它还会在批量在位期间用
操作者本人的密钥重新认证一次，因为"字节看起来对"与"密钥仍然能用"是两个不同的主张，而凌晨两点真正要紧的
是后者。

**第 14 项是把上限调低，而不是去制造一份 1 MiB 的 PrimeTime 日志。** episode 的 manifest 可以调低上限、
可以缩短墙钟；但永远不能调高或延长其中任何一个，因此一份 manifest 绝不可能为某个 episode 买到超出既定
上界的传输量或工具时间。该控制所断言的是：调低上限后的响应里，**没有任何键名**下藏着被缩短的 `stdout`。

### 7.1 forwarder 等价性，以及一套被测量出来而非被挑选出来的归一化

零模型成本下能拿到的最强 parity 证据：在 `p15_dev_0000` 上分别经由冻结 forwarder 与 broker 客户端运行
`run_public.sh`，把两者归一化，并要求公开观测相等。

归一化正是这项检查可能悄悄变得一文不值的地方。一套不断增长直到两段文本相符的规则，与一个被调到什么都不
打印的验证器是同一种失败。因此规则分成两半，而且只有前一半是手写的：

- **静态规则**，在记录中逐条列出各自丢弃了多少行——版本与版权 banner、日期、时钟时间、计时行、licence
  絮语、pid。若任何单条规则占到输出的 20% 以上，检查失败。
- **一套稳定性对照，由测量导出，且在两条路径之间对称。** 每条路径各运行数次（forwarder 3 次，broker 2
  次）。对每一个行**形状**——即数字串被掩码后的那一行——收集它在该路径**内部**所取到的值的集合。只有当一个
  形状在**两条**路径中都恰好只取一个值时，它才参与比较；在任一路径中不稳定的形状被排除，并连同观测到的全部
  取值一起列出。没有任何东西是凭一条手写规则被丢掉的。

这项对照立刻就证明了自己的价值，随后又以艰难的方式换来了它的最终形态。第一次诚实的比较恰好差在一行上：

```
-Maximum memory usage for this session: 2897.31 MB
+Maximum memory usage for this session: 2897.26 MB
```

加一条内存用量的正则就能让它消失，而在记录里，这与"把一处真实差异归一化掉"是无法区分的。于是第一版把
forwarder 跑两次，丢弃这两次之间有差异的内容。接着又出现了两个缺陷，两个都值得留在记录里，因为它们是同一
个错误换了衣服——相信一件采样不足的仪器：

1. **按精确文本匹配太窄。** 两次 forwarder 运行给出 2897.26 与 2897.31；broker 给出的是**第三个**值
   2897.27，字面丢弃集合把它留下，并把一处对照早已证明为噪声的差异报成了差异。改按掩码形状匹配解决了它。
2. **一侧只有一对样本太少。** 在后来的一次运行中，两次 forwarder 运行恰好报出了**相同**的值，于是对照什么
   都没检测到、什么都没丢弃，而检查就在几分钟前它自己正确识别过的噪声上失败了。一个会随机失败的 gate 不是
   gate。改为**两侧**都跑数次解决了它。

若被排除的集合超过输出的 10%，检查失败——因为庞大的排除集合意味着剩下可供"相等"的内容已经不多。

实测：比较 82 行，跨路径 diff 为空，一个不稳定形状占输出的 1.2%——即那条内存行，在五次运行中被观测到取
2897.26、2897.27 与 2897.31 MB——且 broker 输出中不存在任何 forwarder 输出中没有的标识符。

**范围限制。** 仅 PrimeTime。该比较需要一个位于所有被研究面板之外的 instance，而 p16 没有属于被研究世代的
这种目录——`p16_dev_0000` 早于不可变 core 方案——而从 preflight 去开通一个被研究的 p16 instance 并不可接
受。HSPICE 这条路径所依靠的是共用的 broker/client 代码与 artifact 往返，而不是它自己的端到端比较。

**而且此处的 `rc_equal` 近乎空洞**，因为 `run_public.sh` 无条件以 `exit 0` 结尾。它只为完整性而记录；真正
承担分量的断言是 `normalised_equal`。

## 8. Check 6 —— 一项实验臂前的 parity 更正

**更正内容。** check 6 的判据从"绝对不可恢复"改为"与冻结 runner 保持 parity"：

| | 更正前 | 更正后 |
|---|---|---|
| 判据 | agent "**以任何途径**都无法恢复被截断的部分" | OpenCode 特有的溢出落盘存储不可达；agent 自己创建的工作区文件，在冻结 runner 允许的范围内同样允许 |
| 必须成立 | —— | `<state>/data/opencode/tool-output/*` 与 `/tmp/opencode/*` 不可达 |
| 允许 | —— | 重定向后分页读取，因为 `llm_agent_driver.py:67` 同样允许 |

**为什么。** dry run 把 check 6 记为 PARTIAL，并如实记录了原因：scaffold 特有的那个洞已经堵上——对截断
落盘目录的每一次读取都返回"不存在"，因为只读绑定使溢出根本无法被写入——但 agent 通过把一条 >4000 字节
的输出重定向到工作区文件、再用 `read` 的 `offset`/`limit` 分页读回，仍然恢复了它。

冻结 driver 有完全相同的逃逸口。它把每次观测截断到 4000 字节（`llm_agent_driver.py:585,742`），其拒绝正
则（`llm_agent_driver.py:67`）拦截
`EDA_TASK_PATH|/hidden|/solution|/oracle|run_hidden|../`——它并不拦截"重定向后读取一个切片"。两个 scaffold
之间不同的是观测**预算**；观测**上界**在两者中都从未存在过。

因此原判据要求的是一项对照组本身也不具备的性质，会因为 probe **与冻结 runner 相等**而判其失败。这是判据
有缺陷，不是 probe 有缺陷。check 6 真正要保护的量是观测预算的可比性，而 parity 恰好就是这个量。

**为何这是实验臂前的更正，而不是事后的补救。** 这个区分在此处格外要紧，因为本论文的主题正是"不要草率地
做这个区分"：

- 它作出于**正式实验臂运行之前**，此时不存在任何可供窥看的正式实验臂结果。
- 触发它的是一次**按授权即为不计分、不采纳**的 dry-run episode，运行在 `p15_dev_0000` 上——该 instance
  不属于任何被研究的 panel，也不带条件变体，因此根本不存在可被看到的 Base/BundleS 对比，也未作任何计算。
- 它既放松也**收紧**：落盘存储不可达这一条从原先笼统禁止中的隐含项，变成显式且强制的要求。
- 它以带独立标题的、注明日期的修订形式记录，而不是通过改写原文使其看起来"本来就是这么写的"。

该更正会修改 `opencode_scaffold_probe_scope.md` 的两个语言版本，并由
`test_check6_is_parity_not_absolute` 断言更正后的措辞存在、且绝对化的旧措辞已不存在。

## 9. 披露性背景 —— 冻结实验臂同样存在这一暴露

冻结 driver 的拒绝正则是
`(EDA_TASK_PATH|/hidden\b|/solution\b|/oracle\b|run_hidden|\.\./)`。它没有提及 `ssh`、`b04` 或 forwarder。
因此一个冻结 episode 本可以运行 `ssh tsb@b04 cat /tmp/eda_shim_*/signoff_intent_truth.json`，而被中介的
`RUN:` 语法会放行。

之所以记录此事，是因为它正是 broker 比 parity 更严格的理由；把它说出来，好过悄悄造一个更强的控制、并暗
示冻结实验臂也有一个。关于它的含义有三条限制：

- 对 `reports/` 下已入库记录中直接调用 `ssh`/`b04` 的 grep 返回 **0 条命中**，因此这一暴露是可用的，而
  在已入库的记录中并未被使用。这是一句关于"记录里有什么"的陈述，不是一次完整审计——本次未做审计。
- `a89e084` 实验计划已关闭。这不是那边需要修的缺陷，不重跑任何 episode，也不改变任何冻结数字。
- 它不允许把 broker 解读为 scaffold 的改进。scaffold 主效应按构造被排除且不予计算；
  `test_no_scaffold_main_effect_claim` 依然适用。

## 10. 本设计没有建立什么

明确写出来，因为本项目反复防范的失败模式，正是"一项检查在没人会真正使用的配置下通过了"：

- **它不授权正式实验臂。** check 7 仍为 UNSETTLED，本设计并未触及它。
- **check 5 不能顺延。** 它的 PASS 是在工具缺席的情况下建立的。本设计挂上了工具通道，因此 check 5 必须在
  实验臂真正会使用的配置下重新建立，才算数。
- **它不使实验臂变得负担得起。** 成本是另一个问题，dry run 拒绝从单个短 instance 外推，理由是
  `ARM2_NOT_RUN` 复盘早已付过学费的那些。
- **它并不单凭自身交付 Layer 1。** `n_tool_green_wrong` 需要真实的绿色工具信号**且**不可达的 oracle。本
  设计是在恢复前者的同时尝试达成后者；能否成功，正是 preflight 要测量的。
- **它没有建立"某个传输上限永远不会成为约束"。** §4.1 是在一个有限校准集上测量余量；剩下的部分由 §4.2
  的 fail-closed 行为覆盖。二者不得被合并成"这些上限不构成约束"。
- **它没有建立与冻结 runner 之间逐字节的动作面 parity。** §3.4 记录了这处差异——broker 把工具权威的输入
  钉到规范任务版本上，而冻结 runner 并不这样做——而不是消解它。
- **forwarder 等价性只在 PrimeTime 这条路径上建立。** 该比较需要一个位于所有被研究面板之外的 instance，
  而 p16 没有属于被研究世代的这种目录：`p16_dev_0000` 早于不可变 core 方案，它的 `build_deck.py` 从零写出
  `circuit_built.sp` 且没有 `circuit_core.sp`，op 表无法为它服务。而从 preflight 去开通一个被研究的 p16
  instance 并不是可接受的替代。因此 HSPICE 这条路径所依靠的是共用的 broker/client 代码与 artifact 往返，
  而不是它自己的端到端比较。
- **它没有落定任何需要真实模型请求的性质。** 尤其 check 7 是一个动态性质，一个零调用 preflight 若报告它
  已落定，就是把动态检查伪装成静态检查。唯一被授权的付费 episode 及其预注册门槛见
  [`opencode_probe_broker_dry_run.md`](opencode_probe_broker_dry_run.zh.md)；界定它的 ¥20 实时成本上限在
  那里说明，并且与 §4.2 是同一意义上的 fail-closed。

## 11. 文件与验证

```
scripts/eda_broker/broker_protocol.py                op 表、分帧、上界、错误分类
scripts/eda_broker/authorized_keys_block.py          受管区块、互斥锁、批量装入/拆除
scripts/eda_broker/remote_broker.py                  部署到 b04；即 forced command
scripts/eda_broker/broker_sh.template                部署时渲染为 <root>/broker.sh
scripts/eda_broker/broker_client.py                  沙箱内客户端；同时是 pt_shell/hspice 的 shim
scripts/eda_broker/broker_admin.py                   宿主机侧的部署 / 开通 / 批量 / 拆除
scripts/opencode_probe_raw_output_audit.py           零调用的传输余量校准
scripts/opencode_probe_remote_broker_preflight.py    零调用；写出证据记录
scripts/opencode_probe_agent.py                      把该能力绑定进沙箱
scripts/opencode_probe_broker_dry_run.py             唯一那次付费 episode；另见其自身文档
tests/test_eda_broker.py                             协议、分类、拒绝、负控制
tests/test_opencode_cost_governor.py                 实时成本上限与本次运行的读取器
opencode_probe/evidence/raw_output_audit.json        §4.1 背后的实测上界
opencode_probe/evidence/remote_broker_preflight.json 记录本身
opencode_probe/broker/deploy.json                    远端解释器、逐文件 sha256、主机密钥
opencode_probe/broker/batch.json                     仅在批量在位期间存在
```

以上路径都未被 `reports/evidence/` 下的 sha256 钉死，且不修改任何被钉死的文件。在改动 `scripts/` 下的任
何东西之前先验证：

```bash
python3 -c "import sys; sys.path.insert(0,'scripts'); \
  from frozen_membership_verify import collect_pins, SCAN_ROOT; \
  print('<path>' in collect_pins(SCAN_ROOT))"
```

在相信 preflight 的结论之前，以下门禁必须全部通过：

```bash
scripts/check                                                    # 1065 pins / 9 / 2 / 1
python3 -m pytest tests/test_eda_broker.py tests/test_opencode_probe.py -q
python3 scripts/opencode_probe_raw_output_audit.py               # 零模型调用
python3 scripts/opencode_probe_remote_broker_preflight.py        # 零模型调用
python3 scripts/slim_link_check.py
```
