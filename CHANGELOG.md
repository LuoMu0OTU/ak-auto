# 变更记录（CHANGELOG）

> 只记录用户可见的变化。格式参考 Keep a Changelog；日期为本地时间。

## [0.2.0] - 2026-10-13 —— Phase 1 核心解耦

### 新增

- **统一任务目录**：10 个任务登记为 TaskDefinition（ID/名称/分类/参数/风险/前置条件等）；`python -m ak_auto tasks` 可查看；`run` 支持中文任务名（如 `run 公招`）。
- **执行状态机与事件**：任务全程带 run_id 与状态（含 CANCELLED）；控制台输出事件（▶开始/✔完成/✘失败）。
- **安全停止**：`run` / `daily` 按 Ctrl+C 优雅停止（不再直接杀进程），剩余任务跳过，游戏窗口自动还原。
- **配置服务**：`config.json` 支持 `schema_version`、原子写入、写前备份、损坏自动备份并回退默认、迁移钩子。

### 修复

- 进程被强杀后游戏窗口卡在最小化的问题：新增 `ak_auto restore` 一键还原，正常退出自动还原。

### 兼容

- CLI 命令与行为与之前一致；旧 `config.json`（无 schema_version）无损加载。

## [0.1.0] - 2026-10-12 —— 首个可用版本

- 明日方舟 PC 官服本地自动化：启动/回主界面/关弹窗、公招、基建收菜、好友访问、信用商店采购、任务/邮件/签到、刷图（单场）。
- CLI（`doctor`/`probe`/`fetch-assets`/`run`/`daily`/`lint`）+ 三个一键 .bat 启动脚本。
- 发布到 GitHub：LuoMu0OTU/ak-auto（公开，AGPL-3.0）。
