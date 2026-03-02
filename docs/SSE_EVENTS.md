# Server-Sent Events (SSE) リファレンス

Oiduna APIはSSE (Server-Sent Events)でリアルタイム通知を配信します。

---

## 接続

```bash
# curl
curl -N http://localhost:57122/stream

# JavaScript
const eventSource = new EventSource('http://localhost:57122/stream');
```

**認証不要**: `/stream`エンドポイントは認証なしで接続可能

---

## イベント形式

全てのイベントは以下の形式:

```
event: <event_type>
data: <json_data>

```

例:
```
event: track_created
data: {"track_id":"track_001","track_name":"kick","client_id":"alice_001"}

```

---

## イベントタイプ

### システムイベント

#### `connected`

接続確立時に1回だけ送信

**データ**:
```json
{
  "timestamp": 1709179200.123
}
```

**用途**: 接続成功の確認

---

#### `heartbeat`

15秒ごとに送信（キープアライブ）

**データ**:
```json
{
  "timestamp": 1709179215.456
}
```

**用途**: 接続維持、タイムアウト検出

---

### クライアントイベント

#### `client_connected`

新しいクライアントが登録された

**トリガー**: `POST /clients/{id}`

**データ**:
```json
{
  "client_id": "alice_001",
  "client_name": "Alice's MARS",
  "distribution": "mars"
}
```

**用途**:
- 他のユーザーの参加を通知
- クライアントリスト更新

**JavaScript例**:
```javascript
eventSource.addEventListener('client_connected', (event) => {
  const data = JSON.parse(event.data);
  console.log(`${data.client_name} joined`);
  updateClientList();
});
```

---

#### `client_disconnected`

クライアントが切断された

**トリガー**: `DELETE /clients/{id}`

**データ**:
```json
{
  "client_id": "alice_001"
}
```

**用途**:
- ユーザー離脱を通知
- クライアントリスト更新

---

### Trackイベント

#### `track_created`

新しいTrackが作成された

**トリガー**: `POST /tracks/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "track_name": "kick",
  "client_id": "alice_001",
  "destination_id": "superdirt"
}
```

**用途**:
- Trackリスト更新
- UI更新（新しいTrack表示）

**JavaScript例**:
```javascript
eventSource.addEventListener('track_created', (event) => {
  const data = JSON.parse(event.data);
  addTrackToUI(data);

  if (data.client_id !== myClientId) {
    showNotification(`${data.track_name} created by another user`);
  }
});
```

---

#### `track_updated`

Trackのbase_paramsが更新された

**トリガー**: `PATCH /tracks/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "client_id": "alice_001",
  "updated_params": {
    "gain": 0.7
  }
}
```

**用途**:
- 他のクライアントの変更を検知
- パラメータ表示を更新

**重要**: `updated_params`は変更されたフィールドのみ含む（全paramsではない）

**JavaScript例**:
```javascript
eventSource.addEventListener('track_updated', (event) => {
  const data = JSON.parse(event.data);

  if (data.client_id !== myClientId) {
    // 他人が編集した場合の警告
    showWarning(`Track ${data.track_id} was modified by another user`);

    // 自動リロード（オプション）
    refreshTrack(data.track_id);
  }
});
```

---

#### `track_deleted`

Trackが削除された

**トリガー**: `DELETE /tracks/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "client_id": "alice_001"
}
```

**用途**:
- UIからTrackを削除
- 依存関係のクリーンアップ

---

### Patternイベント

#### `pattern_created`

新しいPatternが作成された

**トリガー**: `POST /tracks/{track_id}/patterns/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "pattern_id": "pattern_001",
  "pattern_name": "main_beat",
  "client_id": "alice_001",
  "active": true,
  "event_count": 4
}
```

**用途**:
- Patternリスト更新
- UI更新（新しいPattern表示）

**JavaScript例**:
```javascript
eventSource.addEventListener('pattern_created', (event) => {
  const data = JSON.parse(event.data);
  addPatternToTrack(data.track_id, data);

  console.log(`Pattern ${data.pattern_name} with ${data.event_count} events`);
});
```

---

#### `pattern_updated`

Patternが更新された（active状態またはevents）

**トリガー**: `PATCH /tracks/{track_id}/patterns/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "pattern_id": "pattern_001",
  "client_id": "alice_001",
  "active": false,
  "event_count": 8
}
```

**用途**:
- Pattern状態の同期
- active切り替えの通知
- イベント数の更新

**注意**: 個別のイベント内容は含まれません。必要なら`GET /tracks/{id}/patterns/{id}`で取得。

**JavaScript例**:
```javascript
eventSource.addEventListener('pattern_updated', (event) => {
  const data = JSON.parse(event.data);

  // Active状態を更新
  updatePatternActive(data.pattern_id, data.active);

  // 自分以外の変更を警告
  if (data.client_id !== myClientId) {
    showWarning(`Pattern ${data.pattern_id} modified by another user`);
  }
});
```

