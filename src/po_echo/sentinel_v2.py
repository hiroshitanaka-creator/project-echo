import ast
import os
import sys
import re
from collections import defaultdict
from pathlib import Path

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


class Doberman(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.violations = []
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self._check_vendor(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self._check_vendor(node.module, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node):
        # 文字列定数の中にAPIキーが生書きされていないかチェック
        if isinstance(node.value, str):
            for pattern, name in HARDCODED_SECRETS:
                if re.search(pattern, node.value):
                    self.violations.append(
                        f"💀 Line {node.lineno}: Hardcoded {name} detected. You are leaking the keys to your cage."
                    )
        self.generic_visit(node)

    def _check_vendor(self, module_name, lineno):
        # サブモジュール (google.cloud.storage) も検知するために前方一致
        for risk_mod, vendor in VENDOR_RISK_MAP.items():
            if module_name == risk_mod or module_name.startswith(risk_mod + "."):
                self.violations.append(
                    f"⛓️ Line {lineno}: Import '{module_name}' -> Dependency on {vendor}."
                )


def scan_directory(target_dir):
    print(f"🐕 Releasing the Doberman in: {target_dir}\n")

    total_files = 0
    total_violations = 0
    file_violation_map = defaultdict(list)

    for root, _, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py") and "venv" not in root:
                full_path = Path(root) / file
                total_files += 1

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
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


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    scan_directory(target)
