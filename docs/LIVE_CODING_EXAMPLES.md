# ライブコーディング実用例

Oiduna新APIを使った実際のライブコーディングシナリオ

---

## シナリオ1: 基本的なキックパターン

### Step 1: セットアップ

```bash
# 1. Client登録
curl -X POST http://localhost:57122/clients/alice \
  -d '{"client_name": "Alice", "distribution": "mars"}' \
  | jq -r '.token' > ~/.oiduna_token

TOKEN=$(cat ~/.oiduna_token)

# 2. Kickトラック作成
curl -X POST http://localhost:57122/tracks/kick \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "track_name": "Kick",
    "destination_id": "superdirt",
    "base_params": {
      "sound": "bd",
      "orbit": 0,
      "gain": 0.9
    }
  }'
```

### Step 2: 4つ打ちパターン

```bash
curl -X POST http://localhost:57122/tracks/kick/patterns/four_on_floor \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Four on Floor",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}},
      {"step": 64, "cycle": 1.0, "params": {}},
      {"step": 128, "cycle": 2.0, "params": {}},
      {"step": 192, "cycle": 3.0, "params": {}}
    ]
  }'

# 同期して再生
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"

curl -X POST http://localhost:57122/playback/start
```

### Step 3: アクセントを追加

```bash
# 2拍目と4拍目にアクセント
curl -X POST http://localhost:57122/tracks/kick/patterns/accents \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Accents",
    "active": true,
    "events": [
      {"step": 64, "cycle": 1.0, "params": {"gain": 1.1}},
      {"step": 192, "cycle": 3.0, "params": {"gain": 1.1}}
    ]
  }'

# 再同期
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

結果: メインパターン + アクセントが重なって再生される

---

## シナリオ2: ハイハット追加

```bash
# Hihatトラック作成
curl -X POST http://localhost:57122/tracks/hh \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "track_name": "HiHat",
    "destination_id": "superdirt",
    "base_params": {
      "sound": "hh",
      "orbit": 0,
      "gain": 0.6
    }
  }'

# 8分音符パターン
curl -X POST http://localhost:57122/tracks/hh/patterns/eighth \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Eighth Notes",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}},
      {"step": 32, "cycle": 0.5, "params": {}},
      {"step": 64, "cycle": 1.0, "params": {}},
      {"step": 96, "cycle": 1.5, "params": {}},
      {"step": 128, "cycle": 2.0, "params": {}},
      {"step": 160, "cycle": 2.5, "params": {}},
      {"step": 192, "cycle": 3.0, "params": {}},
      {"step": 224, "cycle": 3.5, "params": {}}
    ]
  }'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

---

## シナリオ3: パターン切り替え

### メインとフィルを用意

```bash
# メインパターン
curl -X POST http://localhost:57122/tracks/kick/patterns/main \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Main",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}},
      {"step": 64, "cycle": 1.0, "params": {}},
      {"step": 128, "cycle": 2.0, "params": {}},
      {"step": 192, "cycle": 3.0, "params": {}}
    ]
  }'

# フィルパターン
curl -X POST http://localhost:57122/tracks/kick/patterns/fill \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Fill",
    "active": false,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}},
      {"step": 16, "cycle": 0.25, "params": {"gain": 0.8}},
      {"step": 32, "cycle": 0.5, "params": {"gain": 0.7}},
      {"step": 48, "cycle": 0.75, "params": {"gain": 0.8}},
      {"step": 64, "cycle": 1.0, "params": {}}
    ]
  }'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

### ライブ切り替え

```bash
# フィルに切り替え
curl -X PATCH http://localhost:57122/tracks/kick/patterns/main \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{"active": false}'

curl -X PATCH http://localhost:57122/tracks/kick/patterns/fill \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{"active": true}'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"

# 数秒後、メインに戻す
curl -X PATCH http://localhost:57122/tracks/kick/patterns/main \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{"active": true}'

curl -X PATCH http://localhost:57122/tracks/kick/patterns/fill \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{"active": false}'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

---

## シナリオ4: BPM変更

```bash
# 現在のBPM確認
curl http://localhost:57122/session/state \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  | jq '.environment.bpm'

# BPMを140に変更
curl -X PATCH http://localhost:57122/session/environment \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{"bpm": 140.0}'

# 再生中でもリアルタイムで変更される
```