---

#### `pattern_deleted`

Patternが削除された

**トリガー**: `DELETE /tracks/{track_id}/patterns/{id}`

**データ**:
```json
{
  "track_id": "track_001",
  "pattern_id": "pattern_001",
  "client_id": "alice_001"
}
```

**用途**:
- UIからPatternを削除
- 関連リソースのクリーンアップ

---

### Environmentイベント

#### `environment_updated`

グローバル環境設定が変更された

**トリガー**: `PATCH /session/environment`

**データ**:
```json
{
  "bpm": 140.0,
  "metadata": {
    "key": "Am",
    "scale": "minor"
  },
  "position_update_interval": "bar"
}
```

**注意**: 変更されたフィールドのみ含まれます

**用途**:
- BPM表示の更新
- メタデータ同期
- SSE position頻度の変更検知

**JavaScript例**:
```javascript
eventSource.addEventListener('environment_updated', (event) => {
  const data = JSON.parse(event.data);

  if (data.bpm) {
    updateBPMDisplay(data.bpm);
    console.log(`BPM changed to ${data.bpm}`);
  }

  if (data.metadata) {
    updateMetadataDisplay(data.metadata);
  }
});
```

---

### Loop Engineイベント

#### `position`

現在の再生位置（設定可能な頻度）

**トリガー**: Loop Engine内部

**送信頻度** (`position_update_interval`で設定):
- **`"beat"`** (デフォルト): 4ステップごと（1拍ごと）— BPM 120で約2イベント/秒
- **`"bar"`**: 16ステップごと（1小節ごと）— BPM 120で約0.5イベント/秒（ネットワーク負荷75%削減）

設定方法:
```bash
PATCH /session/environment
{
  "position_update_interval": "bar"
}
```

**データ**:
```json
{
  "step": 64,
  "bar": 4,
  "beat": 0,
  "bpm": 120.0,
  "transport": "playing"
}
```

**用途**:
- 再生位置インジケーター
- 同期表示

**クライアント側の補間** (`"bar"`設定時推奨):

更新頻度を下げた場合、クライアント側でBPMを使って中間位置を推定できます:

```javascript
// 設定取得
const config = await fetch('/config').then(r => r.json());
const bpm = config.environment.bpm;

// 最後の位置を記録
let lastPosition = { step: 0, beat: 0, bar: 0 };
let lastUpdateTime = Date.now();

eventSource.addEventListener('position', (e) => {
  lastPosition = JSON.parse(e.data);
  lastUpdateTime = Date.now();
});

// 補間（60fps で呼び出し）
function getInterpolatedPosition() {
  const elapsed = (Date.now() - lastUpdateTime) / 1000;
  const stepDuration = 60 / (bpm * 4);
  const estimatedStep = lastPosition.step + Math.floor(elapsed / stepDuration);

  return {
    step: estimatedStep % 256,
    beat: Math.floor(estimatedStep / 4) % 4,
    bar: Math.floor(estimatedStep / 16)
  };
}
```

**注意**:
- `"beat"`設定でも一定の頻度で送信されます
- ネットワーク帯域削減が必要な場合は`"bar"`を使用
- `"bar"`使用時は、上記の補間コードでスムーズなUI更新を実現できます

---

#### `status`

再生状態の変化

**トリガー**: `/playback/start`, `/playback/stop`, `/playback/pause`

**データ**:
```json
{
  "transport": "playing",
  "bpm": 120.0,
  "active_tracks": ["track_001", "track_002"]
}
```

**用途**:
- 再生/停止ボタンの状態更新
- アクティブTrackの表示

---

#### `error`

エラー通知

**トリガー**: Engine内部エラー

**データ**:
```json
{
  "code": "DESTINATION_ERROR",
  "message": "Failed to send OSC message to superdirt"
}
```

**用途**:
- エラー表示
- ログ記録

---

## 実装パターン

### 基本接続 (JavaScript)

```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

// 接続成功
eventSource.addEventListener('connected', (event) => {
  console.log('Connected to Oiduna');
});

// エラーハンドリング
eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);
  // 自動再接続は標準で実装されています
};

// 接続終了
window.addEventListener('beforeunload', () => {
  eventSource.close();
});
```

---

### 全イベント監視

```javascript
const eventSource = new EventSource('http://localhost:57122/stream');

const eventHandlers = {
  // クライアント
  client_connected: (data) => console.log('Client joined:', data),
  client_disconnected: (data) => console.log('Client left:', data),

  // Track
  track_created: (data) => addTrack(data),
  track_updated: (data) => updateTrack(data),
  track_deleted: (data) => removeTrack(data),

  // Pattern
  pattern_created: (data) => addPattern(data),
  pattern_updated: (data) => updatePattern(data),
  pattern_deleted: (data) => removePattern(data),

  // Environment
  environment_updated: (data) => updateEnvironment(data),

  // System
  heartbeat: (data) => console.log('Heartbeat:', data.timestamp),
  error: (data) => showError(data),
};

// 全てのハンドラーを登録
for (const [eventType, handler] of Object.entries(eventHandlers)) {
  eventSource.addEventListener(eventType, (event) => {
    const data = JSON.parse(event.data);
    handler(data);
  });
}
```

