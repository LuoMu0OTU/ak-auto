# ak-auto — 明日方舟本地自动化助手

一个跑在本机、由 [MaaFramework](https://github.com/MaaXYZ/MaaFramework)（`MaaFw` Python 绑定）驱动的
明日方舟自动化程序。目标端为**官方 PC 客户端**（`E:\Arknights\Arknights.exe`），无需模拟器。

> ⚠️ 本项目为非官方、非营利的个人辅助工具，与鹰角网络 / MAA 项目组无隶属关系。
> 使用本工具可能违反游戏服务条款，存在账号风险，请自行评估并承担后果。

## 功能（首期 = 日常全家桶）

- 启动游戏、回到主界面、消化公告/断线/活动弹窗
- 公开招募（标签识别 + 保底 4★ 词条匹配）
- 基建收菜 + 按预设干员换班
- 自动刷理智（指定关卡/材料，理智耗尽或次数到限停止；用药/碎石默认关闭）
- 信用商店按优先级购买
- 日常/周常任务、邮件、签到领取
- 一条命令跑完整套日常，输出运行报告

## 环境要求

- Windows 11（10.0.1903+），已安装**明日方舟官方 PC 客户端**
- Python **3.12**（⚠ 3.14 下 `onnxruntime` 等轮子缺失，不要用默认 `python`）
- 游戏窗口建议窗口化 **1280×720（16:9）**，并在游戏内 `设置 - 游戏` 把 **UI 缩放改为 100**
  （识别模板按 16:9 的 720p 标定；16:10 / 全屏会导致模板对不齐，参考 MAA PC 端同款要求）

## 安装

```powershell
# 用 3.12 建虚拟环境
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .   # 安装本项目包（提供 ak-auto 命令）

# 组装 MAA 识别资源（模板图 / OCR 模型 / 数据表）
.\.venv\Scripts\python.exe -m ak_auto fetch-assets --tag v6.19.0
```

## 配置

复制并编辑本机配置：

```powershell
Copy-Item config\config.example.json config\config.json
```

关键项见 `config\config.example.json`（含字段说明）。至少确认 `startup.game_path` 与 `device.window_match`。

## 使用

```powershell
.\.venv\Scripts\python.exe -m ak_auto doctor          # 环境/资源/窗口/截图自检
.\.venv\Scripts\python.exe -m ak_auto probe           # 探测窗口与截图/输入方式，输出推荐配置
.\.venv\Scripts\python.exe -m ak_auto run Fight --stage CE-6   # 单任务
.\.venv\Scripts\python.exe -m ak_auto daily           # 日常全家桶
.\.venv\Scripts\python.exe -m ak_auto lint            # 流水线静态校验
```

运行日志：`logs/`；失败截图与识别可视化：`debug/`。

## 许可证

- 本项目代码与整体仓库：**AGPL-3.0**（见 `LICENSE`）
- 识别素材大量复用 [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights)
  （AGPL-3.0，tag v6.19.0）；来源与许可详见 `NOTICE.md`
- 运行时框架 [MaaFramework](https://github.com/MaaXYZ/MaaFramework)（LGPL-3.0）通过 `MaaFw` 动态调用

## 目录结构

```
assets/resource/pipeline/   自写流水线 JSON（MaaFw 协议）
assets/resource/image/      模板图（由 fetch-assets 生成）
assets/resource/model/ocr/  OCR 模型（由 fetch-assets 生成）
assets/maa-vendor/          数据表（由 fetch-assets 生成）
src/ak_auto/                应用代码
tools/                      资源获取 / 窗口探测 / 流水线校验
tests/                      测试
```

## 参考

- [MaaFramework 文档](https://maafw.com/)
- [MaaFramework Pipeline 协议](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/3.1-%E4%BB%BB%E5%8A%A1%E6%B5%81%E6%B0%B4%E7%BA%BF%E5%8D%8F%E8%AE%AE.md)
- [MaaFramework Win32 控制方式](https://github.com/MaaXYZ/MaaFramework/blob/main/docs/zh_cn/2.4-%E6%8E%A7%E5%88%B6%E6%96%B9%E5%BC%8F%E8%AF%B4%E6%98%8E.md)
- [MaaAssistantArknights](https://github.com/MaaAssistantArknights/MaaAssistantArknights)
