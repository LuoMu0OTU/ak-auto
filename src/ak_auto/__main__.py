"""CLI 入口。

子命令：
  doctor       环境/资源/窗口/截图自检
  probe        探测窗口与截图/输入方式
  fetch-assets 组装 MAA 识别资源
  run          运行指定任务
  daily        日常全家桶
  lint         流水线静态校验
"""
from __future__ import annotations

import subprocess
import sys

import typer

app = typer.Typer(name="ak-auto", no_args_is_help=True, help="明日方舟本地自动化助手")


def _utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


@app.callback()
def _callback() -> None:
    _utf8()


@app.command("doctor")
def doctor() -> None:
    """环境 / 资源 / 窗口 / 截图自检。"""
    from ak_auto import device
    from ak_auto.config import AppConfig, PROJECT_ROOT

    checks: list[tuple[str, bool, str]] = []

    # Python 版本
    py = sys.version_info
    ok = (py.major, py.minor) == (3, 12)
    checks.append(("Python 3.12", ok, f"{py.major}.{py.minor}.{py.micro}" + ("" if ok else "（必须 3.12）")))

    # MaaFw
    try:
        import maa  # noqa: F401
        checks.append(("MaaFw 可导入", True, "ok"))
    except Exception as e:  # noqa: BLE001
        checks.append(("MaaFw 可导入", False, str(e)))

    # 资源
    manifest = PROJECT_ROOT / "assets" / "MANIFEST.json"
    ocr_dir = PROJECT_ROOT / "assets" / "resource" / "model" / "ocr"
    img_dir = PROJECT_ROOT / "assets" / "resource" / "image"
    ocr_ok = all((ocr_dir / f).is_file() for f in ("det.onnx", "rec.onnx", "keys.txt"))
    img_ok = img_dir.is_dir() and any(img_dir.rglob("*.png"))
    checks.append(("识别资源（MANIFEST）", manifest.is_file(), "存在" if manifest.is_file() else "缺失，请先 `fetch-assets`"))
    checks.append(("OCR 模型", ocr_ok, "就绪" if ocr_ok else "缺失，请先 `fetch-assets`"))
    checks.append(("模板图", img_ok, "就绪" if img_ok else "缺失，请先 `fetch-assets`"))

    # 游戏
    cfg = AppConfig.load()
    import os
    game = cfg.startup.game_path
    checks.append(("游戏路径存在", os.path.isfile(game), game))

    # 窗口
    try:
        device.init_maa()
        win = device.find_game_window(cfg)
        checks.append(("游戏窗口", win is not None, f"hwnd={win['hwnd']} title={win['window_name']!r}" if win else "未找到（游戏是否已启动？）"))
    except Exception as e:  # noqa: BLE001
        checks.append(("游戏窗口", False, str(e)))

    width = max(len(name) for name, _, _ in checks)
    for name, ok, msg in checks:
        mark = "OK " if ok else "FAIL"
        typer.echo(f"[{mark}] {name:<{width}}  {msg}")
    all_ok = all(ok for _, ok, _ in checks)
    typer.echo("\n结论：" + ("全部通过" if all_ok else "存在未通过项，按提示处理后重试"))
    raise typer.Exit(0 if all_ok else 1)


@app.command("probe")
def probe(
    list_only: bool = typer.Option(False, "--list", help="仅列出所有窗口"),
    click: str = typer.Option("", help="点击测试坐标 x,y"),
    out: str = typer.Option("", help="截图保存目录"),
) -> None:
    """探测窗口与截图/输入方式。"""
    import json

    from ak_auto import device
    from ak_auto.config import AppConfig, PROJECT_ROOT

    device.init_maa()
    cfg = AppConfig.load()

    if list_only:
        for w in device.list_windows():
            typer.echo(f"hwnd={w['hwnd']}\tclass={w['class_name']!r}\ttitle={w['window_name']!r}")
        return

    win = device.find_game_window(cfg)
    if not win:
        typer.echo("未找到匹配窗口。可用 --list 查看窗口列表，再改 config 里的 device.window_match。")
        raise typer.Exit(1)

    typer.echo(f"命中窗口: hwnd={win['hwnd']} class={win['class_name']!r} title={win['window_name']!r}")
    result = device.probe_best(cfg, win, save_dir=out or None)
    typer.echo(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))

    if click:
        try:
            x, y = (int(v) for v in click.split(","))
        except ValueError:
            typer.echo("--click 格式应为 x,y")
            raise typer.Exit(2)
        sc = device.parse_screencap(result.screencap)
        ctrl = device.connect_controller(
            win["hwnd"], sc,
            device.parse_input(result.mouse),
            device.parse_input(result.keyboard),
        )
        ctrl.post_click(x, y).wait()
        typer.echo(f"[click] 已点击 ({x},{y})，请查看游戏窗口是否响应。")


@app.command("fetch-assets")
def fetch_assets(tag: str = typer.Option("v6.19.0", help="MAA 发版 tag")) -> None:
    """组装 MAA 识别资源（委托给 tools/fetch_maa_assets.py）。"""
    from ak_auto.config import PROJECT_ROOT

    script = PROJECT_ROOT / "tools" / "fetch_maa_assets.py"
    raise typer.Exit(subprocess.run([sys.executable, str(script), "--tag", tag]).returncode)