---

### 他人の変更を警告

```javascript
const myClientId = 'alice_001';  // 自分のID

function warnIfOtherUser(eventType, data) {
  if (data.client_id && data.client_id !== myClientId) {
    showWarning(`${eventType}: Modified by ${data.client_id}`);
    return true;
  }
  return false;
}

eventSource.addEventListener('track_updated', (event) => {
  const data = JSON.parse(event.data);
  if (warnIfOtherUser('track_updated', data)) {
    // 自動リロードやロック表示など
    highlightModifiedTrack(data.track_id);
  }
});

eventSource.addEventListener('pattern_updated', (event) => {
  const data = JSON.parse(event.data);
  if (warnIfOtherUser('pattern_updated', data)) {
    highlightModifiedPattern(data.pattern_id);
  }
});
```

---

### 再接続ロジック

```javascript
let eventSource;
let reconnectAttempts = 0;
const MAX_RECONNECTS = 10;

function connect() {
  eventSource = new EventSource('http://localhost:57122/stream');

  eventSource.addEventListener('connected', () => {
    console.log('Connected');
    reconnectAttempts = 0;  // リセット
  });

  eventSource.onerror = () => {
    console.error('Connection lost');
    eventSource.close();

    // 指数バックオフで再接続
    if (reconnectAttempts < MAX_RECONNECTS) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
      reconnectAttempts++;
      console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`);
      setTimeout(connect, delay);
    } else {
      console.error('Max reconnection attempts reached');
      showPermanentError('Cannot connect to server');
    }
  };
}

connect();
```

---

### Python実装例

```python
import requests
import json

def stream_events(url):
    """SSEイベントをストリーミング"""
    response = requests.get(url, stream=True)

    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')

            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
            elif line.startswith('data:'):
                data = json.loads(line.split(':', 1)[1].strip())
                handle_event(event_type, data)

def handle_event(event_type, data):
    if event_type == 'track_created':
        print(f"New track: {data['track_id']}")
    elif event_type == 'pattern_updated':
        print(f"Pattern updated: {data['pattern_id']}")
    # ... more handlers

# 使用
stream_events('http://localhost:57122/stream')
```

---

## パフォーマンス考慮事項

### イベント頻度

| イベント | 頻度 | 注意 |
|---------|------|------|
| heartbeat | 15秒 | 常時 |
| position | 毎ステップ | 高頻度（256steps/pattern） |
| track_* | 低頻度 | ユーザー操作時のみ |
| pattern_* | 中頻度 | ライブコーディング中 |
| environment_* | 低頻度 | BPM変更時のみ |

### フィルタリング

不要なイベントは無視:

```javascript
// position イベントは無視（高頻度）
eventSource.addEventListener('position', () => {
  // 何もしない
});

// 必要なイベントだけ処理
eventSource.addEventListener('track_created', handleTrackCreated);
eventSource.addEventListener('pattern_updated', handlePatternUpdated);
```

### バッチ処理

複数イベントをまとめて処理:

```javascript
let pendingUpdates = [];
let updateTimer = null;

eventSource.addEventListener('pattern_updated', (event) => {
  const data = JSON.parse(event.data);
  pendingUpdates.push(data);

  // 100ms後にまとめて処理
  clearTimeout(updateTimer);
  updateTimer = setTimeout(() => {
    processBatchUpdates(pendingUpdates);
    pendingUpdates = [];
  }, 100);
});
```

---

## トラブルシューティング

### 接続が切れる

**原因**: ネットワーク問題、タイムアウト

**解決**:
- 自動再接続実装（上記例参照）
- Heartbeat監視でタイムアウト検出

### イベントが届かない

**原因**: クライアント側の問題、イベントハンドラー未登録

**確認**:
```bash
# curlで確認
curl -N http://localhost:57122/stream

# イベントが流れるか確認
```

### 高CPU使用率

**原因**: `position`イベントの処理

**解決**:
- positionイベントを無視
- サンプリング（10イベント中1イベントのみ処理）

```javascript
let positionCounter = 0;
eventSource.addEventListener('position', (event) => {
  positionCounter++;
  if (positionCounter % 10 === 0) {
    // 10回に1回だけ処理
    updatePosition(JSON.parse(event.data));
  }
});
```

---

## 次のステップ

- [Migration Guide](./MIGRATION_GUIDE.md) - 旧APIからの移行
- [Live Coding Examples](./LIVE_CODING_EXAMPLES.md) - 実用例
- [API Reference](http://localhost:57122/docs) - 完全なAPIドキュメント