---

## シナリオ5: ベースライン追加

```bash
# Bassトラック
curl -X POST http://localhost:57122/tracks/bass \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "track_name": "Bass",
    "destination_id": "superdirt",
    "base_params": {
      "sound": "bass",
      "orbit": 1,
      "gain": 0.8,
      "lpf": 800
    }
  }'

# シンプルなベースライン (C - C - G - F)
curl -X POST http://localhost:57122/tracks/bass/patterns/main \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Main Bassline",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {"note": 36}},
      {"step": 64, "cycle": 1.0, "params": {"note": 36}},
      {"step": 128, "cycle": 2.0, "params": {"note": 43}},
      {"step": 192, "cycle": 3.0, "params": {"note": 41}}
    ]
  }'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

---

## シナリオ6: パラメータモジュレーション

```bash
# フィルターをスイープ
curl -X POST http://localhost:57122/tracks/bass/patterns/filter_sweep \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Filter Sweep",
    "active": true,
    "events": [
      {"step": 0, "cycle": 0.0, "params": {"lpf": 400}},
      {"step": 64, "cycle": 1.0, "params": {"lpf": 800}},
      {"step": 128, "cycle": 2.0, "params": {"lpf": 1200}},
      {"step": 192, "cycle": 3.0, "params": {"lpf": 800}}
    ]
  }'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

---

## シナリオ7: エフェクト追加

```bash
# Delay送信量を変化
curl -X POST http://localhost:57122/tracks/hh/patterns/delay \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  -d '{
    "pattern_name": "Delay Send",
    "active": true,
    "events": [
      {"step": 224, "cycle": 3.5, "params": {"delaySend": 0.5, "delayTime": 0.25}}
    ]
  }'

curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN"
```

---

## シナリオ8: 複数クライアント協調

### Alice（リズムセクション担当）

```bash
# Aliceのセットアップ
curl -X POST http://localhost:57122/clients/alice \
  -d '{"client_name": "Alice", "distribution": "mars"}'
# → token保存

# Kick & Snare
curl -X POST http://localhost:57122/tracks/drums \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $ALICE_TOKEN" \
  -d '{
    "track_name": "Drums",
    "destination_id": "superdirt",
    "base_params": {"orbit": 0}
  }'
```

### Bob（メロディ担当）

```bash
# Bobのセットアップ
curl -X POST http://localhost:57122/clients/bob \
  -d '{"client_name": "Bob", "distribution": "mars"}'
# → token保存

# Lead synth
curl -X POST http://localhost:57122/tracks/lead \
  -H "X-Client-ID: bob" \
  -H "X-Client-Token: $BOB_TOKEN" \
  -d '{
    "track_name": "Lead",
    "destination_id": "superdirt",
    "base_params": {"sound": "superpiano", "orbit": 2}
  }'
```

### SSEで他人の変更を監視

```javascript
// Alice's client
const eventSource = new EventSource('http://localhost:57122/stream');

eventSource.addEventListener('track_created', (event) => {
  const data = JSON.parse(event.data);
  if (data.client_id === 'bob') {
    console.log(`Bob created track: ${data.track_name}`);
  }
});
```

---

## シナリオ9: セッション保存・復元

### 現在の状態を取得

```bash
# 完全な状態を取得
curl http://localhost:57122/session/state \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  > session_backup.json
```

### 復元スクリプト

```python
import json
import requests

BASE_URL = "http://localhost:57122"
TOKEN = "your-token-here"
headers = {
    "X-Client-ID": "alice",
    "X-Client-Token": TOKEN
}

# バックアップから読み込み
with open('session_backup.json') as f:
    session = json.load(f)

# Tracksを再作成
for track_id, track in session['tracks'].items():
    requests.post(
        f"{BASE_URL}/tracks/{track_id}",
        headers=headers,
        json={
            "track_name": track['track_name'],
            "destination_id": track['destination_id'],
            "base_params": track['base_params']
        }
    )

    # Patternsを再作成
    for pattern_id, pattern in track['patterns'].items():
        requests.post(
            f"{BASE_URL}/tracks/{track_id}/patterns/{pattern_id}",
            headers=headers,
            json={
                "pattern_name": pattern['pattern_name'],
                "active": pattern['active'],
                "events": pattern['events']
            }
        )

# 同期
requests.post(f"{BASE_URL}/playback/sync", headers=headers)
print("Session restored!")
```

