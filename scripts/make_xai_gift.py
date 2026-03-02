from __future__ import annotations

"""Build a distributable xAI gift package zip from tracked project artifacts."""

import os
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def _collect_existing(root: Path, relative_paths: list[str]) -> list[Path]:
    """Return existing files only, preserving declared order for deterministic packaging."""
    files: list[Path] = []
    for rel in relative_paths:
        candidate = root / rel
        if candidate.exists() and candidate.is_file():
            files.append(candidate)
    return files


def _collect_docs(root: Path) -> list[Path]:
    """Collect top-level docs files and preserve stable lexical order."""
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return []
    return sorted(path for path in docs_dir.glob("*") if path.is_file())


def _run_doberman_scan(root: Path) -> None:
    """Run Doberman secret/vendor scan before package generation."""
    cmd = [sys.executable, str(root / "src" / "po_echo" / "sentinel_v2.py"), str(root)]
    env = dict(os.environ)
    try:
        subprocess.run(cmd, cwd=root, env=env, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Doberman scan failed. Gift packaging blocked.") from exc


def build_xai_gift_zip() -> Path:
    """Create a timestamped xAI gift package zip and return the archive path."""
    root = Path(__file__).resolve().parents[1]
    _run_doberman_scan(root)

    dist_dir = root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    zip_path = dist_dir / f"xai-gift-package-{timestamp}.zip"

    explicit_files = _collect_existing(
        root,
        [
            "CHANGELOG.md",
            "PROGRESS.md",
            "README.md",
            ".github/workflows/benchmark.yml",
            "scripts/make_xai_gift.py",
            "docs/demo_c_example.py",
            "docs/BENCHMARK_RESULTS.md",
        ],
    )
    doc_files = _collect_docs(root)

    seen: set[Path] = set()
    files_to_package: list[Path] = []
    for path in explicit_files + doc_files:
        if path not in seen:
            files_to_package.append(path)
            seen.add(path)

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files_to_package:
            zf.write(path, arcname=path.relative_to(root).as_posix())

    print(f"Created: {zip_path}")
    print(f"Included files: {len(files_to_package)}")
    for path in files_to_package:
        print(f"- {path.relative_to(root).as_posix()}")

    return zip_path


if __name__ == "__main__":
    build_xai_gift_zip()
