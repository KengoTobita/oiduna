# ADR-018: Optimistic Locking for Session Sync

## Status

**Accepted** - 2026-03-02

## Context

Oidunaの複数クライアント環境において、`/playback/sync`エンドポイントでの同時編集時に操作の原子性が保証されていなかった。

### 問題: 操作のインターリーブ

従来の実装では、各クライアントが独立してSession全体を更新し、最後に`/sync`を呼ぶと**後勝ち（last-write-wins）**で反映されていた:

```
Client C: C1→C2→C3→C4 (kick trackの一連の編集)
Client D: D1→D2→D3→D4 (snare trackの一連の編集)

❌ 問題: C1→C2→D1→C3→D2→D3→D4→C4 のようなインターリーブが発生
```

このような操作のインターリーブにより、以下の問題が発生する可能性があった:

1. **意図しないキメラ状態**: Client Cの編集途中でClient Dの編集が混入
2. **データ整合性の破綻**: 一連の操作が原子的に適用されないことで、中間状態が残る
3. **予測不可能な結果**: 同時編集時の結果が不定

### ユースケース

```
ライブコーディングセッション:
- Alice: kick trackを編集中 (pattern追加→event追加→BPM変更)
- Bob: snare trackを編集中 (base_params変更→pattern activate)
→ 両者がほぼ同時に/syncを呼ぶ
→ どちらかの編集が中途半端に反映される可能性
```

## Decision

**楽観的ロック（Optimistic Locking）を実装し、Session単位でバージョン管理を行う**

### 実装内容

#### 1. Session Modelの拡張

```python
class Session(BaseModel):
    version: int = 0
    last_modified_by: Optional[str] = None
    last_modified_at: Optional[datetime] = None

    environment: Environment = Field(...)
    destinations: dict[str, DestinationConfig] = Field(...)
    clients: dict[str, ClientInfo] = Field(...)
    tracks: dict[str, Track] = Field(...)
```

**フィールド**:
- `version`: 各sync成功時にインクリメント（0から始まる）
- `last_modified_by`: 最後にsyncを成功させたクライアントID
- `last_modified_at`: 最終更新時刻（UTC）

#### 2. /sync エンドポイントの変更

**リクエスト**:
```http
POST /playback/sync
Headers:
  X-Client-ID: alice
  X-Client-Token: <token>
  X-Session-Version: 5  # ← 新規追加
```

**サーバー側処理**:
```python
# Version Check
if container.session.version != x_session_version:
    raise HTTPException(status_code=409, detail={
        "error": "session_conflict",
        "message": f"Session was modified by {last_modified_by}",
        "current_version": current_version,
        "your_version": x_session_version,
        "last_modified_at": last_modified_at
    })

# Apply changes atomically
batch = SessionCompiler.compile(container.session)
engine._handle_session(payload)

# Increment version on success
container.session.version += 1
container.session.last_modified_by = x_client_id
container.session.last_modified_at = datetime.now(timezone.utc)
```

#### 3. 競合時の挙動

**Success (200 OK)**:
```json
{
  "status": "synced",
  "version": 6,
  "message_count": 42,
  "bpm": 120.0
}
```

**Conflict (409 Conflict)**:
```json
{
  "detail": {
    "error": "session_conflict",
    "message": "Session was modified by bob",
    "current_version": 6,
    "your_version": 5,
    "last_modified_at": "2026-03-02T10:30:00Z"
  }
}
```

## Consequences

### Positive

1. **原子性の保証**
   - 一連の操作（C1→C2→C3→C4）が途中で割り込まれない
   - トランザクション的な振る舞い

2. **後勝ちの維持**
   - バージョンが新しい方が勝つ（従来の動作を保持）
   - シンプルな競合解決ポリシー

3. **衝突検出**
   - 409 Conflictで明示的に通知
   - 誰が、いつ更新したかの情報を提供

4. **人間による解決**
   - クライアント同士が相談して調整
   - 自動マージの複雑さを避ける

5. **後方互換性**
   - `X-Session-Version`ヘッダー省略時は`0`として扱う
   - 古いクライアントも動作可能（競合検出なし）

### Negative

1. **クライアント実装の複雑化**
   - バージョン取得→記憶→送信のフローが必要
   - 409時のリトライロジック実装が必要

2. **粒度の粗さ**
   - Session全体でロック（Track単位ではない）
   - 別々のTrackを編集していても衝突する

3. **リトライコスト**
   - 衝突時は最新Session取得→再編集→再syncが必要
   - ネットワークラウンドトリップ増加

### Trade-offs

**Session-level vs Track-level versioning**:
- Session-level（採用）: シンプル、BPM変更などグローバル操作に対応
- Track-level（不採用）: 細かいが実装複雑、デッドロック対策必要

**Optimistic vs Pessimistic Locking**:
- Optimistic（採用）: 衝突が少ない場合に高速、実装がシンプル
- Pessimistic（不採用）: ロック管理が複雑、ライブコーディングのフローに合わない

**Auto-merge vs Manual resolution**:
- Manual（採用）: 予測可能、実装シンプル、人間判断を尊重
- Auto-merge（不採用）: CRDTなど実装が非常に複雑

## Implementation

### Files Modified

1. `packages/oiduna_models/session.py`
   - `version`, `last_modified_by`, `last_modified_at`フィールド追加

2. `packages/oiduna_api/routes/playback.py`
   - `/sync`エンドポイントにバージョンチェック実装
   - 409 Conflictレスポンス追加

3. `packages/oiduna_api/routes/session.py`
   - `GET /config`に`session_version`追加
   - `GET /session/state`でversion情報返却

### Tests Added

`tests/integration/test_loop_engine_integration.py`:
- `test_sync_version_increment`: バージョンインクリメント確認
- `test_sync_version_conflict`: 競合検出(409)確認
- `test_sync_concurrent_operations_atomicity`: 原子性確認

### Documentation

- `docs/OPTIMISTIC_LOCKING.md`: 楽観的ロックの仕組みとクライアント実装例
- `docs/API_REFERENCE.md`: 更新予定（`X-Session-Version`ヘッダーの説明）

## Future Work

1. **Track-level versioning**
   - 別々のTrackの同時編集を許可
   - より細かい粒度の競合検出

2. **Conflict resolution strategies**
   - 3-way merge support
   - Last-writer-wins以外のポリシー

3. **Optimistic locking for other operations**
   - Environment updates
   - Destination configuration

4. **Client-side version caching**
   - WebSocket経由でversion変更通知
   - クライアント側でのバージョン同期

## References

- [Optimistic Locking - Martin Fowler](https://martinfowler.com/eaaCatalog/optimisticOfflineLock.html)
- [HTTP ETag and Conditional Requests](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag)
- [Operational Transformation vs CRDT](https://www.inkandswitch.com/local-first/)

## Related ADRs

- ADR-010: Session Container Refactoring - Session構造の基盤
- ADR-017: IPC and Session Naming Standardization - Session層の命名規則
