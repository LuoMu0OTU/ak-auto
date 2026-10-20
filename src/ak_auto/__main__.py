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
    # 打包版首启：把只读资源（流水线/数据表/配置模板）复制到数据目录
    from ak_auto import paths

    paths.ensure_data_layout()


@app.command("doctor")
def doctor() -> None:
    """环境 / 资源 / 窗口 / 截图自检。"""
    from ak_auto.application.diagnostics import run_checks

    checks = run_checks(_load_config())

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
    from ak_auto.config import PROJECT_ROOT

    device.init_maa()
    cfg = _load_config()

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
    """组装 MAA 识别资源（进程内执行 ak_auto.assets_fetch）。"""
    from ak_auto.assets_fetch import fetch
    from ak_auto.config import PROJECT_ROOT

    fetch(PROJECT_ROOT, tag=tag)
    raise typer.Exit(0)


def _load_config(path: str = ""):
    """经 ConfigurationService 读配置（损坏恢复 + 迁移），有警告则提示。"""
    from ak_auto.application import ConfigurationService

    svc = ConfigurationService(path or None)
    cfg = svc.load()
    if svc.warning:
        typer.echo(f"[warn] {svc.warning}")
    return cfg


def _event_console_logger(echo):
    """把事件总线接到控制台输出（TaskProgress 由 on_progress 负责，此处跳过）。"""
    from ak_auto.domain import EventType, TaskEvent

    def _on(e: TaskEvent) -> None:
        if e.type is EventType.TASK_PROGRESS:
            return
        if e.type is EventType.TASK_STARTED:
            text = f"[event] ▶ 开始 {e.task_id}（{e.run_id}）"
        elif e.type is EventType.TASK_COMPLETED:
            text = f"[event] ✔ 完成 {e.task_id}（{e.run_id}）"
        elif e.type is EventType.TASK_FAILED:
            text = f"[event] ✘ 失败 {e.task_id}（{e.message}）"
        else:
            text = f"[event] {e.type.value} {e.task_id} {e.message}".rstrip()
        echo(text)

    return _on


@app.command("run")
def run(
    task: str = typer.Argument(..., help="任务名，如 StartUp / ReturnToHome / Fight / Infrast"),
    config: str = typer.Option("", "--config", help="config.json 路径"),
) -> None:
    """连接游戏并运行指定任务。"""
    from ak_auto import device
    from ak_auto.domain import EventBus, ExecutionResult, ExecutionState, resolve_task

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
    cfg = _load_config(config)
    from ak_auto.infrastructure import GameWindowAdapter, MaaFrameworkAdapter, WindowNotFound

    win_adapter = GameWindowAdapter(cfg)
    try:
        _hwnd, ctrl = win_adapter.acquire(on_log=typer.echo)
    except WindowNotFound as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)

    try:
        tasker = MaaFrameworkAdapter(cfg).build_tasker(ctrl)
        bus = EventBus()
        bus.subscribe_all(_event_console_logger(typer.echo))
        from ak_auto.application import ExecutionController

        controller = ExecutionController(tasker, bus=bus)
        controller.start([entry], retry_per_task=0)
        try:
            results = controller.wait()
        except KeyboardInterrupt:
            typer.echo("\n[stop] 收到 Ctrl+C，正在安全停止 ...")
            controller.cancel()
            results = controller.wait(timeout=10.0)
        result = (
            results[0]
            if results
            else ExecutionResult(run_id="", task_id=entry, state=ExecutionState.FAILED, error="no-result")
        )
        typer.echo(result.summary)
        for n in result.nodes:
            typer.echo(f"  - {n}")
        code = 0 if result.ok else 1
    finally:
        # MaaFw 会把游戏窗口伪最小化，结束前务必还原
        win_adapter.release(restore=True)
    raise typer.Exit(code)


