"""AST-based vendor lock-in scanner and semantic diversity helper for source code.

Responsibility: two distinct concerns bundled in this module:

1. **Doberman (AST scanner)** — scan Python *source files* for:
   - `import` statements that pull in monitored vendor packages
   - Hardcoded API keys / credentials in string constants
   Call `scan_directory(path)` or run as `python -m po_echo.sentinel_v2 <dir>`.

2. **apply_semantic_diversity** — wraps `po_echo.diversity.apply_semantic_diversity`
   with a fixed prompt_text ("sentinel_semantic_scan") for use in sentinel
   audit pipelines that need semantic diversity enrichment alongside the
   vendor scan.

Use this module when you want to answer:
  "Does my *source code* import vendor-locked packages or leak credentials?"
  "What is the semantic diversity score for this candidate set in a sentinel context?"

Distinct from sentinel.py:
  - sentinel.py   → static analysis of *package dependency lists* (requirements.txt)
  - sentinel_v2.py → AST-based scan of *Python source code* + semantic diversity
"""
import ast
import fnmatch
import os
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from po_core.diversity import Rec

_apply_semantic_diversity = None

# 監視対象ベンダー定義 (地雷リスト)
VENDOR_RISK_MAP = {
    "openai": "OpenAI (Gumdrop)",
    "anthropic": "Anthropic",
    "boto3": "AWS (Infrastructure Lock-in)",
    "botocore": "AWS",
    "google.cloud": "Google Cloud",
    "firebase_admin": "Google Firebase",
    "azure": "Microsoft Azure",
    "vercel": "Vercel",
    # 💥 Google / Gemini Specific Traps
    "google.generativeai": "Google Gemini API (Vendor Lock-in)",
    "vertexai": "Google Vertex AI (Enterprise Lock-in)",
    "google_auth_oauthlib": "Google Auth (Identity Lock-in)",
}

# 💡 依存に対する「逃げ道」(代替手段)
ALTERNATIVE_MAP = {
    "openai": "litellm (Universal Proxy), ollama (Local LLM)",
    "anthropic": "litellm (Universal Proxy), langchain (Abstraction)",
    "boto3": "minio (S3-compatible OSS), localstack (Local AWS)",
    "google.cloud": "minio (Storage), self-hosted alternatives",
    "azure": "self-hosted alternatives, OSS equivalents",
    # 💡 Geminiへの依存に対する「逃げ道」
    "google.generativeai": "litellm (Universal Proxy), langchain (Abstraction)",
    "vertexai": "mlflow (Open MLOps), kubeflow (OSS MLOps)",
}

# 思考停止（ハードコードされた認証情報）のパターン
HARDCODED_SECRETS = [
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI API Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key"),
]


def _is_demo_dummy_secret(value: str) -> bool:
    """Allow explicitly-marked demo dummy keys to avoid false-positive lockouts."""
    lowered = value.lower()
    return "sk-dummy-" in lowered and ("demo" in lowered or "dummy" in lowered)


