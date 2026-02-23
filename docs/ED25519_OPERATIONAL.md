# Ed25519鍵運用手順（3コマンド完了）

本書は、鍵運用を**責任境界・検証可能・透明性・再構築可能**の4条件で固定するための手順書。

- 返却形式は常に「候補セット＋証拠＋責任境界」
- 商業バイアス排除はシステムで強制
- Echo Markは `Ed25519 + HMAC` dual signature を基準
- テスト失敗は停止条件（即修正）

---

## 0. 責任境界

### Issuer（署名発行側）
- Ed25519秘密鍵とHMAC秘密鍵を保護
- `registry.json` の `status` (`active/inactive/revoked`) を更新
- ローテーション時の新旧鍵状態を記録

### Verifier（検証側）
- バッジ単体を信頼しない
- `key_id` と `registry.json` の公開鍵整合を検証
- 署名検証を独立実行（Ed25519優先、必要時HMAC）

### 本手順の境界外
- 組織内承認フロー
- 法務連携
- 長期保管ポリシー

---

## 1. 前提

- Python
- `pynacl`
- リポジトリ直下で実行

---

## 2. 3コマンド（生成→登録→検証）

### 1) 鍵生成（Ed25519 + HMAC dual）

```bash
# Project Echo 不変原則：Echo MarkはEd25519 + HMAC dual signatureを基準にし、責任境界を固定する
python tools/generate_keypair.py --key-id 2026q1 --output .keys --with-hmac
```

### 2) registry.json 登録

```bash
# Project Echo 不変原則：透明性をシステムで担保し、公開鍵レジストリで検証可能性を維持する
python tools/generate_keypair.py --key-id 2026q1 --output .keys --with-hmac --registry --overwrite
```

### 3) 整合検証（key_id / public_key）

```bash
# Project Echo 不変原則：AIは推奨せず、証拠と責任境界を機械検証で返す
PYTHONPATH=src python -c "from po_echo.echo_mark import verify_key_in_registry; from pathlib import Path; key_id='2026q1'; pub=Path('.keys/2026q1.public.key').read_text().strip(); ok, reason = verify_key_in_registry(key_id, pub, '.keys/registry.json'); print({'ok': ok, 'reason': reason, 'key_id': key_id})"
```

期待値:
- `{'ok': True, 'reason': 'key_verified', 'key_id': '2026q1'}`

---

## 3. 失効・ローテーション

### 失効

```bash
# Project Echo 不変原則：失効は即時にregistryへ反映し、検証者へ責任境界を開示する
python tools/generate_keypair.py --key-id 2026q1 --output .keys --registry --status revoked --overwrite
```

### ローテーション

```bash
# Project Echo 不変原則：選択肢を残すため新旧鍵の並行期間を定義し、段階移行を機械的に管理する
python tools/generate_keypair.py --key-id 2026q2 --output .keys --with-hmac --registry
```

運用:
- 新鍵 `active`
- 旧鍵 `inactive`（検証互換期間）
- 廃止時 `revoked`

---

## 4. 静的検証（mypy strict寄り）

```bash
# Project Echo 不変原則：テストが落ちたら即修正必須
mypy src tools --ignore-missing-imports --no-implicit-optional --warn-unused-ignores --warn-return-any --strict-equality
# TODO: 将来 --strict に移行予定（P0完了後）
```

---

## 5. テスト実行境界

```bash
# Project Echo 不変原則：テストが落ちたら即修正必須
pytest -q
```

```bash
# Project Echo 不変原則：テストが落ちたら即修正必須
ruff check . --output-format=github
```

---

## 6. 監査チェック

- `key_id` 一意性
- `registry.json` 反映
- `status` と実運用の一致
- 失効/ローテーション履歴の再構築可能性
- 第三者が同手順で検証可能

本手順は推奨文言を排し、責任境界と証拠を固定する運用仕様である。
