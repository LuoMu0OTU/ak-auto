Agent 可恢复工作状态


每轮结束、上下文压缩前更新。这里记录当前事实，不代替 AGENTS.md 的长期规则。




更新日期：2026-10-13

当前阶段：Phase 4 高级模式（进行中，起步：配置 Schema 扩展）

当前分支：main

HEAD：203d4df（Phase 3 完成提交）

工作区状态：干净

本轮获准任务：Phase 3 已人工验收（2026-10-13）；授权进入 Phase 4 高级模式（完整参数、预设管理、任务排序、诊断；两种模式共享核心，切换不重置参数）；推送已授权。

工作区状态：干净

本轮获准任务：Phase 2 已人工验收（2026-10-13）；授权进入 Phase 3 核心集成（全部已有稳定任务接入 GUI：状态同步、异常、停止、配置的逐项真机验收）；推送已授权。


已完成

- Phase 0：完整审计 + 测试基线 + 架构设计 + 路线图，已人工验收。
- Phase 1：八项全部完成并已人工验收。细节见 CHANGELOG.md 与 git 历史。
- 修复（用户报告：双击启动脚本崩溃）：launch_game 捕获启动异常（游戏清单 requireAdministrator，普通权限报 740）+ 三个启动器自动提权 + 新增「启动界面.bat」。测试 tests/test_device_launch.py 4 例。
- Phase 4 第 1 项 —— 配置 Schema v2：
  - config.py：CONFIG_SCHEMA_VERSION=2；新增 UiConfig（mode simple/advanced、theme dark/light，校验器）、PresetConfig（自定义预设）、fight.min_sanity（理智策略，计划中）、recruit.tag_priority（公招策略，计划中）、AppConfig.ui 与 AppConfig.custom_presets。
  - configsvc.py：注册 MIGRATIONS[1]（v1→v2 无字段搬移，仅刷新版本）。
  - config.example.json：升级到 v2 并附新字段。
  - 测试：迁移/校验/预设往返 4 例；本地真实 config v1→v2 无损加载验证；全套 80 例 exit=0。
- Phase 3 第 1 项 —— GUI 首页状态区：
  - worker.py：新增 task_state(task_id, 状态值) 与 seq_progress(已完成, 总数) 信号（由事件总线驱动，跨线程安全）。
  - 首页：运行状态标签（当前任务 — 状态机状态）+ 序列进度条；开始→准备中，结束→「已结束（k/n 成功）」。
  - 真机验证：跑 StartUp 时状态区「准备中…」+ 进度条可见，结束「已结束（1/1 成功）」。
  - 测试：tests/test_gui.py 新增 2 例（状态区流转 / worker 信号齐全），全套 74 例 exit=0。
- Phase 2 第 1 轮：
  - PySide6 6.12.0 加入 requirements/pyproject；NOTICE 增加 PySide6 LGPL 声明。
  - 新增 src/ak_auto/gui/：theme.py（深色设计令牌 + QSS + QPalette）、worker.py（TaskWorker(QThread) 桥接 ExecutionController：事件/结果经 Qt 信号回传、stop() 协作取消、finally 还原窗口）、main_window.py（侧边导航 + 四页面：首页（运行 StartUp/停止 + 日志窗）、任务中心（任务目录勾选展示）、运行记录、设置占位）、app.py（run_gui 入口）。
  - __main__.py 新增 `gui` 命令。
  - 测试：tests/test_gui.py 4 例（offscreen 冒烟：主窗口/主题/任务页/Worker 类型）。
  - 真机验证：真实窗口启动（1024×680、深色主题、2 秒自动关闭退出码 0）——DPI/字体/线程三风险的首项目检通过。
- Phase 2 第 2 轮：
  - 任务中心：勾选（任务目录全量，默认每日常规）+ 三个推荐预设（每日常规/快速收菜/公招与信用）+ `_sequence()` 生成执行序列（非 StartUp 前插 ReturnToHome，与 CLI daily 一致）+「开始执行」。
  - 首页：连接状态行（识别资源 + 游戏窗口，AssetManager/device 只读检查）；开始执行后自动切回首页看日志。
  - 真机验证：GUI 点击「运行 StartUp」→ TaskWorker → 真实 ExecutionController → StartUp OK（3.6s），事件实时进日志窗，停止按钮状态正确，退出码 0。
