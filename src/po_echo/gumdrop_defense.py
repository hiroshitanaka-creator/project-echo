# src/po_echo/gumdrop_defense.py
"""
Gumdrop（画面無しデバイス）向けEcho Mark強化
OpenAI World Register戦略（状態保持チップ＋「失敗しなかった意図」課金）への直接カウンター
"""

from .echo_mark import generate_echo_mark
from .voice_boundary import get_voice_boundary_policy
from .rth import compute_rth

def apply_gumdrop_defense(recommendation: dict, context: dict) -> dict:
    """
    画面無しデバイス用処理フロー
    1. 商業バイアスを音声用に簡略監査
    2. Diversity Noiseを音声候補に変換
    3. Execution Gate適用
    4. Echo Mark発行（音声読み上げ用テキスト付き）
    """
    # 1. 簡略バイアス監査（画面なしでも可能な軽量版）
    bias_score = _light_commercial_bias_audit(recommendation)
    
    # 2. 音声用多様性ノイズ（2〜3候補に圧縮）
    diversified = _voice_diversity_noise(recommendation, bias_score)
    
    # 3. 音声境界ポリシー適用
    policy = get_voice_boundary_policy(bias_score, context.get("device_type") == "gumdrop")
    
    # 4. Echo Mark生成（音声読み上げテキスト付き）
    mark = generate_echo_mark(
        payload=diversified,
        device="gumdrop",
        extra_text=f"Echo Verified. 失敗リスク {bias_score*100:.1f}%。責任境界はここまで。"
    )
    
    return {
        "candidates": diversified["candidates"],
        "policy": policy,
        "echo_mark": mark,
        "rth": compute_rth(context.get("transcript", ""))  # プライバシー保護
    }

def _light_commercial_bias_audit(rec: dict) -> float:
    # 簡易版（将来的に拡張）
    return 0.0 if not rec.get("affiliate") else 0.8

def _voice_diversity_noise(rec: dict, bias: float) -> dict:
    # 音声で読みやすい2〜3候補に制限
    return {"candidates": rec.get("alternatives", [rec])[:3]}
