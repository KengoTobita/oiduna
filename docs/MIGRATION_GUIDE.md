# Oiduna API 移行ガイド

旧API（ScheduledMessageBatch直接送信）から新API（Session/Track/Pattern階層）への移行ガイド

---

## 概要

### 旧アーキテクチャ

```
Client → ScheduledMessageBatch → POST /playback/session → Loop Engine
```

- クライアントがScheduledMessageBatchを生成
- APIに直接送信
- Track/Patternの概念なし

### 新アーキテクチャ

```
Client → Track/Pattern作成 → POST /playback/sync → SessionCompiler → ScheduledMessageBatch → Loop Engine
```

- Session内でTrack/Patternを管理
- SessionCompilerが自動でバッチ生成
- 状態管理、所有権、リアルタイム通知

---

## 後方互換性

**重要**: 旧APIは引き続き動作します。

```python
# 旧API - 引き続き動作
POST /playback/session
{
    "messages": [...],
    "bpm": 120.0,
    "pattern_length": 4.0
}
```

段階的移行が可能です。

---

## 移行手順

### Step 1: Client登録

**新規**: Clientを登録してトークンを取得

```bash
# Client登録
curl -X POST http://localhost:57122/clients/my_client \
  -H "Content-Type: application/json" \
  -d '{
    "client_name": "My MARS Client",
    "distribution": "mars",
    "metadata": {"version": "1.0.0"}
  }'

# レスポンス
{
  "client_id": "my_client",
  "client_name": "My MARS Client",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "distribution": "mars",
  "metadata": {"version": "1.0.0"}
}
```

**重要**: `token`は登録時のみ返却されます。保存してください。

### Step 2: 以降の全リクエストにトークンを付与

```bash
# 全てのリクエストに必須
-H "X-Client-ID: my_client"
-H "X-Client-Token: 550e8400-e29b-41d4-a716-446655440000"
```

### Step 3: Trackの作成

**旧**: なし（ScheduledMessageに直接含める）

**新**:

```bash
curl -X POST http://localhost:57122/tracks/kick_track \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "track_name": "Kick",
    "destination_id": "superdirt",
    "base_params": {
      "sound": "bd",
      "orbit": 0,
      "gain": 0.8
    }
  }'
```

**base_params**: 全てのイベントに適用されるデフォルトパラメータ

### Step 4: Patternの作成

**旧**: ScheduledMessageとして直接送信

**新**:

```bash
curl -X POST http://localhost:57122/tracks/kick_track/patterns/main \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_name": "Main Beat",
    "active": true,
    "events": [
      {
        "step": 0,
        "cycle": 0.0,
        "params": {}
      },
      {
        "step": 64,
        "cycle": 1.0,
        "params": {"gain": 0.9}
      },
      {
        "step": 128,
        "cycle": 2.0,
        "params": {}
      },
      {
        "step": 192,
        "cycle": 3.0,
        "params": {"gain": 0.9}
      }
    ]
  }'
```

**events**: 個別イベント（Track.base_paramsとマージされる）

### Step 5: セッション同期

**新規**: SessionをLoop Engineに同期

```bash
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>"

# レスポンス
{
  "status": "synced",
  "message_count": 4,
  "bpm": 120.0
}
```

SessionCompilerが自動で:
- 全TrackのアクティブなPatternを収集
- base_paramsとevent paramsをマージ
- ScheduledMessageBatchを生成

### Step 6: 再生開始

```bash
# 旧APIと同じ
curl -X POST http://localhost:57122/playback/start
```

---

## パラメータマージの仕組み

```python
# Track
base_params = {"sound": "bd", "orbit": 0, "gain": 0.8}

# Event
event_params = {"gain": 0.9}  # Override gain

# 結果（ScheduledMessage.params）
merged_params = {
    "sound": "bd",     # From base_params
    "orbit": 0,        # From base_params
    "gain": 0.9,       # From event_params (override)
    "track_id": "kick_track"  # Added by compiler
}
```

**優先度**: `Event.params` > `Track.base_params`

---

## 増分更新

### Pattern更新

```bash
# イベントのみ更新
curl -X PATCH http://localhost:57122/tracks/kick_track/patterns/main \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {"step": 0, "cycle": 0.0, "params": {}}
    ]
  }'

# 再同期
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>"
```

### Patternのアクティブ切り替え

```bash
# 非アクティブに
curl -X PATCH http://localhost:57122/tracks/kick_track/patterns/main \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{"active": false}'

# 再同期（このパターンは除外される）
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>"
```

### Track base_params更新

```bash
# Shallow merge
curl -X PATCH http://localhost:57122/tracks/kick_track \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "base_params": {
      "gain": 0.7
    }
  }'

# 再同期
curl -X POST http://localhost:57122/playback/sync \
  -H "X-Client-ID: my_client" \
  -H "X-Client-Token: <token>"
```

---

## コード例

### Python (旧API)

```python
import requests

# 旧API
batch = {
    "messages": [
        {
            "destination_id": "superdirt",
            "cycle": 0.0,
            "step": 0,
            "params": {"sound": "bd", "orbit": 0}
        },
        # ... more messages
    ],
    "bpm": 120.0,
    "pattern_length": 4.0
}

response = requests.post(
    "http://localhost:57122/playback/session",
    json=batch
)
```

### Python (新API)

