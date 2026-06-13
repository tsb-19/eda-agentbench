**[English](p2_tb_sva.md) | 中文**

# P2：测试平台 / SVA 生成

## 概述

P2 赛道评估智能体能否为给定的 RTL 模块编写有效的测试平台或 SystemVerilog 断言（SVA）文件。

## 任务概念

每个任务提供：

- 一个正确的黄金 RTL 设计（对智能体可见）
- 一个提示，要求智能体编写测试平台

提交的测试平台使用**基于变异的评分**进行评估：

1. 测试平台与黄金设计一起编译（应通过）
2. 测试平台与变异设计一起编译（应失败/检测到缺陷）

## 评分

| 组件          | 权重 | 标准                                          |
|---------------|------|-----------------------------------------------|
| compile       | 0.2  | VCS 编译成功                                  |
| golden_pass   | 0.4  | 黄金设计通过所有测试                          |
| mutant_1      | 0.2  | 检测到变异体 1（测试失败或报错）              |
| mutant_2      | 0.2  | 检测到变异体 2（测试失败或报错）              |

**通过标准：** total_score = 1.00（黄金设计通过且所有变异体被捕获）

**弱基线：** 空/无操作测试平台得分为 0.0（黄金设计无通过指示）

## 任务目录结构

```
task_200000/
  prompt.md                  # 任务描述
  metadata.json              # 机器可读规格
  files/                     # 对智能体可见
    design_golden.sv         # 正确设计（只读）
    run_public.sh            # 运行黄金测试（只读）
  hidden/                    # 仅用于评分
    design_mutant1.sv        # 变异体 1
    design_mutant2.sv        # 变异体 2
    run_hidden.sh            # 运行变异体测试
  solution/                  # 正确答案
    tb.sv                    # 能捕获所有变异体的测试平台
  buggy_submission/          # 弱基线
    tb.sv                    # 空测试平台
```

## 设计模板

生成器使用 10 个设计模板：

| # | 模板              | 模块               | 难度   | 变异体 1                  | 变异体 2                    |
|---|-------------------|--------------------|--------|---------------------------|-----------------------------|
| 1 | mux2              | `mux2`             | 简单   | select_swapped            | stuck_at_zero               |
| 2 | counter           | `counter4`         | 简单   | enable_inverted           | off_by_one                  |
| 3 | fsm               | `fsm_simple`       | 中等   | wrong_transition          | missing_busy                |
| 4 | handshake         | `handshake_reg`    | 中等   | ready_inverted            | data_not_captured           |
| 5 | priority_encoder  | `priority_enc`     | 简单   | reversed_priority         | wrong_encoding              |
| 6 | pulse_detector    | `pulse_detect`     | 简单   | missing_pulse             | wrong_edge                  |
| 7 | arbiter           | `arbiter_rr`       | 中等   | fixed_priority            | grant_two_bits              |
| 8 | edge_detector     | `edge_detect`      | 简单   | rising_falling_swapped    | registered_output           |
| 9 | valid_ready_fsm   | `vr_pipe`          | 中等   | ready_inverted            | data_not_latched            |
|10 | fifo_status       | `fifo_status`      | 简单   | empty_inverted            | wrong_threshold             |

每个模板有 2 个变异体（10 个模板共 20 个变异体）。

**变异体多样性：**
- 选择/极性反转：select_swapped、enable_inverted、ready_inverted、empty_inverted、rising_falling_swapped
- 缺失/错误行为：stuck_at_zero、missing_busy、missing_pulse、data_not_captured、data_not_latched
- 优先级/顺序：reversed_priority、fixed_priority、wrong_transition
- 差一/阈值：off_by_one、wrong_threshold、wrong_encoding
- 多信号：grant_two_bits、registered_output、wrong_edge

## 模板分配

100 个生成任务使用 10 个模板，生成器每 4 个任务循环一次模板：

- 任务 0-39：模板 0-9（每个 4 个任务）
- 任务 40-79：模板 0-9（每个 4 个任务）
- 任务 80-99：模板 0-4（每个 4 个任务）

结果：模板 0-4 各获得 12 个任务，模板 5-9 各获得 8 个任务。

## 任务 ID 范围

P2 任务使用以 `task_200000` 开头的任务 ID，以避免与 P1（0-199999）冲突。

## 预期数量

- 冒烟测试：1 个任务（task_200000，手工制作的 mux2）
- 生成任务：100 个任务（task_200001 - task_200100）
- 总计：101 个任务

## 命令

```bash
# 生成任务
python3 scripts/generate_p2_tasks.py --count 100 --seed 42

# 运行冒烟测试
bash scripts/run_p2_smoke.sh

# 验证任务
eda-bench validate-task tasks/p2_tb_sva_gen/smoke/task_200000

# 使用解答进行评估
eda-bench evaluate-task tasks/p2_tb_sva_gen/smoke/task_200000 \
    --submission tasks/p2_tb_sva_gen/smoke/task_200000/solution

# 评估数据集
eda-bench evaluate-dataset tasks --submission-mode solution --track p2_tb_sva_gen
```

## 测试平台要求

提交的测试平台必须：

1. 实例化设计模块（按名称，如 `mux2`）
2. 驱动激励以验证设计
3. 根据预期值检查输出
4. 成功时打印 `ALL_TESTS_PASS: N/M`
5. 任何失败时打印 `TEST_FAIL: N/M`
6. 完成时调用 `$finish`
