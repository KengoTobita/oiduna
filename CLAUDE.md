# Claude Code - Oiduna プロジェクトガイド

このドキュメントは、Claude CodeがOidunaプロジェクトで作業する際の重要な情報を記載しています。

---

## パッケージマネージャー: **uv** を使用すること

**重要**: このプロジェクトは **uv** をパッケージマネージャーとして使用しています。

### ❌ 使用禁止コマンド
```bash
pip install <package>
python -m pip install <package>
source .venv/bin/activate && pip install <package>
```

### ✅ 正しいコマンド
```bash
# 依存関係のインストール
uv sync

# パッケージの追加
uv add <package>

# 開発依存関係の追加
uv add --dev <package>

# Pythonの実行
uv run python <script.py>

# テストの実行
uv run pytest

# カバレッジテスト
uv run pytest --cov=packages/oiduna_models --cov-report=term-missing

# 型チェック
uv run mypy packages/oiduna_models packages/oiduna_auth packages/oiduna_session
```

---

## プロジェクト構成

### パッケージ構造
```
packages/
├── oiduna_models/          # データモデル (Phase 1)
├── oiduna_auth/            # 認証システム (Phase 1)
├── oiduna_session/         # SessionManager (Phase 1)
├── oiduna_api/             # FastAPI routes (Phase 2)
├── oiduna_loop/            # Loop Engine (既存)
├── oiduna_scheduler/       # MessageScheduler (既存)
└── oiduna_destination/     # Destination管理 (既存)
```

### アーキテクチャ
- **Session → Track → Pattern → Event** 階層モデル
- **UUID Token認証** (X-Client-ID + X-Client-Token)
- **SessionCompiler**: Session → ScheduledMessageBatch
- **Loop Engine**: 256-step固定ループ

---

## テストの実行

### 全テスト
```bash
uv run pytest packages/ tests/ -v
```

### 新規パッケージのみ
```bash
uv run pytest packages/oiduna_models packages/oiduna_auth packages/oiduna_session -v
```

### カバレッジ測定（新規パッケージ）
```bash
uv run pytest packages/oiduna_models packages/oiduna_auth packages/oiduna_session \
  --cov=packages/oiduna_models \
  --cov=packages/oiduna_auth \
  --cov=packages/oiduna_session \
  --cov-report=term-missing \
  --cov-report=html
```

**現在のカバレッジ**: 92%

---

## 型チェック

### mypyによる型チェック
```bash
# 新規パッケージ（strictモード）
uv run mypy packages/oiduna_models packages/oiduna_auth packages/oiduna_session --strict

# 全パッケージ（通常モード）
uv run mypy packages/
```

**型安全性**: 新規パッケージは95%カバレッジ

---

## サーバーの起動

### 開発サーバー
```bash
uv run uvicorn oiduna_api.main:app --reload --host 0.0.0.0 --port 57122
```

### プロダクション
```bash
uv run uvicorn oiduna_api.main:app --host 0.0.0.0 --port 57122
```

---

## リファクタリングガイドライン

### 優先度の高い技術的負債

#### 🔴 Critical
1. **SessionManager分割** (497行 → 5クラス)
   - `packages/oiduna_session/manager.py`
   - ClientManager, TrackManager, PatternManager等に分割

#### 🟡 High
2. **Request Objects作成**
   - TrackCreateRequest, PatternCreateRequest等
   - Primitive Obsession解消

3. **長いメソッド分割**
   - create_client() (43行)
   - create_track() (56行)
   - create_pattern() (61行)

詳細: `REFACTORING_REPORT.md`参照

---

## コミットガイドライン

### コミットメッセージ形式
```
<type>: <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

### Type
- `feat`: 新機能
- `fix`: バグ修正
- `refactor`: リファクタリング
- `test`: テスト追加/修正
- `docs`: ドキュメント
- `chore`: その他

---

## ドキュメント

### 主要ドキュメント
- `IMPLEMENTATION_COMPLETE.md` - Phase 1-4完了サマリー
- `REFACTORING_REPORT.md` - リファクタリング & 型安全性レポート
- `docs/MIGRATION_GUIDE.md` - 旧API→新API移行ガイド
- `docs/SSE_EVENTS.md` - SSEイベントリファレンス
- `docs/LIVE_CODING_EXAMPLES.md` - ライブコーディング実用例

### OpenAPI
- 開発サーバー起動後: http://localhost:57122/docs

---

## 重要な制約

### Python バージョン
- **Python 3.13** 固定
- `pyproject.toml`: `requires-python = ">=3.13,<3.14"`

### Loop Engine
- **256-step固定ループ** (変更不可)
- `LOOP_STEPS = 256` (ハードコーディング)

### 認証
- Admin password: `config.yaml`で設定
- Client token: UUID v4 (登録時のみ返却)

---

## トラブルシューティング

### uvが見つからない
```bash
# uvのインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# パスの確認
export PATH="$HOME/.local/bin:$PATH"
```

### 依存関係の問題
```bash
# ロックファイルの再生成
uv lock

# 依存関係の再インストール
uv sync --reinstall
```

### テスト失敗
```bash
# 詳細なエラー表示
uv run pytest -vv --tb=long

# 特定のテストのみ実行
uv run pytest packages/oiduna_session/tests/test_compiler.py::TestSessionCompiler::test_compile -vv
```

---

## 参考リンク

- **uv公式ドキュメント**: https://docs.astral.sh/uv/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **SuperDirt**: https://github.com/musikinformatik/SuperDirt

---

**最終更新**: 2026-02-28
**実装者**: Claude Sonnet 4.5
**テストステータス**: 513/513 passed ✅
**カバレッジ**: 92% (新規パッケージ)
