# ADR-0002：协作式取消方案（Phase 1 任务 4）

> 状态：**已采纳（实现于 scheduler._run_entry + application.ExecutionController）**
> 日期：2026-10-13
> 依据：AGENTS.md 第 2.6 条（状态机含 Stopping/Cancelled，所有运行必须有终态）、第 5.4 条（停止采用可验证的协作式取消）、第 8 节 Phase 1 任务 4。

## 背景

原实现 `run_task` 用 `job.wait()` 阻塞等待，唯一停止手段是杀进程——这会留下 MaaFw
「伪最小化」的窗口状态（历史教训），也不满足「所有运行必须有终态」。

## 评估结论

| 能力 | 事实 |
|---|---|
| `Tasker.post_stop()` | ✅ 存在（MaaFw v5.14.3），返回 Job |
| `Job.wait(timeout)` | ❌ 无超时参数 |
| `Job.done` | ✅ 布尔属性，可轮询 |

## 决策

1. **统一执行核心** `scheduler._run_entry(...)`：无取消事件时仍走 `job.wait()`（与旧行为字节级一致）；有取消事件时轮询 `job.done`（间隔 50ms），取消则先 `STOPPING` → `tasker.post_stop().wait()` → `CANCELLED`。
2. **ExecutionController**（`application/execution.py`）：daemon 线程跑序列；`cancel()` 置标志；`wait(timeout)` 收结果；控制面终态规则 = 任一 CANCELLED → CANCELLED，全 OK → SUCCEEDED，否则 FAILED；worker 异常也落到 FAILED（有终态保证）。
3. **序列级取消**：`run_sequence` 每个任务开始前检查取消，剩余任务全部记 CANCELLED（不做无用操作）。
4. **CLI 集成**：`run`/`daily` 的 Ctrl+C 改为 `cancel()` + 有限等待，不再杀进程；窗口还原仍由 finally 兜底。

## 降级方案（如真机发现 post_stop 失效）

记录于此，真机验证不通过时启用：
- 仅置取消标志，等当前节点超时（next 列表默认 20s）自然结束；序列不再启动新任务。
- 最坏情况（任务永久卡死）：保留 `restore` 命令兜底 + 提示手动结束。

## 待真机验证

- `post_stop` 对真实游戏任务（如战斗等待 300s 节点）能否立即中断；
- 取消后游戏画面状态是否安全（回到可识别状态）；
- 轮询间隔 50ms 的 CPU 占用是否可接受。

## 验收

- 单元：FakeTasker 下取消路径（STOPPING→post_stop→CANCELLED）、序列剩余任务取消、终态保证。
- 真机（任务 8 阶段）：Ctrl+C 停止一次真实任务并确认窗口/状态正常。
