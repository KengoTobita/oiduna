# Oiduna 起動スクリプト

Oidunaをスマートに起動するためのスクリプト集。

## スクリプト一覧

### setup_superdirt.sh

SuperColliderの自動起動を設定します（一度だけ実行）。

```bash
./scripts/setup_superdirt.sh
```

**動作**:
1. SuperColliderの `startup.scd` を自動生成
2. 既存の `startup.scd` があればバックアップ
3. Oidunaデータディレクトリのパスを自動設定

**実行後**:
- `sclang` を起動するだけでSuperDirt + Oiduna連携が自動起動
- カスタムサンプル・SynthDefの監視も自動設定

---

### start_superdirt.sh

SuperDirtをコマンドラインから直接起動します（startup.scd不要）。

```bash
./scripts/start_superdirt.sh
```

**動作**:
- 一時的なSuperColliderスクリプトを生成
- SuperDirt + Oiduna連携を起動
- インタラクティブモードで実行

**用途**:
- setup不要で今すぐ起動したい
- 一時的なテスト
- startup.scdを変更したくない

---

### start_all.sh

SuperDirt + Oiduna APIを統合起動します（tmux使用）。

```bash
./scripts/start_all.sh
```

**動作**:
1. tmuxセッション `oiduna` を作成
2. ウィンドウ1: SuperDirt起動
3. ウィンドウ2: Oiduna API起動（10秒待機後）
4. ウィンドウ3: コマンドシェル

**tmux操作**:
- ウィンドウ切り替え: `Ctrl+b n` (次), `Ctrl+b p` (前)
- デタッチ: `Ctrl+b d`
- 再アタッチ: `tmux attach -t oiduna`
- 終了: `Ctrl+b :kill-session`

**用途**:
- 開発環境の起動
- デモ・プレゼンテーション
- 複数コンポーネントの管理

---

### restore_superdirt.sh

SuperColliderの `startup.scd` を元に戻します。

```bash
./scripts/restore_superdirt.sh
```

**動作**:
1. バックアップファイルを検索
2. 最新のバックアップから復元
3. 現在のファイルもバックアップ

**用途**:
- setup前の設定に戻したい
- Oiduna連携を無効化したい

---

## 使用例

### 初回セットアップ

```bash
# 1. SuperDirt自動起動を設定
./scripts/setup_superdirt.sh

# 2. 起動確認
sclang  # SuperDirt自動起動を確認

# 3. 別のターミナルでOiduna API起動
uv run python -m oiduna_api.main
```

### 日常的な使用（setup後）

```bash
# ターミナル1
sclang

# ターミナル2
uv run python -m oiduna_api.main
```

### tmuxで統合起動

```bash
# 一発起動
./scripts/start_all.sh

# バックグラウンドで実行
./scripts/start_all.sh
# → Ctrl+b d でデタッチ

# 後で再アタッチ
tmux attach -t oiduna
```

### 元に戻す

```bash
./scripts/restore_superdirt.sh
```

---

## 前提条件

- **SuperCollider** がインストールされている
- **SuperDirt** がインストールされている
- **uv** がインストールされている（Python環境管理）
- **tmux** がインストールされている（start_all.sh使用時のみ）

### tmuxのインストール

```bash
# macOS
brew install tmux

# Linux (Debian/Ubuntu)
sudo apt install tmux

# Linux (Fedora/RHEL)
sudo dnf install tmux
```

---

## トラブルシューティング

### "sclang: command not found"

SuperColliderがインストールされていないか、PATHが通っていません。

```bash
# macOSの場合
export PATH="/Applications/SuperCollider.app/Contents/MacOS:$PATH"

# Linuxの場合
which sclang  # パスを確認
```

### SuperDirtが起動しない

```supercollider
// SuperColliderで実行
Quarks.update;
Quarks.install("SuperDirt");
0.exit;
```

### ポートが使用中

```bash
# OSCポート（57120）
lsof -i :57120
kill <PID>

# HTTPポート（8000）
lsof -i :8000
kill <PID>
```

### tmuxセッションが残っている

```bash
# セッション一覧
tmux ls

# 強制終了
tmux kill-session -t oiduna
```

---

## ファイル配置

スクリプトは以下のディレクトリ構造を想定しています：

```
oiduna/
├── scripts/
│   ├── setup_superdirt.sh
│   ├── start_superdirt.sh
│   ├── start_all.sh
│   └── restore_superdirt.sh
├── oiduna_data/          # アセットディレクトリ（自動作成）
│   ├── samples/
│   └── synthdefs/
└── packages/
    └── oiduna_api/
```

---

## 参考資料

- [Quick Start Guide](../docs/quick-start.md) - 起動方法の詳細
- [SuperDirt Startup Template](../docs/superdirt_startup_oiduna.scd) - 起動スクリプトのテンプレート
- [Distribution Guide](../docs/distribution-guide.md) - Distribution開発
