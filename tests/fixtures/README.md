# 截图回归夹具说明

本目录存放**精选小尺寸截图夹具**（非临时抓帧；`*.tmp.png` 不入库），供离线回归测试使用。

## 采集流程（真机，1280×720 / 16:9 / UI 缩放 100%）

1. 连接游戏（`ak_auto run ReturnToHome` 或 GUI 内连接）；
2. 用设备捕获当前画面并**裁剪到被测元素区域**（缩小体积，也避免把整屏游戏画面入库）：

```python
from ak_auto import device
from ak_auto.application import ConfigurationService
from ak_auto.infrastructure import GameWindowAdapter

device.init_maa()
cfg = ConfigurationService().load()
adapter = GameWindowAdapter(cfg)
hwnd, ctrl = adapter.acquire()
img = device.capture(ctrl)
crop = img[160:640, 950:1110]      # 例子：次数选择器竖条
device.save_image(crop, "tests/fixtures/selector_rows.png")
adapter.release(restore=True)
```

3. 编写离线断言（参考 `tests/test_bright_rows.py`）：对夹具运行被测的纯图像逻辑，
   断言与真机观测一致（如「白色数字行 ≥ 2 个」）。

## 现有夹具

| 文件 | 内容 | 用途 | 测试 |
|---|---|---|---|
| `selector_rows.png` | 真机录下的连战次数列表裁剪（160×480） | 白色数字行检测回归 | test_bright_rows.py |

## 约束

- 夹具应裁剪到必要区域，避免整屏游戏画面入库；
- 采集时注意游戏内不处于付费确认等敏感界面；
- 断言用**容差/区间**（识别类逻辑不追求像素级精确），避免游戏皮肤微调导致误报。