@app.command("daily")
def daily(config: str = typer.Option("", "--config", help="config.json 路径")) -> None:
    """日常全家桶。"""
    from ak_auto import device
    from ak_auto.domain import EventBus, resolve_task
    from ak_auto.report import make_report

    device.init_maa()
    cfg = _load_config(config)

    # 校验 task_order：不在任务目录里的项给出警告（是否真的执行由流水线节点是否存在决定）
    for t in cfg.runtime.task_order:
        if resolve_task(t) is None:
            typer.echo(f"[warn] runtime.task_order 里的 {t!r} 不在任务目录中，可能是无效任务")

    from ak_auto.infrastructure import GameWindowAdapter, MaaFrameworkAdapter, WindowNotFound

    win_adapter = GameWindowAdapter(cfg)
    try:
        _hwnd, ctrl = win_adapter.acquire(on_log=typer.echo)
    except WindowNotFound as exc:
        typer.echo(str(exc))
        raise typer.Exit(1)

    try:
        tasker = MaaFrameworkAdapter(cfg).build_tasker(ctrl)
        bus = EventBus()
        bus.subscribe_all(_event_console_logger(typer.echo))
        from ak_auto.application import ExecutionController

        # 每个任务前先回主界面，保证任务之间不串场
        entries: list[str] = []
        for t in cfg.runtime.task_order:
            if t != "StartUp":
                entries.append("ReturnToHome")
            entries.append(t)

        controller = ExecutionController(tasker, bus=bus)
        controller.start(entries, retry_per_task=cfg.runtime.retry_per_task, on_progress=typer.echo)
        try:
            results = controller.wait()
        except KeyboardInterrupt:
            typer.echo("\n[stop] 收到 Ctrl+C，正在安全停止 ...")
            controller.cancel()
            results = controller.wait(timeout=10.0)
        report = make_report(results)
        typer.echo("\n" + report.render())
        typer.echo(f"报告已保存：{report.save()}")
        code = 0 if report.all_ok else 1
    finally:
        win_adapter.release(restore=True)
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


@app.command("check-update")
def check_update() -> None:
    """检查 GitHub Releases 是否有新版本（只提示，不自动安装）。"""
    from ak_auto import __version__
    from ak_auto.application.updates import check_latest

    info = check_latest(__version__)
    if info is None:
        typer.echo(f"检查失败（网络不可达？）。当前版本 {__version__}")
        raise typer.Exit(1)
    if info.is_newer:
        typer.echo(f"发现新版本 {info.latest}（当前 {__version__}）")
        typer.echo(f"下载：{info.url}")
    else:
        typer.echo(f"已是最新版本 {__version__}")
    raise typer.Exit(0)


@app.command("export-diagnostics")
def export_diagnostics(out: str = typer.Option("", "--out", help="输出目录（默认 logs/）")) -> None:
    """打包诊断包（日志 + 脱敏配置 + 失败截图）为 zip。"""
    from ak_auto.application.diagnostics_export import export_diagnostics
    from ak_auto.config import PROJECT_ROOT

    p = export_diagnostics(PROJECT_ROOT, out_dir=out or None)
    typer.echo(f"诊断包已生成：{p}")
    raise typer.Exit(0)


@app.command("profile")
def profile(
    save: str = typer.Option("", "--save", help="把当前配置保存为命名方案"),
    load: str = typer.Option("", "--load", help="载入命名方案"),
    delete: str = typer.Option("", "--delete", help="删除命名方案"),
    list_only: bool = typer.Option(False, "--list", help="列出所有方案"),
) -> None:
    """多配置方案管理（config/profiles/*.json）。"""
    from ak_auto.application import ConfigurationService, profiles as P

    svc = ConfigurationService()
    cfg = svc.load()
    actions = [a for a, _ in (("save", save), ("load", load), ("delete", delete)) if _]
    if len(actions) > 1 or (not actions and not list_only):
        typer.echo("请指定 --save/--load/--delete 之一，或 --list。")
        raise typer.Exit(2)

    if save:
        P.save_profile(cfg, save)
        typer.echo(f"已保存方案「{save}」")
    elif load:
        P.apply_profile(cfg, load)
        svc.save(cfg)
        typer.echo(f"已载入方案「{load}」（已写入 config.json）")
    elif delete:
        ok = P.delete_profile(delete)
        typer.echo(f"{'已删除' if ok else '方案不存在'}：{delete}")
    else:
        names = P.list_profiles()
        typer.echo("配置方案：" + (", ".join(names) if names else "（无）"))
    raise typer.Exit(0)


@app.command("gui")
def gui() -> None:
    """启动图形界面（深色主题，简单模式）。"""
    from ak_auto.gui import run_gui

    raise typer.Exit(run_gui())


@app.command("restore")
def restore() -> None:
    """还原被 MaaFw 伪最小化的游戏窗口（窗口「打不开」时用）。"""
    from ak_auto import device

    device.init_maa()
    cfg = _load_config()
    win = device.find_game_window(cfg)
    if not win:
        typer.echo("没找到游戏窗口（进程没在跑？）")
        raise typer.Exit(1)
    ok = device.restore_window(win["hwnd"])
    typer.echo(f"{'已还原' if ok else '尝试还原失败'}：hwnd={win['hwnd']}")


@app.command("lint")
def lint() -> None:
    """流水线静态校验（进程内执行 tools/pipeline_lint 的逻辑）。"""
    import importlib.util
    from pathlib import Path

    from ak_auto.config import PROJECT_ROOT

    script = PROJECT_ROOT / "tools" / "pipeline_lint.py"
    spec = importlib.util.spec_from_file_location("pipeline_lint", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raise typer.Exit(mod.main())


def main() -> None:
    app()


if __name__ == "__main__":
    main()