- Phase 2 第 3 轮：
  - 新增 src/ak_auto/gui/pages.py：SettingsPage（游戏路径/关卡/次数/用药/碎石/重试 编辑 + 保存（ConfigurationService 原子写）+ 恢复默认 + 付费资源风险提示）、RunLogPage（读 logs/run-*.json 列表 + 详情渲染）。
  - worker.py：任务结束自动保存运行报告（logs/run-*.json），运行记录页随之刷新。
  - 修复：Qt offscreen 与 MaaFw 同进程的解释器退出崩溃（0xC0000409）——模块级清理 fixture（deleteLater + processEvents），全套 exit=0。
- Phase 2 第 4 轮（收尾）：
  - 新增 src/ak_auto/gui/wizard.py：FirstRunWizard（欢迎 → 环境检查 → 游戏路径 → 资源准备 → 完成保存），首次运行（无 config.json）自动弹出；设置页加「重新运行首次向导」。
  - 首页加「上次结果」行（读最新 logs/run-*.json 摘要，运行结束后自动刷新）。
  - **真机验证：GUI 内停止真实任务**——任务中心勾选 StartUp/AwardVisit/Infrast/Mall 执行中点击停止 → post_stop → 当前任务 CANCELLED → 剩余任务全部跳过 → 窗口还原、退出码 0。
  - 测试：wizard 冒烟 1 例；全套 68 例 exit=0。


进行中 / 待办

Phase 4 高级模式（按 AGENTS.md 第 3 节）：
1. 配置 Schema v2：模式（simple/advanced）、自定义预设存储、任务排序、理智/公招/信用策略、重试/超时、诊断开关；迁移 v1→v2 —— 本轮做。
2. GUI 模式切换（简单/高级，切换不重置参数）+ 高级设置页（参数范围验证/推荐值/恢复默认/风险提示）。
3. 预设管理：保存/重命名/删除自定义预设（与推荐预设区分）。
4. 诊断入口：GUI 内跑 doctor/probe、日志级别、失败截图开关。
5. 全部完成后提交 Phase 4 验收报告，等人工验收。


修改文件

- 本轮起：src/ak_auto/gui/（新增）、requirements.txt/pyproject.toml（加 PySide6）、NOTICE.md（LGPL 声明）、__main__.py（gui 命令）、tests/（GUI 冒烟测试）、docs/agent/STATE.md、CHANGELOG.md


测试与验证

命令	结果	环境/备注
python -m pytest -q	77 passed，exit=0（新增：重试链路 3 例、状态区 2 例）	Python 3.12.10 / pytest 9.1.1
逐项验收矩阵	9/10 任务 OK；Fight 已知失败（P1）	本机真实游戏，详见 docs/architecture/PHASE3_ACCEPTANCE.md
GUI 完整日常	16/17 成功，状态区「已结束（16/17 成功）」，失败原因可见	本机真实游戏
缺失节点异常	GhostTask → FAIL (missing-node)，exit 1，无崩溃	本机
配置生效	真机：task_order 被采纳；单测：设置往返 + retry 链路；fight.stage 未生效（Fight P1 缺陷）	—


已知问题 / 风险 / 阻塞

- GUI 与真实游戏并发使用时会抢输入控制者（GameWindowAdapter 已做单控制器互斥，GUI 内串行任务）。
- native_wheel（真实光标滚动）执行期间会抢用户鼠标，GUI 运行刷图任务时应提示用户勿动鼠标。
- 高 DPI/中文字体需真机目检（本轮原型验证点）。
- 沿用 Phase 0 审计风险清单其余项（Fight 选关、连战次数两缺陷、固定坐标脆弱等，属 Phase 5 范围）。


待真机验证

- GUI 窗口在 125%/150% DPI 下的布局与字体；
- GUI 内启动/停止真实任务的完整链路（首轮原型即验证 StartUp 一次）。


设计决策及 ADR

- ADR-0001：GUI 框架 PySide6 + Qt Widgets —— 随 Phase 2 授权确认采纳。
- ADR-0002：协作式取消（post_stop + 轮询）—— 已真机验证。


下一轮第一步

1. 重新读取 AGENTS.md、SESSION_START.md、本文件与 docs/ROADMAP.md。
2. 继续 Phase 4 第 1 项：配置 Schema v2 + 迁移，先输出计划再动手。


阶段验收状态


Phase 0：✅ 已人工验收（2026-10-13）
Phase 1：✅ 已人工验收（2026-10-13）
Phase 2：✅ 已人工验收（2026-10-13）
Phase 3：✅ 已人工验收（2026-10-13）
Phase 4：进行中（起步）
