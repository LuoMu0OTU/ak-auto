Agent 可恢复工作状态


每轮结束、上下文压缩前更新。这里记录当前事实，不代替 AGENTS.md 的长期规则。




更新日期：2026-10-13

当前阶段：Phase 2 GUI 基础（进行中，起步：PySide6 依赖 + 最小窗口原型）

当前分支：main

HEAD：297699b（Phase 1 完成提交；本轮提交号见 git log 最新一条）

工作区状态：干净

本轮获准任务：Phase 2（经人工授权）。已完成第 1、2 轮（依赖+原型；任务中心勾选/预设/真实执行串联）；后续轮次继续设置读写/运行记录/向导；推送已授权。


已完成

- Phase 0：完整审计 + 测试基线 + 架构设计 + 路线图，已人工验收。
- Phase 1：八项全部完成并已人工验收。细节见 CHANGELOG.md 与 git 历史。
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


进行中 / 待办

Phase 2 后续轮次：
- 设置页：ConfigurationService 读写（关键项编辑 + 恢复默认 + 风险提示 + 保存）。
- 运行记录页：读 logs/run-*.json 展示。
- 首页完善：今日任务、最近结果（logs/ 读取）。
- 首次启动向导（环境检查/游戏路径/资源准备/配置验证/试运行）。
- GUI 停止真实任务的链路真机验证（TaskWorker.stop → post_stop）。


修改文件

- 本轮起：src/ak_auto/gui/（新增）、requirements.txt/pyproject.toml（加 PySide6）、NOTICE.md（LGPL 声明）、__main__.py（gui 命令）、tests/（GUI 冒烟测试）、docs/agent/STATE.md、CHANGELOG.md


测试与验证

命令	结果	环境/备注
python -m pytest -q	65 passed（15 旧 + 50 新）	Python 3.12.10 / pytest 9.1.1
python -m ak_auto --help	含 gui 命令	—
真机 GUI 启动	窗口 1024x680 深色主题渲染正常	本机真实桌面
真机 GUI 内跑任务	「运行 StartUp」→ StartUp OK（3.6s），事件实时进日志窗，停止按钮状态正确	本机真实游戏
GUI 内停止任务	未做	下一轮真机验证（TaskWorker.stop → post_stop）


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
2. 继续 Phase 2：装 PySide6 → 最小原型 → gui 命令 → 冒烟测试；先输出本轮计划再动手。


阶段验收状态


Phase 0：✅ 已人工验收（2026-10-13）
Phase 1：✅ 已人工验收（2026-10-13）
Phase 2：进行中（起步）
