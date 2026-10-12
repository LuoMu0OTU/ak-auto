# NOTICE — 第三方资源来源与许可

本项目的**代码**为原创，但**识别素材**大量复用他人开源资源。本文件记录来源、版本与许可，
以满足相应许可证的署名与溯源要求。

---

## 1. MaaAssistantArknights（MAA）

- 上游仓库：https://github.com/MaaAssistantArknights/MaaAssistantArknights
- 使用版本（tag）：**v6.19.0**
- 上游许可：**AGPL-3.0**（本项目的 `LICENSE` 采用同一许可证，以履行 AGPL 的传染性义务）

### 1.1 实际复用的内容

由 `tools/fetch_maa_assets.py` 自动获取，**仅做复制、筛选与重命名，不修改文件内容**：

| 来源路径（MAA 仓库） | 目标路径（本项目） | 说明 |
| --- | --- | --- |
| `resource/template/**/*.png` | `assets/resource/image/**` | 720p 基准的模板匹配图 |
| `resource/PaddleOCR/det/inference.onnx` | `assets/resource/model/ocr/det.onnx` | 文本检测模型（仅重命名） |
| `resource/PaddleOCR/rec/inference.onnx` | `assets/resource/model/ocr/rec.onnx` | 文本识别模型（仅重命名） |
| `resource/PaddleOCR/rec/keys.txt` | `assets/resource/model/ocr/keys.txt` | 字符表 |
| `resource/stages.json` | `assets/maa-vendor/stages.json` | 关卡数据 |
| `resource/recruitment.json` | `assets/maa-vendor/recruitment.json` | 公开招募词条 |
| `resource/infrast.json` | `assets/maa-vendor/infrast.json` | 基建设施/干员数据 |
| `resource/item_index.json` | `assets/maa-vendor/item_index.json` | 物品索引 |
| `resource/battle_data.json` | `assets/maa-vendor/battle_data.json` | 战斗数据 |
| `resource/Arknights-Tile-Pos/**` | `assets/maa-vendor/Arknights-Tile-Pos/**` | 关卡地形坐标 |
| `resource/platform_diff/PC/resource/**` | 合并进 `assets/resource/**` | PC 端差分资源 |

### 1.2 明确**未**复用的内容

- `resource/tasks/**/*.json`（MAA 的**任务流程协议**，字段为 `algorithm` / `specificRect` /
  `rectMove` / `specialParams` / `baseTask`）**不能**被 MaaFramework 的**任务流水线协议**
  （字段为 `recognition` / `roi` / `template` / `expected`）直接解析，因此本项目**没有**复用这些
  流程定义。`assets/resource/pipeline/` 下的流水线 JSON 均为本项目自行编写；MAA 的 `tasks.json`
  仅在开发期作为 ROI 与流程分支的**离线参考**，不进入本仓库、不进入发行产物。

### 1.3 生成物与版本溯源

`tools/fetch_maa_assets.py` 在获取资源后会写出 `assets/MANIFEST.json`，记录：

- 上游仓库、tag、commit SHA
- 每个来源文件 → 目标路径
- 目标文件的 SHA256
- 上游许可证标识

`assets/maa-vendor/`、`assets/resource/image/`、`assets/resource/model/ocr/`、
`assets/MANIFEST.json` 均由该脚本生成，已在 `.gitignore` 中排除，可随时用同一 tag 重现。
`assets/resource/image/source-map.json` 额外记录「本项目所用模板 → MAA 原始路径」的对应关系。

---

## 2. MaaFramework / MaaFw

- 上游仓库：https://github.com/MaaXYZ/MaaFramework
- 上游许可：**LGPL-3.0**
- 使用方式：通过 PyPI 包 `MaaFw`（含预编译二进制）**动态调用**，本项目未修改其源代码。
- 上游附带的 `DirectML.dll`（Windows GPU 加速用，非 LGPL 部分）随 MaaFw 分发，本项目未改动。

---

## 3. 商标与免责

「明日方舟 / Arknights」为鹰角网络（Hypergryph）的商标与作品。本项目为非官方、非营利的个人辅助工具，
与鹰角网络及 MAA 项目组无任何隶属关系。使用者需自行承担使用风险，并遵守游戏服务条款与适用法律。
