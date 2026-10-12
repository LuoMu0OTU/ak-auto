#!/usr/bin/env python3
"""流水线静态校验。

检查项：
- JSON 可解析、顶层为对象
- 节点名全局唯一
- `template` 引用的图片存在（assets/resource/image/ 下）
- `next` / `on_error` / `interrupt` 引用的节点存在（以 # 或 [ 开头视为特殊 token，跳过）

用法：
    python tools/pipeline_lint.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = ROOT / "assets" / "resource" / "pipeline"
IMAGE_DIR = ROOT / "assets" / "resource" / "image"

SPECIAL = ("#self", "#next", "#back")


def _is_special(ref: str) -> bool:
    return ref.startswith(("#", "["))


def lint_pipelines(pipeline_dir: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    pdir = pipeline_dir or PIPELINE_DIR
    if not pdir.is_dir():
        return [f"pipeline 目录不存在: {pdir}"], []

    all_nodes: dict[str, list[str]] = {}  # name -> [file, ...]
    nodes_by_file: dict[str, dict[str, dict]] = {}

    # 第一遍：加载 + 收集节点
    for f in sorted(pdir.rglob("*.json")):
        rel = str(f.relative_to(pdir))
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            errors.append(f"{rel}: JSON 解析失败: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: 顶层应为 JSON 对象")
            continue
        nodes_by_file[rel] = data
        for name, node in data.items():
            all_nodes.setdefault(name, []).append(rel)
            if not isinstance(node, dict):
                errors.append(f"{rel}#{name}: 节点应为对象")

    # 第二遍：检查重复、template、next/on_error/interrupt 引用
    for name, files in all_nodes.items():
        if len(files) > 1:
            errors.append(f"节点名重复: {name} 出现在 {files}")

    def _check_templates(node: dict, rel: str, name: str) -> None:
        """收集并校验 template（含 Or/And 嵌套 any_of/all_of 里的 template）。"""
        tpl = node.get("template")
        for t in (tpl if isinstance(tpl, list) else [tpl]):
            if isinstance(t, str) and not (IMAGE_DIR / t).is_file():
                errors.append(f"{rel}#{name}: template 缺失 {t}")
        for key in ("any_of", "all_of"):
            subs = node.get(key)
            if isinstance(subs, list):
                for s in subs:
                    if isinstance(s, dict):
                        _check_templates(s, rel, name)

    for rel, data in nodes_by_file.items():
        for name, node in data.items():
            if not isinstance(node, dict):
                continue
            _check_templates(node, rel, name)
            for key in ("next", "on_error", "interrupt"):
                refs = node.get(key)
                if isinstance(refs, str):
                    refs = [refs]
                if isinstance(refs, list):
                    for r in refs:
                        if isinstance(r, str) and not _is_special(r) and r not in all_nodes:
                            errors.append(f"{rel}#{name}: {key} 引用不存在的节点 {r!r}")

    if not all_nodes:
        warnings.append("pipeline 目录为空，未发现任何节点")
    return errors, warnings


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
    errors, warnings = lint_pipelines()
    for w in warnings:
        print(f"[warn] {w}")
    for e in errors:
        print(f"[FAIL] {e}")
    print(f"流水线校验：{len(errors)} 个错误，{len(warnings)} 个警告")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