---

## シナリオ10: ライブコーディング統合（Python）

```python
import requests
import time

class OidunaLive:
    def __init__(self, client_id, token):
        self.base_url = "http://localhost:57122"
        self.headers = {
            "X-Client-ID": client_id,
            "X-Client-Token": token
        }

    def track(self, track_id, track_name, destination, **base_params):
        """Trackを作成"""
        return requests.post(
            f"{self.base_url}/tracks/{track_id}",
            headers=self.headers,
            json={
                "track_name": track_name,
                "destination_id": destination,
                "base_params": base_params
            }
        )

    def pattern(self, track_id, pattern_id, name, events, active=True):
        """Patternを作成"""
        return requests.post(
            f"{self.base_url}/tracks/{track_id}/patterns/{pattern_id}",
            headers=self.headers,
            json={
                "pattern_name": name,
                "active": active,
                "events": events
            }
        )

    def sync(self):
        """セッションを同期"""
        return requests.post(
            f"{self.base_url}/playback/sync",
            headers=self.headers
        )

    def play(self):
        """再生開始"""
        return requests.post(f"{self.base_url}/playback/start")

    def stop(self):
        """停止"""
        return requests.post(f"{self.base_url}/playback/stop")

# 使用例
live = OidunaLive("alice", "your-token-here")

# Kickトラック
live.track("kick", "Kick", "superdirt", sound="bd", orbit=0, gain=0.9)
live.pattern("kick", "main", "Main", [
    {"step": 0, "cycle": 0.0, "params": {}},
    {"step": 64, "cycle": 1.0, "params": {}},
    {"step": 128, "cycle": 2.0, "params": {}},
    {"step": 192, "cycle": 3.0, "params": {}},
])

# HiHatトラック
live.track("hh", "HiHat", "superdirt", sound="hh", orbit=0, gain=0.6)
live.pattern("hh", "eighth", "Eighth", [
    {"step": i, "cycle": i/64, "params": {}}
    for i in range(0, 256, 32)  # 8分音符
])

# 同期して再生
live.sync()
live.play()

# ライブでパラメータ変更
time.sleep(4)
live.pattern("kick", "variation", "Variation", [
    {"step": 0, "cycle": 0.0, "params": {"gain": 1.0}},
    {"step": 32, "cycle": 0.5, "params": {"gain": 0.7}},
    {"step": 64, "cycle": 1.0, "params": {"gain": 1.0}},
])
live.sync()
```

---

## Tips

### パフォーマンス最適化

```bash
# 複数の変更をまとめて同期
POST /tracks/t1/patterns/p1
POST /tracks/t2/patterns/p2
POST /tracks/t3/patterns/p3
POST /playback/sync  # 最後に1回だけ
```

### デバッグ

```bash
# 現在のセッション状態を確認
curl http://localhost:57122/session/state \
  -H "X-Client-ID: alice" \
  -H "X-Client-Token: $TOKEN" \
  | jq '.'

# 再生ステータス確認
curl http://localhost:57122/playback/status | jq '.'
```

### ショートカット

```bash
# 環境変数にセット
export OIDUNA_URL="http://localhost:57122"
export OIDUNA_CLIENT="alice"
export OIDUNA_TOKEN="your-token"

# エイリアス
alias oiduna-sync='curl -X POST $OIDUNA_URL/playback/sync -H "X-Client-ID: $OIDUNA_CLIENT" -H "X-Client-Token: $OIDUNA_TOKEN"'
alias oiduna-play='curl -X POST $OIDUNA_URL/playback/start'
alias oiduna-stop='curl -X POST $OIDUNA_URL/playback/stop'

# 使用
oiduna-sync
oiduna-play
```

---

## 次のステップ

- [Migration Guide](./MIGRATION_GUIDE.md) - 旧APIからの移行
- [SSE Events](./SSE_EVENTS.md) - リアルタイム通知
- [API Reference](http://localhost:57122/docs) - 完全なAPIドキュメント
