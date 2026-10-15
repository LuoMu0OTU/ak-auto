Agent 可恢复工作状态


每轮结束、上下文压缩前更新。这里记录当前事实，不代替 AGENTS.md 的长期规则。




更新日期：2026-10-13

当前阶段：Phase 1 核心解耦（进行中，任务 4/8 完成）

当前分支：main

HEAD：2cf3796（本轮任务 4 提交前基线；任务 4 提交号见 git log 最新一条）

工作区状态：干净（原未提交的 infrast.json 已按负责人授权提交并推送）

本轮获准任务：Phase 1（经人工授权）。本轮完成第 1 项：TaskDefinition 任务目录；CLI 保持兼容。


已完成

- Phase 0 全部（审计/测试基线/架构/路线图），已人工验收（2026-10-13）。
- 基建 infrast.json（制造/贸易停工节点）经负责人确认保留，已提交并推送。
- Phase 1 任务 1 —— TaskDefinition 任务目录：
  - 新增 src/ak_auto/domain/taskdef.py：TaskDefinition + ParamSpec 模型（id/名称/分类/描述/参数 Schema/默认推荐值/风险等级/前置条件/执行入口/超时/重试/错误说明）+ 10 个任务的目录 + resolve_task（按 ID/中文名/忽略大小写解析）。
  - CLI 集成：run 经目录解析（支持中文名；未登记的名称按原始流水线节点名兼容执行）；daily 对 task_order 逐项校验并警告；新增 tasks 子命令列出目录。
  - 测试：tests/test_taskdef.py 6 例（目录完整/唯一、必选任务、解析、Fight 安全默认、task_order 一致性、入口在流水线中存在）。
- Phase 1 任务 2 —— ExecutionState 状态机 + ExecutionResult：
  - 新增 src/ak_auto/domain/state.py：ExecutionState 七态枚举（PENDING/PREPARING/RUNNING/STOPPING/SUCCEEDED/FAILED/CANCELLED，Paused 暂不启用）+ 合法转移表 + StateMachine（终态无出边）+ ExecutionResult（run_id/task_id/state/起止时间/错误/nodes，保留 entry/ok/status/summary 兼容属性）+ new_run_id。
  - scheduler.py：TaskResult 改为 ExecutionResult 别名；run_task 经状态机跟踪（PENDING→PREPARING→RUNNING→终态）产出 ExecutionResult；run_sequence 的 missing-node 改用错误码。
  - report.py：报告 JSON 增加 run_id/error 字段；控制台 summary 格式与旧版一致（合成错误如 missing-node 优先展示）。
  - 测试：tests/test_state.py 8 例（happy path/取消/停止/非法转移/兼容字段/错误展示/to_dict/别名）。
- Phase 1 任务 3 —— 事件总线（最小）：
  - 新增 src/ak_auto/domain/events.py：EventType 六事件（TaskStarted/TaskProgress/TaskCompleted/TaskFailed/TaskCancelled/ConnectionChanged）+ TaskEvent（run_id/task_id/时间戳/状态/诊断）+ EventBus（同步订阅/发布、订阅者异常隔离）。
  - scheduler.py：run_task/run_sequence 增加 bus 参数；run_task 发 TaskStarted + TaskCompleted/TaskFailed；run_sequence 发 TaskProgress（重试提示）。
  - __main__.py：run/daily 订阅总线并在控制台输出事件（▶开始/✔完成/✘失败；TaskProgress 由 on_progress 负责不重复打印）。
  - 测试：tests/test_events.py 9 例（订阅/全订阅/异常隔离/调度器事件/序列进度/缺失节点），内含 FakeTasker（任务 7 Fake 控制器的种子）。
- Phase 1 任务 4 —— ExecutionController 协作式取消：
  - 评估结论：MaaFw `Tasker.post_stop()` 存在（v5.14.3），`Job.done` 可轮询 → 见 ADR-0002。
  - scheduler.py 重构出 `_run_entry`（无取消事件时与旧阻塞 wait 等价；有则轮询 + STOPPING→post_stop→CANCELLED）；run_sequence 支持 cancel_event（剩余任务记 CANCELLED）。
  - 新增 src/ak_auto/application/execution.py：ExecutionController（daemon 线程、cancel/wait、控制面终态规则、worker 异常也落 FAILED）。
  - __main__.py：run/daily 改用控制器；**Ctrl+C 从杀进程升级为优雅停止**（cancel + 有限等待 + 窗口还原兜底）。
  - ADR-0002（取消方案）+ 测试 tests/test_execution.py 6 例（正常完成/取消停止/取消事件/序列剩余取消/重复 start/异常终态）。


进行中 / 待办

Phase 1 剩余四项（按 docs/ROADMAP.md 拆解顺序）：
5. ConfigurationService：schema_version/原子写/备份/损坏恢复/迁移框架（保持 config.json 兼容）；
6. Adapters 收敛（最小）：MaaFrameworkAdapter / GameWindowAdapter / AssetManager；
7. 为新核心补单元测试（Fake 控制器 + 录制截图）；
8. CLI 兼容验收（run/daily/doctor/probe/restore 与 Phase 0 行为一致，真机对照）。


修改文件

- 新增 src/ak_auto/domain/*（taskdef/state/events）、src/ak_auto/application/*（execution）、tests/test_taskdef.py、test_state.py、test_events.py、test_execution.py、docs/architecture/adr/0001、0002
- 修改 src/ak_auto/__main__.py（目录解析 + tasks 命令 + 事件订阅 + 控制器/Ctrl+C）、scheduler.py（ExecutionResult + 事件 + 取消）、report.py（run_id/error）
- 未改动 device/runtime/pipeline（任务执行与设备逻辑零变化）


测试与验证

命令	结果	环境/备注
python -m pytest -q	42 passed（15 旧 + 27 新）	Python 3.12.10 / pytest 9.1.1
python -m ak_auto tasks	正常列出 10 个任务（CJK 对齐）	—
取消链路（FakeTasker）	正常完成/取消停止/事件/序列剩余取消/异常终态 全通	—
真机验证	未做	post_stop 对真实任务的中断能力列入任务 8 真机对照（ADR-0002 待真机验证项）


已知问题 / 风险 / 阻塞

- 沿用 docs/architecture/AUDIT.md 第 9 节风险清单（固定坐标、取消/状态机未落地、配置无版本化等，均由 Phase 1 后续任务逐一解决）。
- taskdef 的 params 仅是「描述性 Schema」，值仍存 config 分区；参数化 UI 属 Phase 4，不在 Phase 1 范围。
- 推送已获授权：后续提交可随轮 push。


待真机验证

- 无新增（本轮未改运行代码）；Phase 1 全部完成后按任务 8 做一次真机对照。


设计决策及 ADR

- ADR-0001（提议）：GUI 框架选 PySide6 + Qt Widgets；Phase 2 开工前需人工确认。
- TaskDefinition 模型落地：entry 留空默认等于 id；风险等级 low/medium/high；Fight 的 medicine/stone 默认 0（安全默认）。


下一轮第一步

1. 重新读取 AGENTS.md、SESSION_START.md、本文件与 docs/ROADMAP.md。
2. git status / git log 确认本轮提交与工作区状态。
3. 继续 Phase 1 任务 5：ConfigurationService（schema_version/原子写/备份/损坏恢复/迁移，保持 config.json 兼容），先输出计划再动手。


阶段验收状态


Phase 0：✅ 已人工验收（2026-10-13）
Phase 1：进行中（4/8），按任务逐项自验 + 全部完成后人工验收