class Doberman(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []
        self.imports: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self._check_vendor(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self._check_vendor(node.module, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        # 文字列定数の中にAPIキーが生書きされていないかチェック
        if isinstance(node.value, str):
            for pattern, name in HARDCODED_SECRETS:
                if re.search(pattern, node.value):
                    if _is_demo_dummy_secret(node.value):
                        continue
                    self.violations.append(
                        f"💀 Line {node.lineno}: Hardcoded {name} detected. You are leaking the keys to your cage."
                    )
        self.generic_visit(node)

    def _check_vendor(self, module_name: str, lineno: int) -> None:
        # サブモジュール (google.cloud.storage) も検知するために前方一致
        for risk_mod, vendor in VENDOR_RISK_MAP.items():
            if module_name == risk_mod or module_name.startswith(risk_mod + "."):
                self.violations.append(
                    f"⛓️ Line {lineno}: Import '{module_name}' -> Dependency on {vendor}."
                )


def scan_directory(target_dir: str) -> None:
    scan_directory_optimized(target_dir)


def _matches_any_glob(path: Path, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path.as_posix(), pat) for pat in patterns)


def _iter_python_files(
    target_dir: str,
    *,
    exclude_globs: tuple[str, ...] = (),
    changed_files: set[str] | None = None,
) -> list[Path]:
    files_out: list[Path] = []
    for root, _, files in os.walk(target_dir):
        for file in files:
            if not file.endswith(".py") or "venv" in root:
                continue
            full_path = Path(root) / file
            rel = full_path.as_posix()
            if "tests/fixtures" in rel:
                continue
            if exclude_globs and _matches_any_glob(full_path, exclude_globs):
                continue
            if changed_files is not None and rel not in changed_files:
                continue
            files_out.append(full_path)
    return files_out


def _scan_python_file(path: Path) -> tuple[str, list[str], str | None]:
    try:
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(path))
        dog = Doberman(str(path))
        dog.visit(tree)
        return str(path), dog.violations, None
    except SyntaxError as e:
        return str(path), [], f"SyntaxError: {e}"
    except (OSError, UnicodeDecodeError, PermissionError) as e:
        return str(path), [], f"IOError: {e}"
    except Exception as e:
        return str(path), [], f"UnknownError: {e}"


def scan_directory_optimized(
    target_dir: str,
    *,
    exclude_globs: tuple[str, ...] = (),
    changed_files: set[str] | None = None,
    max_workers: int = 1,
) -> None:
    print(f"🐕 Releasing the Doberman in: {target_dir}\n")

    candidates = _iter_python_files(
        target_dir,
        exclude_globs=exclude_globs,
        changed_files=changed_files,
    )
    total_files = len(candidates)
    total_violations = 0
    unscannable_count = 0
    file_violation_map = defaultdict(list)

    if max_workers > 1 and len(candidates) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            records = list(ex.map(_scan_python_file, candidates))
    else:
        records = [_scan_python_file(path) for path in candidates]

    for path_str, violations, error in records:
        if error:
            unscannable_count += 1
            print(f"⚠️ {error} in {Path(path_str).name}")
            continue
        if violations:
            file_violation_map[path_str] = violations
            total_violations += len(violations)

    # レポート出力
    if total_violations > 0:
        print("🚨 BARK! BARK! Lock-in detected!\n")
        for fpath, errs in file_violation_map.items():
            print(f"📂 {fpath}")
            for err in errs:
                print(f"  {err}")
            print("")

        print(f"🔥 Total Violations: {total_violations}")
        print(f"⚠️ Unscannable files: {unscannable_count}")
        print("❌ CI BLOCKED. Rewrite your code. Regain your will.")
        sys.exit(1)
    else:
        print(f"✅ Scanned {total_files} files. No vendor chains detected. You are free.")
        if unscannable_count > 0:
            print(f"⚠️ Unscannable files: {unscannable_count}")
        sys.exit(0)


def apply_semantic_diversity(
    candidates: list[dict[str, Any] | Rec],
    *,
    counterfactuals: list[dict[str, Any] | Rec] | None = None,
    k: int = 5,
) -> dict[str, Any]:
    """Apply semantic diversity while preserving existing sentinel flow.

    Args:
        candidates: Candidate set from upstream audit pipeline.
        counterfactuals: Optional counterfactual set for diversification.
        k: Number of records to keep after MMR selection.

    Returns:
        Diversity audit payload from ``po_core.diversify_with_mmr``.

    Raises:
        ValueError: If ``k`` is smaller than 1.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    global _apply_semantic_diversity
    if _apply_semantic_diversity is None:
        from po_echo.diversity import apply_semantic_diversity as _apply_semantic_diversity_impl

        _apply_semantic_diversity = _apply_semantic_diversity_impl

    return _apply_semantic_diversity(
        candidates,
        counterfactuals=counterfactuals,
        prompt_text="sentinel_semantic_scan",
        k=k,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AST vendor-lock scanner with optional optimized mode.")
    parser.add_argument("target", nargs="?", default=".")
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Glob pattern(s) to exclude from scan. Can be repeated.",
    )
    parser.add_argument(
        "--changed-files",
        default=None,
        help="Optional newline-separated file list. When set, only listed files are scanned.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Parallel workers for file scan (default: 1).",
    )
    args = parser.parse_args()

    changed_set: set[str] | None = None
    if args.changed_files:
        changed_path = Path(args.changed_files)
        raw = changed_path.read_text(encoding="utf-8") if changed_path.exists() else ""
        changed_set = {line.strip() for line in raw.splitlines() if line.strip()}

    scan_directory_optimized(
        args.target,
        exclude_globs=tuple(args.exclude_glob),
        changed_files=changed_set,
        max_workers=max(1, args.max_workers),
    )
