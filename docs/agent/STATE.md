Agent 可恢复工作状态


每轮结束、上下文压缩前更新。这里记录当前事实，不代替 AGENTS.md 的长期规则。




更新日期：2026-10-13

当前阶段：Phase 2 GUI 基础（四项全部完成，待人工验收；期间修复用户报告的双击启动崩溃）

当前分支：main

HEAD：72b105a（第 4 轮提交；本轮修复提交号见 git log 最新一条）

工作区状态：干净

本轮获准任务：Phase 2（经人工授权）待验收；本轮为用户报告的 bug 修复（双击启动崩溃），推送已授权。


已完成

- Phase 0：完整审计 + 测试基线 + 架构设计 + 路线图，已人工验收。
- Phase 1：八项全部完成并已人工验收。细节见 CHANGELOG.md 与 git 历史。
- 修复（用户报告：双击启动脚本崩溃）：
  - 根因 1：`launch_game` 的 `Popen` 抛异常未捕获（游戏清单 requireAdministrator → 普通权限 CreateProcess 报 740）→ daily 直接崩出 traceback。已改为捕获 PermissionError/OSError 并播报具体原因与处理建议（提权运行或手动开游戏），返回 False 走干净错误路径。
  - 根因 2：DSH/开发 shell 是管理员权限，掩盖了「普通用户双击无法拉起游戏」的问题。已给会拉起游戏的三个启动器加自动提权头（whoami 检查 High Mandatory Level → 非提权时 PowerShell Start-Process -Verb RunAs 弹一次 UAC），并新增「启动界面.bat」。
  - 测试：tests/test_device_launch.py 4 例（路径缺失/权限不足/OSError/正常启动）；README 更新说明 UAC 与四个脚本。
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

- 等人工验收 Phase 2（验收点见下）。
- 验收通过后：Phase 3 核心集成（全部稳定任务在 GUI 内逐项验证状态/停止/配置同步；当前任务中心已能跑全部任务，Phase 3 为逐项真机验收）。


修改文件

- 本轮起：src/ak_auto/gui/（新增）、requirements.txt/pyproject.toml（加 PySide6）、NOTICE.md（LGPL 声明）、__main__.py（gui 命令）、tests/（GUI 冒烟测试）、docs/agent/STATE.md、CHANGELOG.md


测试与验证

命令	结果	环境/备注
python -m pytest -q	72 passed，exit=0	Python 3.12.10 / pytest 9.1.1
坏路径 daily 失败路径	三条干净提示（路径不存在/启动失败/窗口未找到），无 traceback	本机
游戏清单核实	Arknights.exe 内嵌 requireAdministrator → 双击需 UAC，启动器已自动提权	—
提权头逻辑	whoami 检查 High Mandatory Level 在本机验证通过	本机
真机 GUI 启动/跑任务/停止	见 Phase 2 各轮记录	本机真实游戏


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
2. git status / git log 确认本轮提交与工作区状态。
3. 若 Phase 2 已人工验收：进入 Phase 3 核心集成（逐项真机验收全部稳定任务在 GUI 内的状态/停止/配置同步）。


阶段验收状态


Phase 0：✅ 已人工验收（2026-10-13）
Phase 1：✅ 已人工验收（2026-10-13）
Phase 2：四项全部完成 + 测试全绿 + 真机跑/停验证通过 —— 待人工验收