@app.command("run")
def run(
    task: str = typer.Argument(..., help="任务名，如 StartUp / ReturnToHome / Fight / Infrast"),
    config: str = typer.Option("", "--config", help="config.json 路径"),
) -> None:
    """连接游戏并运行指定任务。"""
    from ak_auto import device
    from ak_auto.config import AppConfig
    from ak_auto.domain import resolve_task
    from ak_auto.runtime import build_tasker
    from ak_auto.scheduler import run_task

    # 任务名解析：先查任务目录（支持中文名），查不到则按原始流水线节点名执行（兼容）
    td = resolve_task(task)
    if td:
        entry = td.entry or td.id
        typer.echo(f"[task] {td.id} — {td.name}（{td.category}，风险：{td.risk_level}）")
        if td.risk_level == "high":
            typer.echo("        ⚠ 高风险任务：可能消耗理智或付费资源，请先确认 config 相关设置。")
    else:
        entry = task
        typer.echo(f"[task] 未登记任务，按原始流水线节点名执行：{entry}")

    device.init_maa()
    cfg = AppConfig.load(config or None)
    win = device.ensure_game_window(cfg, on_log=typer.echo)
    if not win:
        typer.echo("未找到游戏窗口，自动启动也没成功。请确认 config 的 startup.game_path，或手动打开游戏。")
        raise typer.Exit(1)

    try:
        sc = device.parse_screencap(cfg.device.screencap[0])
        ctrl = device.connect_controller(
            win["hwnd"], sc,
            device.parse_input(cfg.device.mouse_input[0]),
            device.parse_input(cfg.device.keyboard_input),
        )
        tasker = build_tasker(cfg, ctrl)
        result = run_task(tasker, entry)
        typer.echo(result.summary)
        for n in result.nodes:
            typer.echo(f"  - {n}")
        code = 0 if result.ok else 1
    finally:
        # MaaFw 会把游戏窗口伪最小化，结束前务必还原
        device.restore_window(win["hwnd"])
    raise typer.Exit(code)


@app.command("daily")
def daily(config: str = typer.Option("", "--config", help="config.json 路径")) -> None:
    """日常全家桶。"""
    from ak_auto import device
    from ak_auto.config import AppConfig
    from ak_auto.domain import resolve_task
    from ak_auto.report import make_report
    from ak_auto.runtime import build_tasker
    from ak_auto.scheduler import run_sequence

    device.init_maa()
    cfg = AppConfig.load(config or None)

    # 校验 task_order：不在任务目录里的项给出警告（是否真的执行由流水线节点是否存在决定）
    for t in cfg.runtime.task_order:
        if resolve_task(t) is None:
            typer.echo(f"[warn] runtime.task_order 里的 {t!r} 不在任务目录中，可能是无效任务")

    win = device.ensure_game_window(cfg, on_log=typer.echo)
    if not win:
        typer.echo("未找到游戏窗口，自动启动也没成功。请确认 config 的 startup.game_path，或手动打开游戏。")
        raise typer.Exit(1)

    try:
        sc = device.parse_screencap(cfg.device.screencap[0])
        ctrl = device.connect_controller(
            win["hwnd"], sc,
            device.parse_input(cfg.device.mouse_input[0]),
            device.parse_input(cfg.device.keyboard_input),
        )
        tasker = build_tasker(cfg, ctrl)
        # 每个任务前先回主界面，保证任务之间不串场
        entries: list[str] = []
        for t in cfg.runtime.task_order:
            if t != "StartUp":
                entries.append("ReturnToHome")
            entries.append(t)
        results = run_sequence(
            tasker,
            entries,
            cfg.runtime.retry_per_task,
            on_progress=typer.echo,
        )
        report = make_report(results)
        typer.echo("\n" + report.render())
        typer.echo(f"报告已保存：{report.save()}")
        code = 0 if report.all_ok else 1
    finally:
        device.restore_window(win["hwnd"])
    raise typer.Exit(code)


@app.command("tasks")
def tasks() -> None:
    """列出任务目录（ID / 名称 / 分类 / 风险）。"""
    from ak_auto.domain import all_tasks

    def _w(s: str) -> int:  # CJK 按 2 列宽近似
        return sum(2 if ord(c) > 0x2E80 else 1 for c in s)

    rows = [(t.id, t.name, t.category, t.risk_level) for t in all_tasks()]
    widths = [max(_w(r[i]) for r in rows) for i in range(4)]
    for r in rows:
        line = "  ".join(r[i] + " " * (widths[i] - _w(r[i])) for i in range(4))
        typer.echo(line)
    typer.echo(f"\n共 {len(rows)} 个任务。")


@app.command("restore")
def restore() -> None:
    """还原被 MaaFw 伪最小化的游戏窗口（窗口「打不开」时用）。"""
    from ak_auto import device
    from ak_auto.config import AppConfig

    device.init_maa()
    cfg = AppConfig.load()
    win = device.find_game_window(cfg)
    if not win:
        typer.echo("没找到游戏窗口（进程没在跑？）")
        raise typer.Exit(1)
    ok = device.restore_window(win["hwnd"])
    typer.echo(f"{'已还原' if ok else '尝试还原失败'}：hwnd={win['hwnd']}")


@app.command("lint")
def lint() -> None:
    """流水线静态校验。"""
    from ak_auto.config import PROJECT_ROOT

    script = PROJECT_ROOT / "tools" / "pipeline_lint.py"
    raise typer.Exit(subprocess.run([sys.executable, str(script)]).returncode)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
