#!/usr/bin/env python3
"""组装 MAA 识别资源（模板图 / OCR 模型 / 数据表）。

- 复用对象：MaaAssistantArknights（AGPL-3.0）发版 tag 内的 resource/ 目录
- 仅做「复制 / 筛选 / 重命名」，不修改文件内容
- 幂等：已生成且哈希一致则跳过；--force 强制重拉
- 输出：assets/MANIFEST.json（来源+哈希清单）与 assets/resource/image/source-map.json（模板→上游路径）

用法：
    python tools/fetch_maa_assets.py [--tag v6.19.0] [--force] [--verify]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_REPO = "MaaAssistantArknights/MaaAssistantArknights"
REPO_URL = f"https://github.com/{SRC_REPO}.git"
DEFAULT_TAG = "v6.19.0"
UA = {"User-Agent": "ak-auto/0.1 (local asset fetcher)"}

# 直接复制的数据表（目标放在 assets/maa-vendor/）
DATA_FILES = [
    "stages.json",
    "recruitment.json",
    "infrast.json",
    "item_index.json",
    "battle_data.json",
    "config.json",
    "version.json",
    "ocr_config.json",
]
DATA_DIRS = ["Arknights-Tile-Pos"]

# OCR 模型：仅重命名（MAA 的 PaddleOCR 目录 → MaaFw 的 model/ocr 目录）
# 键相对 resource/ 目录（脚本内会用 resource / 键 拼接）
OCR_MAP = {
    "PaddleOCR/det/inference.onnx": "assets/resource/model/ocr/det.onnx",
    "PaddleOCR/rec/inference.onnx": "assets/resource/model/ocr/rec.onnx",
    "PaddleOCR/rec/keys.txt": "assets/resource/model/ocr/keys.txt",
}

# 目标目录
IMAGE_DIR = ROOT / "assets" / "resource" / "image"
OCR_DIR = ROOT / "assets" / "resource" / "model" / "ocr"
VENDOR_DIR = ROOT / "assets" / "maa-vendor"
MANIFEST_PATH = ROOT / "assets" / "MANIFEST.json"
SOURCE_MAP_PATH = IMAGE_DIR / "source-map.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def fetch_via_codeload(tag: str, tmp: Path) -> tuple[Path, str]:
    """从 codeload 下载 tag 的 tar.gz，解出 resource/（沙箱内 github.com 直连不可达时的首选）。"""
    tarball = tmp / f"{tag}.tar.gz"
    url = f"https://codeload.github.com/{SRC_REPO}/tar.gz/{tag}"
    print(f"[fetch] 下载 {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r, tarball.open("wb") as f:
        shutil.copyfileobj(r, f)
    out = tmp / "tar-root"
    out.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2:
                continue
            rel = parts[1]  # 去掉顶层目录（MaaAssistantArknights-<tag>/）
            if not (rel == "resource" or rel.startswith("resource/")):
                continue
            if m.isfile():
                dest = out / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                with tf.extractfile(m) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
            elif m.isdir():
                (out / rel).mkdir(parents=True, exist_ok=True)
    resource = out / "resource"
    if not resource.is_dir():
        raise RuntimeError("解包完成但未找到 resource/ 目录")
    return resource, tag


def fetch_via_git(tag: str, tmp: Path) -> tuple[Path, str]:
    """稀疏克隆 resource/ 目录（可复现、带 commit）。"""
    repo = tmp / "maa-repo"
    repo.mkdir(parents=True, exist_ok=True)
    p = run(
        ["git", "-c", "advice.detachedHead=false", "clone", "--depth", "1",
         "--branch", tag, "--filter=blob:none", "--sparse", REPO_URL, str(repo)]
    )
    if p.returncode != 0:
        raise RuntimeError(f"git clone 失败: {p.stderr.strip()[:500]}")
    p = run(["git", "-C", str(repo), "sparse-checkout", "set", "resource"])
    if p.returncode != 0:
        raise RuntimeError(f"sparse-checkout 失败: {p.stderr.strip()[:500]}")
    p = run(["git", "-C", str(repo), "rev-parse", "HEAD"])
    commit = p.stdout.strip()
    resource = repo / "resource"
    if not resource.is_dir():
        raise RuntimeError("克隆成功但未找到 resource/ 目录")
    return resource, commit


def fetch_via_zip(tag: str, tmp: Path) -> tuple[Path, str]:
    """从 release 包下载并解出 resource/。"""
    asset = f"MAA-{tag}-win-x64.zip"
    url = f"https://github.com/{SRC_REPO}/releases/download/{tag}/{asset}"
    zip_path = tmp / asset
    print(f"[fetch] 下载 {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, zip_path.open("wb") as f:
        shutil.copyfileobj(r, f)
    out = tmp / "zip-root"
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        for m in z.infolist():
            name = m.filename.replace("\\", "/").lstrip("/")
            if name.startswith("resource/") and not name.endswith("/"):
                dest = out / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(m) as src, dest.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
    resource = out / "resource"
    if not resource.is_dir():
        raise RuntimeError("解包完成但未找到 resource/ 目录")
    return resource, f"{tag} (zip 回退，未解析 commit)"


def resolve_commit(tag: str) -> str:
    """尽力从 GitHub API 解析 tag 对应 commit（codeload/zip 方式时用于溯源）。"""
    base = f"https://api.github.com/repos/{SRC_REPO}/git/ref/tags/{tag}"
    try:
        req = urllib.request.Request(base, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            obj = json.load(r)["object"]
        if obj.get("type") == "commit":
            return obj["sha"]
        # 带注释的 tag：再解一层
        req = urllib.request.Request(obj["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["object"]["sha"]
    except Exception:
        try:
            p = run(["git", "ls-remote", REPO_URL, f"refs/tags/{tag}"])
            if p.returncode == 0 and p.stdout.strip():
                return p.stdout.split()[0]
        except Exception:
            pass
        return tag


def build_manifest(resource: Path, commit: str, tag: str) -> dict:
    entries: list[dict] = []

    def add(src: Path, dst_rel: str) -> None:
        dst = ROOT / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        entries.append({"src": src.relative_to(resource).as_posix(), "dst": dst_rel, "sha256": sha256(src)})

    # 1) 模板图
    image_src_map: dict[str, str] = {}
    template_dir = resource / "template"
    if template_dir.is_dir():
        for f in sorted(template_dir.rglob("*")):
            if f.is_file():
                rel = f.relative_to(template_dir).as_posix()
                dst_rel = f"assets/resource/image/{rel}"
                add(f, dst_rel)
                image_src_map[rel] = f"resource/template/{rel}"

    # 2) OCR 模型（重命名）
    for src_rel, dst_rel in OCR_MAP.items():
        src = resource / src_rel
        if not src.is_file():
            raise FileNotFoundError(f"缺少 OCR 模型: {src_rel}")
        add(src, dst_rel)

    # 3) 数据表
    for name in DATA_FILES:
        src = resource / name
        if src.is_file():
            add(src, f"assets/maa-vendor/{name}")
        else:
            print(f"[warn] 数据表缺失，跳过: {name}")
    for name in DATA_DIRS:
        src = resource / name
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if f.is_file():
                    rel = f.relative_to(resource).as_posix()
                    add(f, f"assets/maa-vendor/{rel}")

    # 4) source-map.json
    SOURCE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_MAP_PATH.write_text(
        json.dumps({"source": f"{SRC_REPO}@{tag}", "images": image_src_map}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": 1,
        "source": {"repo": SRC_REPO, "tag": tag, "commit": commit, "license": "AGPL-3.0"},
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "file_count": len(entries),
        "entries": entries,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def manifest_ok() -> bool:
    """已生成且磁盘与 manifest 一致则视为完成（幂等）。"""
    if not MANIFEST_PATH.exists():
        return False
    try:
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return False
    for e in m.get("entries", []):
        p = ROOT / e["dst"]
        if not p.is_file() or sha256(p) != e.get("sha256"):
            return False
    return True


def verify() -> bool:
    if not MANIFEST_PATH.exists():
        print("无 MANIFEST.json（先运行 --tag 生成）")
        return False
    m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    bad = 0
    for e in m.get("entries", []):
        p = ROOT / e["dst"]
        if not p.is_file():
            print(f"缺失: {e['dst']}")
            bad += 1
        elif sha256(p) != e.get("sha256"):
            print(f"哈希不一致: {e['dst']}")
            bad += 1
    print(f"校验完成：{m.get('file_count')} 项，{bad} 项异常")
    return bad == 0


def main() -> int:
    ap = argparse.ArgumentParser(description="组装 MAA 识别资源")
    ap.add_argument("--tag", default=DEFAULT_TAG, help="MAA 发版 tag")
    ap.add_argument("--force", action="store_true", help="忽略已有结果，强制重拉")
    ap.add_argument("--verify", action="store_true", help="仅校验现有资源")
    args = ap.parse_args()

    if args.verify:
        return 0 if verify() else 1

    if not args.force and manifest_ok():
        m = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        print(f"[skip] 资源已就绪（{m['source']['tag']}，{m['file_count']} 文件，哈希一致）。--force 可重拉。")
        return 0

    with tempfile.TemporaryDirectory(prefix="maa-assets-") as td:
        tmp = Path(td)
        resource: Path
        commit: str
        method = ""
        errors: list[str] = []
        for name, fn in (
            ("codeload tar.gz", fetch_via_codeload),
            ("git sparse clone", fetch_via_git),
            ("release zip", fetch_via_zip),
        ):
            try:
                resource, commit = fn(args.tag, tmp)
                method = name
                break
            except Exception as e:
                errors.append(f"{name}: {e}")
        else:
            raise RuntimeError("所有获取方式均失败：\n" + "\n".join(errors))

        if method != "git sparse clone":
            commit = resolve_commit(args.tag)

        manifest = build_manifest(resource, commit, args.tag)

    print(f"[ok] 完成（方式={method}）：{manifest['file_count']} 文件，来自 {SRC_REPO}@{args.tag} ({commit[:12] if len(commit) > 12 else commit})")
    print(f"[ok] MANIFEST -> {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"[ok] source-map -> {SOURCE_MAP_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
