# ak-auto 架构设计（现状 → 目标）

> 依据：AGENTS.md 第 2 节（永久架构约束）与第 0 节（产品策略 C：统一核心、双模式 UI）。
> 本文件描述**现状事实**与**目标架构**的映射；迁移按 ROADMAP 分阶段进行，禁止一次性重写。

## 1. 现状架构（已验证事实）

单进程、同步、无 UI：

```
┌────────────────────────────────────────────────────────────┐
│  CLI（Typer）：doctor / probe / fetch-assets / run / daily │
│            restore / lint                                   │
├────────────────────────────────────────────────────────────┤
│  scheduler.run_sequence / run_task     report.RunReport     │
├────────────────────────────────────────────────────────────┤
│  runtime.build_tasker（Resource + Tasker + CustomAction）   │
├────────────────────────────────────────────────────────────┤
│  MaaFw：pipeline JSON（识别/动作/next）+ Python CustomAction │
├────────────────────────────────────────────────────────────┤
│  device（Win32Controller / 截图 / 输入 / 窗口 / 原生滚轮）   │
│  config（Pydantic）    data（MAA 数据表）                    │
└────────────────────────────────────────────────────────────┘
```

特点与缺口：
- **业务核心 = scheduler + runtime + MaaFw pipeline**；CLI 直接调用，无应用服务层。
- **任务 = 流水线入口名字符串**；无 TaskDefinition / 参数 Schema / 风险等级。
- **状态只有 TaskResult**；无 run_id、无事件、无状态机（Pending/Stopping/Cancelled 缺失）。
- 无线程模型设计（同步等待）；无取消机制。
- 配置为单文件 Pydantic 模型，无版本/迁移。
- GUI 不存在。

## 2. 目标架构（AGENTS.md 第 2 节）

```
┌──────────────────────── Presentation ────────────────────────┐
│  SimpleMode（默认：预设+一键）   AdvancedMode（策略/编排/诊断）│
│  共享组件 / ViewModel-Presenter                                │
└──────────────────────────────┬───────────────────────────────┘
                               │ 只经应用服务接口，不直接碰识别/点击
┌──────────────────────────────▼── Application ────────────────┐
│ TaskService   Scheduler   ExecutionController                │
│ ConfigurationService   DiagnosticsService                     │
│ （状态机 / 事件 / 取消 / 重试 / 安全策略 在此层）              │
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼── Domain ─────────────────────┐
│ TaskDefinition  TaskParameters  Preset  ExecutionState        │
│ ExecutionResult  RetryPolicy  SafetyPolicy                    │
└──────────────────────────────┬───────────────────────────────┘
┌──────────────────────────────▼── Infrastructure ─────────────┐
│ MaaFrameworkAdapter  GameWindowAdapter  AssetManager          │
│ 配置/日志持久化      更新检查（P2）                            │
└──────────────────────────────────────────────────────────────┘
```

强制约束（第 2 节）：
1. GUI 不直接操作底层识别/点击/MaaFramework；
2. GUI 与 CLI 共用同一业务核心，不分叉任务逻辑；
3. 耗时任务在非 UI 线程；跨线程用安全事件/信号；
4. 同一游戏窗口同一时间只允许一个输入控制者（任务队列防冲突）；
5. 任务统一 8 元定义（ID/名称/分类/描述/参数 Schema/默认推荐值/风险/前置条件/执行入口/超时/重试/结果错误）；
6. 状态机含 Pending/Preparing/Running/Stopping/Succeeded/Failed/Cancelled（Paused 仅在支持检查点后启用），所有运行有终态；
7. 事件携带 run_id/task_id/时间戳/状态/诊断（TaskStarted/TaskProgress/TaskCompleted/TaskFailed/TaskCancelled/ConnectionChanged）；
8. 保留现有可工作模块；重大迁移需兼容层+迁移方案+回归测试+回滚路径；
9. GUI 框架优先评估 PySide6（见 ADR-0001）；
10. 不为形式加无用层次/插件/大依赖。

## 3. 现状 → 目标 的映射（Phase 1 拆解依据）

| 目标层 | 现状对应物 | 迁移动作（Phase 1+） |
|---|---|---|
| Presentation | 无（CLI + .bat 占位） | Phase 2 新建；SimpleMode/AdvancedMode 共享 ViewModel |
| Application·TaskService | 无（CLI 直连 scheduler） | 新建 TaskService：注册任务目录、按 ID 启动 |
| Application·Scheduler | `scheduler.run_task/run_sequence` | 改造：接入状态机/事件/取消，包一层 ExecutionController |
| Application·ConfigurationService | `config.AppConfig.load/dump` | 加版本/迁移/原子写/备份/导入导出 |
| Application·DiagnosticsService | `doctor`/`probe`/`lint` 命令 | 收敛为服务，供 GUI 与 CLI 共用 |
| Domain·TaskDefinition 等 | 无（字符串任务名） | Phase 1 新建：把 10 个流水线入口登记为 TaskDefinition |
| Infrastructure·MaaFrameworkAdapter | `runtime.build_tasker` + custom actions | 收敛为 Adapter，隔离 MaaFw 细节 |
| Infrastructure·GameWindowAdapter | `device.*` | 收敛（含 native_wheel、伪最小化 restore、分辨率守卫） |
| Infrastructure·AssetManager | `fetch-assets` + MANIFEST | 收敛；P2 加版本管理/更新检查 |

## 4. 关键线程/生命周期设计（目标态）

- **单输入控制者**：`GameWindowAdapter` 内部互斥，同一 hwnd 同时只允许一个活动控制器；任务队列串行执行。
- **执行线程**：Scheduler 在独立工作线程运行任务；UI 通过事件/信号（Qt Signal 或等价机制）接收进度。
- **取消**：协作式取消令牌；MaaFw 侧通过 `tasker.post_stop()`（若有）或任务内 StopTask 节点 + 有限等待实现；取消必须有终态（Cancelled）。
- **窗口守护**：进入任务前 `ensure_game_window`；任务期间检测窗口丢失 → 安全停止；退出（含异常）→ `restore_window`（伪最小化还原）。
- **真实光标滚动**：`native_wheel` 与 GUI 交互互斥（执行期间提示用户勿动鼠标，或在 Seize 模式评估替代方案）。

## 5. 需 ADR 记录的关键决策（后续阶段逐条落地）

1. GUI 框架（PySide6 评估）—— 已起草 ADR-0001。
2. 统一任务定义模型（TaskDefinition/TaskParameters 的字段与 Schema 表达，如何兼容现有 pipeline 字符串入口）。
3. 状态机/事件总线实现（自研最小事件 vs Qt Signal 直接贯穿）。
4. 取消机制（MaaFw 是否支持中断；不支持时的降级方案）。
5. 配置版本化与迁移策略（schema_version 起步值、备份/恢复）。
6. 分辨率支持策略（维持 1280×720 基线 + 集中坐标表，还是引入缩放适配）。
7. 打包方案（PyInstaller vs Nuitka，含 MaaFramework 动态库与资源分发）。
8. 更新检查与资源版本管理（P2）。
