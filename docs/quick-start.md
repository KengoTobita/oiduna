# Oiduna クイックスタートガイド

Oidunaを最速で起動する方法を説明します。

## 前提条件

- **SuperCollider** がインストールされている
- **SuperDirt** がインストールされている（Quarks経由）
- **uv** がインストールされている（Python環境管理）

### SuperDirtのインストール確認

```supercollider
// SuperColliderで実行
Quarks.gui;  // QuarksブラウザでSuperDirtを探してインストール
```

または

```bash
# コマンドラインから
sclang -e 'Quarks.install("SuperDirt"); 0.exit;'
```

---

## 起動方法

### 方法1: 自動起動設定（推奨）⭐

**一度だけセットアップを実行**:

```bash
cd /home/tobita/study/livecoding/oiduna
./scripts/setup_superdirt.sh
```

これにより、SuperColliderの `startup.scd` が自動設定されます。

**以降は簡単に起動**:

```bash
# ターミナル1: SuperDirt起動（自動でOiduna連携）
sclang

# ターミナル2: Oiduna API起動
cd /home/tobita/study/livecoding/oiduna
uv run python -m oiduna_api.main
```

---

### 方法2: スクリプトで起動

セットアップ不要で、すぐに起動できます。

```bash
# ターミナル1: SuperDirt起動
cd /home/tobita/study/livecoding/oiduna
./scripts/start_superdirt.sh

# ターミナル2: Oiduna API起動
uv run python -m oiduna_api.main
```

---

### 方法3: 統合起動（tmux使用）

**tmuxを使って全て一発起動**（最もスマート）:

```bash
cd /home/tobita/study/livecoding/oiduna
./scripts/start_all.sh
```

これにより：
- SuperDirtが自動起動（ウィンドウ1）
- Oiduna APIが自動起動（ウィンドウ2）
- コマンドシェルが準備される（ウィンドウ3）

#### tmux操作方法

- **ウィンドウ切り替え**: `Ctrl+b n` (次), `Ctrl+b p` (前)
- **デタッチ**: `Ctrl+b d`（バックグラウンドで実行継続）
- **再アタッチ**: `tmux attach -t oiduna`
- **終了**: `Ctrl+b :kill-session`

---

## 動作確認

### 1. ヘルスチェック

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

### 2. サンプルパターンを再生

```bash
# パターンをロード
curl -X POST http://localhost:8000/playback/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {"bpm": 120},
    "tracks": {
      "bd": {
        "sound": "bd",
        "orbit": 0,
        "gain": 1.0,
        "pan": 0.5,
        "mute": false,
        "solo": false,
        "sequence": [
          {"pitch": "0", "start": 0, "length": 1},
          {"pitch": "0", "start": 4, "length": 1},
          {"pitch": "0", "start": 8, "length": 1},
          {"pitch": "0", "start": 12, "length": 1}
        ]
      }
    },
    "sequences": {}
  }'

# 再生開始
curl -X POST http://localhost:8000/playback/start
```

🔊 音が鳴れば成功！

### 3. 停止

```bash
curl -X POST http://localhost:8000/playback/stop
```

---

## カスタムサンプルのアップロード

```bash
# サンプルをアップロード
curl -X POST http://localhost:8000/assets/samples \
  -F "file=@my_kick.wav" \
  -F "category=kicks"

# パターンで使用
curl -X POST http://localhost:8000/playback/pattern \
  -H "Content-Type: application/json" \
  -d '{
    "environment": {"bpm": 120},
    "tracks": {
      "custom": {
        "sound": "kicks",
        "orbit": 0,
        "sequence": [{"pitch": "0", "start": 0, "length": 1}]
      }
    },
    "sequences": {}
  }'
```

---

## トラブルシューティング

### SuperDirtが起動しない

```supercollider
// SuperColliderで実行
Quarks.update;
Quarks.install("SuperDirt");
0.exit;
```

### OSCポートが使用中

```bash
# ポート57120を使用しているプロセスを確認
lsof -i :57120

# 必要なら終了
kill <PID>
```

### Oiduna APIが起動しない

```bash
# 依存関係の再インストール
cd /home/tobita/study/livecoding/oiduna
uv sync

# ポート8000が使用中でないか確認
lsof -i :8000
```

---

## 次のステップ

- [API Examples](api-examples.md) - 全エンドポイントのcurl例
- [Data Model](data-model.md) - CompiledSessionスキーマ
- [Distribution Guide](distribution-guide.md) - MARS等のDistribution開発

---

## 開発モード

開発時は、自動リロードを有効にして起動：

```bash
cd /home/tobita/study/livecoding/oiduna
uv run python -m oiduna_api.main  # uvicorn --reload付きで起動
```

コードを編集すると自動的に再起動します。

---

## まとめ

### 最速起動（tmux使用）

```bash
./scripts/start_all.sh
```

### シンプル起動

```bash
# ターミナル1
./scripts/start_superdirt.sh

# ターミナル2
uv run python -m oiduna_api.main
```

### 恒久設定

```bash
./scripts/setup_superdirt.sh  # 一度だけ実行
# 以降は sclang で自動起動
```

どの方法でも、**SuperDirt (port 57120) + Oiduna API (port 8000)** が起動します！
