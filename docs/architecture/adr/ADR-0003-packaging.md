# ADR-0003：Windows 打包方案选型（PyInstaller vs Nuitka）

- 状态：已采纳
- 日期：2026-10-17
- 依据：AGENTS.md §7「打包评估 PyInstaller/Nuitka」；Phase 6 发布工程

## 背景

ak-auto 需产出不依赖用户预装 Python 的 Windows 便携包，包含：

- Python 运行时 + 依赖：PySide6、pydantic、numpy、Pillow、typer、maafw==5.14.3（ctypes 绑定 MaaFramework 动态库的 wheel）；
- 仓库内只读资源：`assets/resource/pipeline/`（流水线 JSON）、`assets/maa-vendor/`（数据表）、`config/config.example.json`；
- 大体积识别资源（模板图/OCR 模型，数百 MB）**不随包分发**，由首次启动的 fetch-assets 流程按 MANIFEST 下载+校验。

## 候选对比

| 维度 | PyInstaller | Nuitka |
|---|---|---|
| PySide6/Qt 打包钩子 | 成熟（官方与社区钩子完善，窗口模式可直接打包） | 支持，但 Qt 插件/翻译资源需自行处理，坑多 |
| ctypes 绑定库（maafw） | 数据文件随 wheel 收集，稳定 | 同样可行，但二进制收集规则需手工维护 |
| 构建速度 | 分钟级，迭代快 | 首次编译 20-60 分钟，迭代慢 |
| 体积/启动速度 | 约 200-300 MB（PySide6 占大头），启动 2-5s | 略小、启动稍快，但差异不显著 |
| 反编译面 | Python 字节码（AGPL 开源项目，无保密诉求） | 编译为原生，防护更强（本项目不需要） |
| 社区验证与故障排查资料 | 极多 | 较少 |
| Windows 构建（CI） | 稳定 | 长耗时，CI 预算压力大 |

## 决策

**采用 PyInstaller（onedir 便携模式）**。

理由：

1. 本项目为 AGPL 开源项目，无代码保密诉求，Nuitka 的主要优势（防护）无意义；
2. PySide6 + maafw(ctypes) 的组合在 PyInstaller 下有成熟钩子，风险最低；
3. 构建快，本地与 CI 迭代成本低；体积差异对桌面工具不敏感；
4. 便携 onedir 模式与「配置与程序分离」天然契合：可写数据放 exe 旁目录，只读资源放 `_internal`。

## 打包形态

- `dist/AkAuto/ak-auto.exe`（onedir）：exe + `_internal/`（运行时与只读资源）。
- 首启 bootstrap：把 `_internal` 内的 `assets/resource/pipeline/`、`assets/maa-vendor/`、`config/config.example.json` 复制到 exe 旁数据目录（不存在时），之后所有读写都在数据目录进行（与开发模式同构）。
- 识别资源（模板图/OCR 模型）：首启 fetch-assets 进程内下载（工具模块 stdlib-only，可导入复用）。
- 升级策略：新版本替换 exe + `_internal`，数据目录保留（配置/日志/资源不回滚）。

## 后果

- 引入 PyInstaller 为开发期依赖（不入运行时依赖）。
- 需要 frozen 模式路径层（`sys.frozen` → exe 目录为 PROJECT_ROOT）。
- fetch_maa_assets 工具需模块化（可被进程内导入）。
