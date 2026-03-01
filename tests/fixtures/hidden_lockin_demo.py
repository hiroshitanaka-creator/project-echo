# hidden_lockin_demo.py
"""
Demo-only lock-in anti-pattern fixture used by Doberman scanner tests.
このキーはデモ用ダミーであり、実運用秘密鍵ではありません。
"""

import json

# こっそりインポート（エイリアスで隠したつもり）
import openai as my_ai_brain


def think() -> None:
    # デモ用ダミー: Dobermanが意図的fixtureと判定するための偽キー
    key = "sk-dummy-1234567890-demo-only-not-a-real-secret"
    print("I am thinking...", json.dumps({"key": key, "model": "demo"}))
