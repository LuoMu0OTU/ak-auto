# ak-auto 仓库审计（Phase 0）

> 审计日期：2026-10-13
> 依据：AGENTS.md 第 1/11 节。本文件只陈述**由代码与测试验证过的事实**，不重复 README 的自我描述。
> 审计范围：`src/`、`assets/resource/pipeline/`、`config/`、`tools/`、`tests/`、`pyproject.toml`、`requirements.txt`、`LICENSE`、`NOTICE.md`、`.gitignore`、根目录启动脚本。

## 1. 仓库概览与规模

| 项 | 事实 |
|---|---|
| 语言/运行时 | Python 3.12（`requires-python >=3.12,<3.13`，实测 3.12.10；3.14 缺 onnxruntime 轮子） |
| 核心依赖 | `maafw==5.14.3`、`numpy`、`Pillow`、`pydantic>=2.6`、`typer`；dev: `pytest` |
| 代码规模 | `src/` 15 个文件约 1000 行；`tools/` 5 个脚本约 600 行 |
| 流水线 | `assets/resource/pipeline/` 7 个 JSON，共 69 个节点、10 个入口任务 |
| 测试 | `tests/` 4 个文件、15 个用例（实测 15 passed，49.21s） |
| 界面 | **无 GUI**；CLI（Typer）+ 3 个双击 .bat（GBK 编码）+ 生成器 `tools/make_launchers.py` |
| 许可证 | 项目 AGPL-3.0（LICENSE）；MAA 资源 AGPL-3.0（NOTICE.md + MANIFEST）；MaaFramework LGPL-3.0（运行时动态调用） |

## 2. 入口点

| 入口 | 作用 |
|---|---|
| `python -m ak_auto` / `ak-auto` | Typer CLI（`pyproject [project.scripts]`） |
| `doctor` | 环境/资源/窗口/截图自检 |
| `probe` | 窗口探测 + 截图/输入方式推荐 + `--click` 点击测试 |
| `fetch-assets` | 委托 `tools/fetch_maa_assets.py` 拉取 MAA 资源 |
| `run <Task>` | 连接游戏运行单个流水线入口 |
| `daily` | 按 `runtime.task_order` 顺序跑日常（每任务前插 ReturnToHome） |
| `lint` | 委托 `tools/pipeline_lint.py` |
| `restore` | 还原被 MaaFw 伪最小化的游戏窗口（新加） |
| `首次安装.bat` / `启动日常.bat` / `静默日常.bat` | 双击启动（**必须 GBK 编码**；UTF-8 会让 cmd 把半行当命令） |

## 3. 模块依赖与调用链

```
CLI (__main__)
 ├─ config.AppConfig（Pydantic，config/config.json，缺字段回退默认）
 ├─ device（init_maa / find_game_window / ensure_game_window / connect_controller
 │         / capture / native_wheel / bright_rows / restore_window）
 ├─ runtime（load_resource + build_tasker + 注册 custom actions）
 ├─ scheduler（run_task / run_sequence，TaskResult）
 └─ report（RunReport → 控制台 + logs/run-*.json）
      ↓
MaaFw：Tasker.bind(Resource, Win32Controller) → post_task(entry)
      ↓
pipeline JSON（识别/动作/next/on_error）+ Python CustomAction
（RecruitSelectTags / MallSelectBuy / FightSetRepeatCount）
      ↓
data/（stages.json、recruitment.json —— assets/maa-vendor 下的 MAA 数据表）
```

**事实**：
- 任务在代码里只是**流水线入口名字符串**（`runtime.task_order`），没有类型化的任务定义、参数 Schema、风险等级等（AGENTS.md 第 2.5 条要求，是 Phase 1 的主要缺口）。
- 状态只有 `TaskResult(entry, ok, status, duration_ms, nodes)`；无 run_id、无事件流、无 Pending/Stopping/Cancelled 状态机（第 2.6/2.7 条）。
- CLI 与（未来）GUI 将共用的业务核心目前就是 `scheduler + runtime`；GUI 尚未存在。

## 4. 线程模型与停止行为

| 项 | 事实 |
|---|---|
| 线程模型 | 应用本体**同步单线程**（所有 Job 均 `.wait()`）；并发在 MaaFw 内部线程（日志 Tx/Px） |
| 停止行为 | **无协作式取消**：`run_task` 阻塞到任务结束/节点超时（next 列表默认 20s）；控制台 Ctrl+C = 强杀进程 |
| 强杀后遗症 | MaaFw 运行期把窗口「伪最小化」挪到屏幕外；正常退出时 `restore_window` 还原，强杀则卡在最小化（`ak_auto restore` 兜底） |
| 输入独占 | 单控制器单窗口（符合第 2.4 条）；无并发运行的互斥防护 |
| 真实光标副作用 | `device.native_wheel` 会移动**真实鼠标光标**并发送硬件滚轮（该游戏不认 SendMessage 滚轮） |

## 5. 安全与运行可靠性（对照 AGENTS.md 第 5 节）

