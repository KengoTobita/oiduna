# Optimistic Locking for Session Sync

## 概要

Oidunaは楽観的ロック（Optimistic Locking）を使用して、複数クライアントによる同時編集時の操作の原子性を保証します。

## 問題

従来の実装では、`/playback/sync`エンドポイントが**後勝ち（last-write-wins）**で動作していました:

```
Client C: C1→C2→C3→C4 (一連の操作)
Client D: D1→D2→D3→D4 (一連の操作)

❌ 問題: C1→C2→D1→C3→D2→D3→D4→C4 (インターリーブ、キメラ)
```

このようなインターリーブが発生すると、意図しない状態になる可能性がありました。

## 解決方法: Session Version

### データモデル

`Session`モデルにバージョン管理フィールドを追加:

```python
class Session(BaseModel):
    version: int = 0  # 各syncで+1
    last_modified_by: Optional[str] = None  # 最終更新クライアントID
    last_modified_at: Optional[datetime] = None  # 最終更新時刻(UTC)
    # ... その他のフィールド
```

### /sync エンドポイント

クライアントは`X-Session-Version`ヘッダーで期待しているバージョンを送信:

```http
POST /playback/sync
Headers:
  X-Client-ID: alice
  X-Client-Token: <token>
  X-Session-Version: 5
```

**サーバー側の処理**:

1. バージョンチェック
   ```python
   if container.session.version != x_session_version:
       raise HTTPException(status_code=409, detail={
           "error": "session_conflict",
           "message": f"Session was modified by {last_modified_by}",
           "current_version": current_version,
           "your_version": x_session_version
       })
   ```

2. 成功時: バージョンインクリメント
   ```python
   container.session.version += 1
   container.session.last_modified_by = x_client_id
   container.session.last_modified_at = datetime.now(timezone.utc)
   ```

## 動作例

### 成功ケース

```
初期状態: version=5

[Client C]
1. GET /session/state → version=5を記憶
2. ローカル編集: C1→C2→C3→C4
3. POST /sync (version=5)
   → サーバーversion=5と一致 ✅
   → C1〜C4適用、version→6

[Client D]
1. GET /session/state → version=6を記憶
2. ローカル編集: D1→D2→D3→D4
3. POST /sync (version=6)
   → サーバーversion=6と一致 ✅
   → D1〜D4適用、version→7
```

### 競合ケース (409 Conflict)

```
初期状態: version=5

[Client C]
1. GET /session/state → version=5を記憶
2. ローカル編集
3. POST /sync (version=5) → 成功、version→6

[Client D]
1. GET /session/state → version=5を記憶 (Cと同じタイミング)
2. ローカル編集
3. POST /sync (version=5)
   → サーバーversion=6になってる ❌
   → 409 Conflict!

[Client D - リトライ]
4. GET /session/state → version=6を取得
5. Cの変更を確認
6. 必要なら調整してPOST /sync (version=6) → 成功
```

## クライアント実装例

### JavaScript/TypeScript

```typescript
// 1. 編集開始時にバージョン取得
const session = await fetch('/session/state', {
  headers: {
    'X-Client-ID': clientId,
    'X-Client-Token': token
  }
}).then(r => r.json())

const currentVersion = session.version

// 2. ローカル編集
// ...

// 3. Sync
const syncResponse = await fetch('/playback/sync', {
  method: 'POST',
  headers: {
    'X-Client-ID': clientId,
    'X-Client-Token': token,
    'X-Session-Version': currentVersion.toString()
  }
})

if (syncResponse.status === 409) {
  // 競合発生
  const error = await syncResponse.json()
  console.warn(`Conflict: ${error.detail.message}`)
  console.warn(`Current version: ${error.detail.current_version}`)

  // 最新を取得して再試行
  // ...
} else if (syncResponse.ok) {
  const data = await syncResponse.json()
  console.log(`Synced! New version: ${data.version}`)
}
```

### Python

```python
import requests

# 1. バージョン取得
resp = requests.get('http://localhost:57122/session/state', headers={
    'X-Client-ID': client_id,
    'X-Client-Token': token
})
session = resp.json()
current_version = session['version']

# 2. ローカル編集
# ...

# 3. Sync
resp = requests.post('http://localhost:57122/playback/sync', headers={
    'X-Client-ID': client_id,
    'X-Client-Token': token,
    'X-Session-Version': str(current_version)
})

if resp.status_code == 409:
    # 競合発生
    error = resp.json()['detail']
    print(f"Conflict: {error['message']}")
    print(f"Current: {error['current_version']}, Your: {error['your_version']}")
    # リトライロジック
    # ...
elif resp.ok:
    data = resp.json()
    print(f"Synced! New version: {data['version']}")
```

## バージョン要件

**⚠️ v3.0以降**: `X-Session-Version`ヘッダーは**必須**です。

省略した場合、`400 Bad Request`エラーが返されます:

```python
if x_session_version is None:
    raise HTTPException(
        status_code=400,
        detail="X-Session-Version header is required"
    )
```

**変更履歴**:
- **v2.x**: ヘッダー省略時は`0`として扱う（後方互換性）
- **v3.0**: ヘッダー必須化（ADR-0021）

**移行方法**: すべてのクライアントで`X-Session-Version`ヘッダーを送信してください。

## エンドポイント一覧

| エンドポイント | versionの扱い |
|---------------|--------------|
| `GET /config` | `session_version`を返す（認証不要） |
| `GET /session/state` | `version`, `last_modified_by`, `last_modified_at`を返す（認証必要） |
| `POST /playback/sync` | `X-Session-Version`ヘッダーでチェック、成功時にインクリメント |

## テスト

テストは`tests/integration/test_loop_engine_integration.py`に追加されています:

- `test_sync_version_increment` - バージョンインクリメントの確認
- `test_sync_version_conflict` - 競合検出(409)の確認
- `test_sync_concurrent_operations_atomicity` - 原子性の確認

実行:
```bash
uv run pytest tests/integration/test_loop_engine_integration.py::TestPlaybackCommandIntegration -v
```

## まとめ

- **原子性**: 一連の操作（C1→C2→C3→C4）が途中で割り込まれない
- **後勝ち**: バージョンが新しい方が勝つ（従来通り）
- **衝突検出**: 409 Conflictで通知
- **人間判断**: クライアント同士で相談して解決

この方式により、複数人での同時編集時もデータ整合性が保たれます。
