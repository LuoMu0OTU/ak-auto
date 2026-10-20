# 构建与发布（BUILD）

> 目标平台：Windows 10/11 x64；Python 3.12；MaaFw 5.14.3；打包方案见 ADR-0003。

## 一、开发环境

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"          # 运行时依赖 + pytest + pyinstaller
python -m ak_auto fetch-assets   # 组装 MAA 识别资源（首次，需联网，幂等）
python -m pytest -q              # 113 例全绿
python -m ak_auto lint           # 流水线 0 错误 0 警告
```

## 二、构建便携包

```powershell
python tools/build_windows.py            # 全量构建（--clean）
python tools/build_windows.py --no-clean # 增量
python tools/build_windows.py --smoke    # 构建后启动 GUI 冒烟
```

产物：`dist/AkAuto/`

```
AkAuto/
  ak-auto.exe          双击启动 GUI（首次弹「首次启动向导」）
  _internal/           运行时 + 只读资源（流水线/数据表/配置模板）
  assets/  config/  logs/   首启由程序 bootstrap 到 exe 旁（可写数据）
```

要点：

- **配置与程序分离**：可写数据（config/logs/下载的识别资源）都在 exe 旁目录，`_internal` 只读。
- **识别资源不进包**：模板图/OCR 模型（数百 MB）由首次启动的 fetch-assets 按 `MANIFEST.json` 下载+校验。
- **控制台策略**：以 console 模式构建（窗口版引导器在本机于 Python 之前静默崩溃），GUI 启动时隐藏控制台并把输出重定向到 `logs/console.log`；带参数运行（`ak-auto.exe doctor` / `daily` 等）走 CLI、保留控制台输出。
- 升级：替换 `ak-auto.exe` + `_internal/`，数据目录不动。

## 三、CI

`.github/workflows/ci.yml`：`test`（pytest + 流水线 lint，windows-latest）→ `build`（PyInstaller 构建 + doctor 冒烟 + 上传 artifact）。

## 四、干净机验收清单（发布前必做）

**无第二台机器时的替代（已做过）**：把 `dist/AkAuto/` 整体复制到一个与仓库/venv 无关的全新目录
（如 `%TEMP%\AkAuto-CleanTest`），运行 `ak-auto.exe doctor`——Python、MaaFw（动态库）、
游戏路径检测均通过，即证明便携包**自包含、不依赖开发环境**。

**剩余系统级依赖**（无法靠复制目录排除，真正干净机需注意）：

- **VC++ 运行库**：PyInstaller 打包的 `python312.dll` 依赖 `vcruntime140.dll`（VS2015-2022 再发行包）。
  Windows 10/11 不自带；若干净机双击报「缺少 vcruntime140.dll」，安装
  [Microsoft Visual C++ Redistributable (x64)](https://aka.ms/vs/17/release/vc_redist.x64.exe) 即可。
  发布包可在 README/下载页标注此依赖。

**有干净机时**（未装 Python 的 Windows 10/11 x64）：

1. 解压 `dist/AkAuto/` 到任意目录，双击 `ak-auto.exe`。
2. 首次启动向导完成环境检查 → 资源下载（fetch-assets，需联网）。
3. 连接游戏（游戏路径/窗口检测通过）。
4. 勾选一个真实任务（如「返回主页」或「公开招募」）→ 开始 → 观察进度 → 安全停止。
5. 关闭后重新启动，确认配置与资源未丢失。
6. 用新版本替换 exe + `_internal`（保留数据目录），确认升级后配置/日志仍在。

**构建成功 ≠ 可发布**：以上真机步骤通过后方可发布。

## 五、发布步骤

1. `python -m pytest -q` + `python -m ak_auto lint` 全绿。
2. `python tools/build_windows.py`。
3. 干净机验收（上节）。
4. 打 tag（`vX.Y.Z`），CI 产出 artifact。
5. 更新 `CHANGELOG.md`；核对 `NOTICE.md`（AGPL/LGPL/第三方）无遗漏。