| 条目 | 现状 |
|---|---|
| 执行前确认窗口 | ✅ 进程名优先匹配（防误点标题含「明日方舟」的浏览器/聊天窗） |
| 分辨率依赖集中管理 | ⚠️ 固定坐标**遍布 pipeline JSON**（1280×720 / 16:9 / UI 100% 基线），无集中清单/校验；不可声称任意分辨率可用 |
| 循环/等待有上限 | ✅ next 列表默认 20s 超时；⚠️ 少数固定 300s（Fight 战斗等待） |
| 付费资源默认关闭 | ✅ `medicine=0`/`stone=0` 默认；但无「独立显式授权」流程（仅配置项） |
| 不注入/不改游戏 | ✅ 仅截图 + 窗口消息/硬件输入 |
| 隐私 | ⚠️ 日志含窗口标题、截图存 debug/（gitignored）；未系统审查敏感信息最小化 |
| 失败恢复 | ⚠️ 重试次数有限（retry_per_task=2）；失败任务跳过继续，无失败恢复策略层 |

## 6. 配置现状

- Pydantic 模型 + JSON，缺字段回退默认（有测试覆盖）。
- `dump()` 整文件重写，**无原子写入、无备份、无版本号（schema_version）、无旧版迁移、无损坏恢复**（第 3 节「配置原则」要求）。
- 推荐预设/自定义预设：**不存在**（仅 task_order 一个列表）。
- 简单/高级模式：**不存在**（尚无 GUI）。
- ⚠️ 代码内硬编码默认路径 `E:\Arknights\Arknights.exe`（`config.py`），违反「禁止硬编码本机路径」。

## 7. 功能状态（以本仓库真机验证为准，非 README 自述）

| 功能 | 状态 | 证据 |
|---|---|---|
| StartUp / ReturnToHome / 关弹窗 | ✅ 已真机验证 | 本机多次运行 OK |
| 公开招募（选标签/9h/多槽循环） | ✅ 已真机验证 | 4 槽招募完成 |
| 基建收菜（铃铛 → 逐个点待办） | ✅ 已真机验证 | 待办清空 |
| 好友访问（好友列表 → 访问基建 ×10） | ✅ 已真机验证 | 10 次访问完成 |
| 信用商店采购（只买加急许可） | ✅ 已真机验证 | 购买成功 |
| Award / AwardMail / AwardSignIn | ✅ 已真机验证 | 领取完成 |
| daily 全流程 | ✅ 已真机验证 | 100.1s 跑通（Fight 除外） |
| Fight 单场战斗循环 | ✅ 已真机验证 | 开始→编队→代理→结算→回列表 |
| Fight 选关 | ❌ 已知失败 | 「前往上一次作战」会飘到 EP16/矢量突破等 |
| Fight 连战次数自动选择 | 🔶 部分实现 | 计算+真实滚轮+白色行检测已通；**单次消耗读取 ROI 不准、点完会卡住** 两问题未解决 |
| 基建换班（shift_presets） | ⏳ 计划中 | 未实现；工作区有未提交的「制造/贸易停工」节点改动（来源待确认，已保留） |
| 吃药/碎石 | ⏳ 未实现（配置占位） | medicine/stone 恒 0 |
| 定时任务/插件/自动更新 | ⏳ 计划中 | — |

## 8. 测试覆盖

| 层 | 现状 |
|---|---|
| 单元测试 | config 5 例、pipeline lint 3 例、资源清单 5 例、资源加载 2 例，共 **15** |
| 缺口 | `device`/`scheduler`/`report`/custom actions **无单测**；无 Fake/Mock 设备；无 GUI 测试；无 CI |
| 真机验证 | 依赖人工（本会话已完成大量真机验证，见 Git 历史 commit 记录） |
| 资源完整性 | MANIFEST + SHA256 + 数据表/OCR 存在性有测试 |

## 9. 风险清单（摘要）

1. **固定坐标脆弱**：PC 客户端分辨率/UI 缩放一变即失效；坐标散落 JSON，无集中登记。
2. **无任务抽象**：字符串任务名 + 无参数 Schema，GUI 接入需要 Phase 1 统一任务接口。
3. **无取消与状态机**：长期阻塞任务只能杀进程；无事件流，UI 进度/停止无从谈起。
4. **配置无版本/迁移/原子写**。
5. **伪最小化后遗症**：异常退出会留下「打不开」的窗口（已有 restore 兜底，但根因是 MaaFw 行为）。
6. **真实光标滚动**：native_wheel 会抢用户鼠标，与 GUI 并行使用需互斥。
7. **Fight 选关不稳定**：P1 阻塞项。
8. **连战次数功能未完成**：两处已知缺陷。
9. **硬编码本机路径**（config.py 默认 game_path）。
10. **测试基线偏薄**：核心逻辑（scheduler/device/report）无自动化测试，重构前需先补。

## 10. 未提交改动（保留不动）

`assets/resource/pipeline/infrast.json`（工作区未提交）：新增 `Infrast@MfgStopped`/`Infrast@TradeStopped`（处理制造/贸易停工待办）。来源待项目负责人确认；按宪章第 9 节**不覆盖、不清理、不擅自提交**。
