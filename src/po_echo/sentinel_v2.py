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
import os
import re
import sys
from collections import defaultdict
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
    print(f"🐕 Releasing the Doberman in: {target_dir}\n")

    total_files = 0
    total_violations = 0
    file_violation_map = defaultdict(list)

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py") and "venv" not in root:
                full_path = Path(root) / file
                if "tests/fixtures" in full_path.as_posix():
                    continue
                total_files += 1

                try:
                    with open(full_path, encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=str(full_path))

                    dog = Doberman(str(full_path))
                    dog.visit(tree)

                    if dog.violations:
                        file_violation_map[str(full_path)] = dog.violations
                        total_violations += len(dog.violations)

                except Exception as e:
                    print(f"⚠️ Could not parse {file}: {e}")

    # レポート出力
    if total_violations > 0:
        print("🚨 BARK! BARK! Lock-in detected!\n")
        for fpath, errs in file_violation_map.items():
            print(f"📂 {fpath}")
            for err in errs:
                print(f"  {err}")
            print("")

        print(f"🔥 Total Violations: {total_violations}")
        print("❌ CI BLOCKED. Rewrite your code. Regain your will.")
        sys.exit(1)
    else:
        print(f"✅ Scanned {total_files} files. No vendor chains detected. You are free.")
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
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)
