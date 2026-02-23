# Ed25519鍵運用手順（誰でも3コマンドで完了）

Project Echoの鍵運用は、**候補セット＋証拠＋責任境界**を維持するための運用手順として定義する。  
ここでは、Echo Markの**Ed25519 + HMAC dual signature**前提で、生成・登録・検証を機械的に実行する。

---

## 0. 目的と責任境界

- 本手順の目的は、署名の真正性と改ざん検知を運用で担保すること。
- 責任境界:
  - **運用担当者**: 秘密鍵/HMAC秘密の保管、失効、ローテーションを実行。
  - **検証担当者（第三者含む）**: `registry.json` と公開鍵で検証。
  - **システム**: 商業バイアスを道徳でなくルールとして排除し、署名検証可能性を維持。

---

## 1. 前提

- Python 3.11+
- 依存関係（PyNaCl）
- リポジトリルートで作業

```bash
# Project Echo 不変原則：候補セット＋証拠＋責任境界を運用で固定する
python -m pip install -e .[dev]
```

---

## 2. 鍵生成（Ed25519 + HMAC dual）

以下で、Ed25519秘密鍵/公開鍵と、dual signature用HMAC秘密を生成する。

```bash
# Project Echo 不変原則：Echo MarkはEd25519 + HMAC dual signatureを基本とする
python tools/generate_keypair.py --key-id 2026-01 --output .keys --hmac-secret
```

生成物（秘密と公開の責任境界を分離）:

- `.keys/2026-01.private.key`（秘密・chmod 600）
- `.keys/2026-01.public.key`（公開可）
- `.keys/2026-01.hmac.secret`（秘密・chmod 600）

---

## 3. `registry.json` への登録

`registry.json` は公開検証の証拠台帳。`key_id` と `public_key` を機械的に登録する。

```bash
# Project Echo 不変原則：透明性を優先し、公開鍵台帳を監査可能にする
python tools/generate_keypair.py --key-id 2026-01 --output .keys --registry --force
```

> `--force` は同一`key_id`の再登録時に旧エントリを置換する。事故防止のため、運用記録（チケット/監査ログ）とセットで実行する。

---

## 4. 検証コマンド（登録整合性）

`registry.json` の公開鍵とローカル公開鍵が一致するかを検証する。

```bash
# Project Echo 不変原則：検証可能性を優先し、秘密を渡さず一致検証する
PYTHONPATH=src python -c "from po_echo.echo_mark import verify_key_in_registry; from pathlib import Path; pub=Path('.keys/2026-01.public.key').read_text().strip(); ok,reason=verify_key_in_registry('2026-01', pub, '.keys/registry.json'); print({'verified':ok,'reason':reason}); raise SystemExit(0 if ok else 2)"
```

期待値:

- `{'verified': True, 'reason': 'key_verified'}`

---

## 5. 3コマンドで「生成→登録→検証」を完了する手順

以下をそのまま順に実行する。

```bash
# Project Echo 不変原則：dual署名前提で鍵素材を生成し、責任境界を分離する
python tools/generate_keypair.py --key-id 2026-01 --output .keys --hmac-secret

# Project Echo 不変原則：公開鍵台帳を機械的に更新し、透明性を確保する
python tools/generate_keypair.py --key-id 2026-01 --output .keys --registry --force

# Project Echo 不変原則：証拠を検証し、主観でなく可否を返す
PYTHONPATH=src python -c "from po_echo.echo_mark import verify_key_in_registry; from pathlib import Path; pub=Path('.keys/2026-01.public.key').read_text().strip(); ok,reason=verify_key_in_registry('2026-01', pub, '.keys/registry.json'); print({'verified':ok,'reason':reason}); raise SystemExit(0 if ok else 2)"
```

---

## 6. 失効・ローテーションの基本

### 6-1. 失効（revocation）

1. 対象`key_id`を特定。
2. `registry.json` の該当キーを `status: "revoked"` に変更。
3. 失効理由・時刻・実施者を監査ログに残す。
4. 検証系は `revoked` を拒否する。

```bash
# Project Echo 不変原則：失効は人の善意でなく台帳状態で強制する
python -c "import json; p='.keys/registry.json'; r=json.load(open(p)); [k.update({'status':'revoked'}) for k in r.get('keys',[]) if k.get('key_id')=='2026-01']; json.dump(r, open(p,'w'), indent=2, ensure_ascii=False); print('revoked: 2026-01')"
```

### 6-2. ローテーション

- 新しい`key_id`（例: `2026-02`）で新規生成。
- 新キーを`active`で登録。
- 旧キーは即時`revoked`または猶予付き`inactive`。
- 受領側は `key_id` ごとに公開鍵を選択して検証。

```bash
# Project Echo 不変原則：選択肢を残すため、新旧キーの共存期間を明示運用する
python tools/generate_keypair.py --key-id 2026-02 --output .keys --hmac-secret --registry
```

---

## 7. iPhoneユーザー向け運用メモ

iPhoneでも、次のどちらかで同じ3コマンドを実行可能。

- iSH / a-Shell などのローカルシェル
- GitHub Codespaces / SSH先Linux（Termius等）

責任境界の要点:

- `.private.key` と `.hmac.secret` は端末の共有領域に置かない。
- `registry.json` と `.public.key` のみ共有対象にする。
- 「生音声保存を避ける」「Rolling Transcript Hash前提」の音声ポリシーとは独立せず、監査証拠として一体運用する。

---

## 8. 透明性チェックリスト

- [ ] `key_id` が一意である
- [ ] 秘密ファイルが `chmod 600` である
- [ ] `registry.json` に `status` がある
- [ ] 登録検証コマンドが `verified=True` を返す
- [ ] 失効/ローテーションの監査ログが残っている

この手順は、AIの判断をブラックボックス化せず、常に検証可能な証拠を残すための運用基準である。
