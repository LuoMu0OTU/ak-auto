Agent 可恢复工作状态


每轮结束、上下文压缩前更新。这里记录当前事实，不代替 AGENTS.md 的长期规则。




更新日期：2026-10-13

当前阶段：Phase 2 GUI 基础（进行中，起步：PySide6 依赖 + 最小窗口原型）

当前分支：main

HEAD：297699b（Phase 1 完成提交；本轮提交号见 git log 最新一条）

工作区状态：干净

本轮获准任务：Phase 1 已人工验收（2026-10-13）；授权进入 Phase 2（GUI 基础），ADR-0001（PySide6）随之确认采纳；推送已授权。


已完成

- Phase 0：完整审计 + 测试基线 + 架构设计 + 路线图，已人工验收。
- Phase 1：八项全部完成并已人工验收（TaskDefinition 目录 / 状态机与 ExecutionResult / 事件总线 / ExecutionController 取消 / ConfigurationService / 三个基础设施适配器 / 共享 Fake + 录制截图回归 / CLI 真机验收与 post_stop 真机验证）。59 个测试全绿。细节见 CHANGELOG.md 与 git 历史。


进行中 / 待办

Phase 2 GUI 基础（按 AGENTS.md 第 3/4 节 + ROADMAP）：
1. PySide6 依赖（requirements + NOTICE 许可声明）—— 本轮做。
2. 最小窗口原型：主窗口 + 深色主题 + 首页 + 一个真实任务按钮（StartUp）+ QThread 桥接（ExecutionController/事件/取消），验证 DPI/字体/线程三条风险 —— 本轮做。
3. 页面扩展：任务中心（勾选 + 推荐预设）、运行记录、设置（ConfigurationService 读写）。
4. 首次启动向导（环境检查/游戏路径/资源准备/配置验证/试运行）。
5. `ak_auto gui` 命令入口 + 冒烟测试。
（第 3–5 项分轮推进，每轮小步 + 可验证。）


修改文件

- 本轮起：src/ak_auto/gui/（新增）、requirements.txt/pyproject.toml（加 PySide6）、NOTICE.md（LGPL 声明）、__main__.py（gui 命令）、tests/（GUI 冒烟测试）、docs/agent/STATE.md、CHANGELOG.md


测试与验证

命令	结果	环境/备注
python -m pytest -q	59 passed	Phase 1 基线
（本轮 GUI 新增后补充）	—	—


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