```python
import requests

BASE_URL = "http://localhost:57122"

# 1. Client登録
response = requests.post(
    f"{BASE_URL}/clients/my_client",
    json={
        "client_name": "My Client",
        "distribution": "python"
    }
)
token = response.json()["token"]

# 認証ヘッダー
headers = {
    "X-Client-ID": "my_client",
    "X-Client-Token": token
}

# 2. Track作成
requests.post(
    f"{BASE_URL}/tracks/kick_track",
    headers=headers,
    json={
        "track_name": "Kick",
        "destination_id": "superdirt",
        "base_params": {"sound": "bd", "orbit": 0}
    }
)

# 3. Pattern作成
requests.post(
    f"{BASE_URL}/tracks/kick_track/patterns/main",
    headers=headers,
    json={
        "pattern_name": "Main",
        "active": True,
        "events": [
            {"step": 0, "cycle": 0.0, "params": {}},
            {"step": 64, "cycle": 1.0, "params": {}}
        ]
    }
)

# 4. 同期
requests.post(f"{BASE_URL}/playback/sync", headers=headers)

# 5. 再生
requests.post(f"{BASE_URL}/playback/start")
```

---

## SSEイベント受信

### JavaScript

```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

// Track作成通知
eventSource.addEventListener('track_created', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Track created: ${data.track_id}`);
});

// Pattern更新通知
eventSource.addEventListener('pattern_updated', (event) => {
  const data = JSON.parse(event.data);
  console.log(`Pattern updated: ${data.pattern_id}`);

  // 他人の変更を検知
  if (data.client_id !== myClientId) {
    showWarning(`Pattern ${data.pattern_id} was modified by another user`);
  }
});

// BPM変更通知
eventSource.addEventListener('environment_updated', (event) => {
  const data = JSON.parse(event.data);
  if (data.bpm) {
    updateBPMDisplay(data.bpm);
  }
});
```

---

## よくある質問

### Q: 旧APIはいつまで使える？

A: 引き続き使用可能です。`POST /playback/session`は削除されません。

### Q: 複数のPatternを同時に再生できる？

A: はい。Track内の全てのactiveなPatternが再生されます。

```bash
# Pattern 1: メインビート
POST /tracks/kick/patterns/main
{"active": true, "events": [...]}

# Pattern 2: フィル
POST /tracks/kick/patterns/fill
{"active": true, "events": [...]}

# 両方とも再生される
POST /playback/sync
```

### Q: Patternを切り替えるには？

A: `active`フラグを切り替えて`/sync`を呼ぶ

```bash
# メインを非アクティブ
PATCH /tracks/kick/patterns/main
{"active": false}

# フィルをアクティブ
PATCH /tracks/kick/patterns/fill
{"active": true}

# 再同期
POST /playback/sync
```

### Q: トークンを忘れた場合は？

A: 再登録が必要です。同じclient_idは使用できません（409エラー）。別のIDで登録してください。

### Q: 複数クライアントが同じTrackを編集できる？

A: 所有者のみ編集可能です。他人のTrackを編集しようとすると403エラー。

---

## トラブルシューティング

### 401 Unauthorized

```json
{"detail": "Invalid credentials"}
```

**原因**: トークンが無効またはヘッダーが不足

**解決**:
```bash
# 正しいヘッダーを確認
-H "X-Client-ID: <your_client_id>"
-H "X-Client-Token: <your_token>"
```

### 403 Forbidden

```json
{"detail": "You don't own this track"}
```

**原因**: 他人のリソースを編集しようとしている

**解決**: 自分のTrack/Patternのみ編集してください

### 404 Not Found

```json
{"detail": "Track not found"}
```

**原因**: Track/Patternが存在しない

**解決**:
```bash
# Trackを先に作成
POST /tracks/<track_id>

# その後Patternを作成
POST /tracks/<track_id>/patterns/<pattern_id>
```

### 400 Bad Request

```json
{"detail": "Destination superdirt does not exist"}
```

**原因**: 指定したdestination_idが存在しない

**解決**:
```bash
# 利用可能なdestinationを確認（admin権限必要）
GET /admin/destinations
-H "X-Admin-Password: <password>"
```

---

## パフォーマンス考慮

### バッチ更新

複数の変更を行う場合、最後に1回だけ`/sync`を呼ぶ:

```bash
# ❌ 非効率
POST /tracks/t1/patterns/p1 → POST /playback/sync
POST /tracks/t2/patterns/p2 → POST /playback/sync
POST /tracks/t3/patterns/p3 → POST /playback/sync

# ✅ 効率的
POST /tracks/t1/patterns/p1
POST /tracks/t2/patterns/p2
POST /tracks/t3/patterns/p3
POST /playback/sync  # 1回だけ
```

### コンパイル時間

- 10 tracks × 10 patterns × 10 events: ~5ms
- 100 tracks: ~50ms（通常のライブコーディングでは十分）

---

## 次のステップ

1. [SSEイベントリファレンス](./SSE_EVENTS.md) - リアルタイム通知の詳細
2. [API Reference](http://localhost:57122/docs) - 完全なAPIドキュメント
3. [ライブコーディング例](./LIVE_CODING_EXAMPLES.md) - 実用例

---

## サポート

- Issues: https://github.com/your-org/oiduna/issues
- Documentation: `/docs` directory
