# src/po_echo/sentinel.py
import sys
from collections import Counter
from pathlib import Path
from .vendor_db import VENDOR_MAP, DEFAULT_THRESHOLD


class CodeSentinel:
    def __init__(self, threshold=DEFAULT_THRESHOLD):
        self.threshold = threshold

    def audit_requirements(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}

        dependencies = []
        with open(path, "r") as f:
            # 簡易パーサー: コメント削除、バージョン指定削除 ('=='等)
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 'package==1.0.0' -> 'package'
                pkg_name = line.split("==")[0].split(">=")[0].split("<")[0].strip().lower()
                dependencies.append(pkg_name)

        total_deps = len(dependencies)
        if total_deps == 0:
            return {"status": "SAFE", "message": "No dependencies found"}

        vendor_counts = Counter()
        details = []

        for dep in dependencies:
            vendor = VENDOR_MAP.get(dep)
            if vendor:
                vendor_counts[vendor] += 1
                details.append(f"{dep} -> {vendor}")
            else:
                details.append(f"{dep} -> (OSS/Unknown)")

        # 支配率の計算
        most_common = vendor_counts.most_common(1)
        if not most_common:
            max_vendor, max_count = "None", 0
        else:
            max_vendor, max_count = most_common[0]

        concentration_score = max_count / total_deps

        # 判定
        is_locked_in = concentration_score > self.threshold

        result = {
            "status": "BLOCKED" if is_locked_in else "PASSED",
            "score": round(concentration_score, 2),
            "dominant_vendor": max_vendor,
            "total_dependencies": total_deps,
            "vendor_breakdown": dict(vendor_counts),
            "details": details
        }
        return result


def run_audit(target_file):
    sentinel = CodeSentinel()
    result = sentinel.audit_requirements(target_file)

    print(f"🔍 Audit Target: {target_file}")
    print(f"📊 Vendor Concentration: {result['score'] * 100}% ({result['dominant_vendor']})")

    if result['status'] == "BLOCKED":
        print(f"🚫 [BLOCKED] Threshold ({DEFAULT_THRESHOLD*100}%) exceeded!")
        print(f"⚠️  WARNING: High dependency on {result['dominant_vendor']}.")
        print(f"   Consider replacing proprietary libs with open alternatives.")
        sys.exit(1)  # CIを落とす
    else:
        print(f"✅ [PASSED] Diversity check OK.")
        sys.exit(0)
