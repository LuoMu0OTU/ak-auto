# ADR-0001：GUI 框架选型评估（Phase 0 技术选型）

> 状态：**提议（Phase 0 评估结论，待 Phase 2 前由项目负责人确认）**
> 日期：2026-10-13
> 依据：AGENTS.md 第 2.9 条「优先评估 PySide6/Qt Widgets，核实 Python、MaaFramework 线程、Windows DPI、构建体积及 LGPL/其他许可要求后决策；替代方案须写 ADR」。

## 背景

产品策略 C：统一核心、双模式 UI（简单/高级）。需要现代 Windows 桌面 GUI：
- 默认深色、可切浅色、中文优先；
- 高 DPI 适配（游戏与桌面常放大 125%/150%）；
- 运行中实时展示任务/步骤/进度/失败原因，支持安全停止；
- 非 UI 线程执行任务 + 跨线程事件。

## 候选对比

| 维度 | PySide6（Qt Widgets） | Tkinter | Dear PyGui | Electron/Web | Flet |
|---|---|---|---|---|---|
| 成熟度/生态 | 高，工业级 | 高但老旧 | 中 | 高 | 低-中 |
| 深色主题/自定义样式 | QSS/调色板，强 | 差 | 内建深色 | 强 | Material |
| 高 DPI（PerMonitorV2） | 原生支持好 | 一般 | 一般 | Chromium 处理 | 一般 |
| 非 UI 线程 + 事件 | QThread + Signal/Slot，标准方案 | 需 after() 轮询 | 回调 | IPC/worker | asyncio |
| 打包体积（含运行时） | ~40-60MB 增量 | 小 | 中 | ~150MB+ | 中 |
| 许可 | **LGPL-3.0**（PySide6 官方绑定） | PSF | MIT | MIT | Apache-2.0 |
| 中文/国际化 | 优秀 | 可用 | 中 | 强 | 中 |
| 与 Python 3.12 兼容 | ✅ | ✅ | ✅ | — | ✅ |

## 评估结论（推荐）

**推荐 PySide6 + Qt Widgets**，理由：
1. 线程模型与本项目「同步阻塞 + MaaFw 后台线程」的现状最匹配：QThread/QThreadPool 跑任务，Signal/Slot 回传进度与状态，正是 AGENTS.md 第 2.3 条要求的安全事件机制。
2. Windows 高 DPI 支持最稳，深色主题可用 QSS/调色板统一设计令牌（第 4 节）。
3. Widgets 而不是 QML：本项目交互以表单/列表/状态为主，Widgets 更轻、打包更小、调试更直接。
4. 许可可接受：PySide6 为 LGPL-3.0，动态链接使用不要求本仓库整体改为 LGPL；与本项目 AGPL-3.0 相容（LGPL-3.0 组件作为独立库动态链接，需在 NOTICE 中声明并提供替换路径说明）。**发布前仍须法务/负责人复核分发义务（提供库的副本或可获取方式、允许重新链接）。**
5. 体积增量 ~50MB，可接受；对比 Electron 明显更轻。

## 备选（写清楚取舍）

- **Tkinter**：零依赖，但深色主题/高 DPI/现代观感成本高，做「现代桌面产品」性价比低。不选。
- **Dear PyGui**：即时模式 + 内建深色，轻量；但中文 IME、表单控件生态、长期维护风险较大，线程模型不成熟。备选。
- **Electron/Web**：UI 能力最强，但引入 Node 运行时 + IPC + 双语言维护，与「轻量、可维护、单人维护」定位冲突，且体积大。不选（除非未来需要 Web 端）。
- **Flet**：上手快但抽象层薄、定制深色/DPI 受限、生态年轻。不选。

## 决策影响

- 新依赖：`PySide6`（约 200MB 安装包、~50MB 部署增量），需在 Phase 2 加入依赖清单并更新 NOTICE。
- 打包（Phase 6）评估 PyInstaller/Nuitka 时需包含 Qt 插件（platforms/styles）与 MaaFramework 动态库。
- 引入后 GUI 与 CLI 共享 Application 层；本 ADR 不改变任何现有代码（Phase 0 不做实现）。

## 验收

Phase 2 开工前：项目负责人确认本 ADR；确认后先做最小窗口原型（主窗口 + 深色主题 + 一个真实任务按钮）验证 DPI/字体/线程三条风险，再进入正式 GUI 开发。
