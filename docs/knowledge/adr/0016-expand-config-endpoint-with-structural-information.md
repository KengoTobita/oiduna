# ADR-0016: GET /config エンドポイントの構造情報拡張

**Status**: Accepted
**Date**: 2026-03-02
**Author**: Oiduna Development Team

---

## Context

Oidunaは `GET /config` エンドポイントでEnvironment設定（BPM、position_update_interval等）を提供していたが、クライアントがOidunaの構造を理解するために必要な情報が不足していた。

### 現状の課題

1. **初期化時の構造情報不足**:
   - クライアントは接続時に、他のクライアントやDestinationの状態を把握できない
   - Trackを作成する際、利用可能なDestinationを事前確認できない
   - 接続しているクライアント一覧を取得する手段がない

2. **エンドポイントの責任分離不足**:
   - `GET /session/state` は認証必須で、演奏状態（Tracks/Patterns）を返す
   - 構造的情報（clients/destinations）を取得する専用エンドポイントがない
   - 認証前に知りたい情報と、認証後に知りたい情報が混在

3. **クライアント実装の煩雑さ**:
   - 初期化時に複数のエンドポイントを呼び出す必要がある
   - Destination情報がないため、Track作成時にエラーが発生する可能性

### 設計要件

- クライアントが初期化時に必要な構造情報を一度に取得できる
- 認証不要で構造情報を参照可能（プライバシーに配慮）
- 既存の `GET /session/state` との責任分離を明確化
- シンプルな実装（過剰設計を避ける）

---

## Decision

`GET /config` エンドポイントを拡張し、Oidunaの構造情報（clients、destinations）を返すようにする。

### 返却情報

#### 既存フィールド
- `environment`: BPM、position_update_interval等の設定
- `loop_steps`: ループステップ数（256固定）
- `api_version`: APIバージョン

#### 新規フィールド
- **`clients`**: 接続中のクライアント一覧（最小限の情報）
- **`destinations`**: 利用可能なDestination一覧（完全な設定情報）

### クライアント情報の公開範囲

**公開する情報**:
```json
{
  "client_id": "alice_001",
  "client_name": "Alice's LiveCoding Session",
  "distribution": "alice_local"
}
```

**公開しない情報**:
- `client_token`: セキュリティ上、非公開
- `metadata`: プライバシー保護のため非公開

### Destination情報の公開範囲

**完全な設定情報を公開**:
```json
{
  "destination_id": "superdirt_default",
  "destination_type": "osc",
  "target_host": "127.0.0.1",
  "target_port": 57120,
  "metadata": {}
}
```

理由: Track作成時に正確なdestination_idを指定する必要があるため

---

## Implementation

### API仕様

#### GET /config (拡張後)

**Request**:
```http
GET /config
```

**Response**:
```json
{
  "environment": {
    "bpm": 120.0,
    "metadata": {},
    "position_update_interval": "beat"
  },
  "loop_steps": 256,
  "api_version": "1.0",
  "clients": [
    {
      "client_id": "alice_001",
      "client_name": "Alice's LiveCoding Session",
      "distribution": "alice_local"
    },
    {
      "client_id": "bob_002",
      "client_name": "Bob's Session",
      "distribution": "bob_local"
    }
  ],
  "destinations": [
    {
      "destination_id": "superdirt_default",
      "destination_type": "osc",
      "target_host": "127.0.0.1",
      "target_port": 57120,
      "metadata": {}
    },
    {
      "destination_id": "midi_synth",
      "destination_type": "midi",
      "port_name": "IAC Driver Bus 1",
      "metadata": {}
    }
  ]
}
```

### 変更ファイル

- **packages/oiduna_api/routes/session.py**:
  - `GET /config` エンドポイントを拡張
  - `container.clients.list()` から client 情報を取得
  - `container.session.destinations.values()` から destination 情報を取得

### クライアント実装例

```javascript
// 初期化時にconfig取得
const config = await fetch('/config').then(r => r.json());

// 利用可能なDestinationを確認
console.log('Available destinations:', config.destinations.map(d => d.destination_id));

// 他のクライアントを確認
console.log('Connected clients:', config.clients.map(c => c.client_name));

// Track作成時にDestinationを指定
const createTrackRequest = {
  track_name: "kick",
  destination_id: config.destinations[0].destination_id  // superdirt_default
};
```

---

## Consequences

### Positive

- ✅ **初期化の簡素化**: 1回のAPIコールで必要な構造情報を取得
- ✅ **エラー削減**: Destination IDを事前確認できるため、Track作成時のエラーが減少
- ✅ **責任分離の明確化**:
  - `GET /config`: 構造情報（認証不要）
  - `GET /session/state`: 演奏状態（認証必要）
- ✅ **プライバシー保護**: tokenやmetadataを公開しない

### Negative

- ⚠️ **API表面積の増加**: 返却フィールドが増加
- ⚠️ **ドキュメント更新負荷**: API_REFERENCEの更新が必要

### Neutral

- 🔄 **認証不要のトレードオフ**: 構造情報は公開されるが、機密情報は含まない
- 🔄 **clients情報の用途限定**: 表示用途が主で、操作用途ではない

---

## Alternatives Considered

### Alternative 1: 個別エンドポイント（GET /clients, GET /destinations）

**Pros**:
- RESTful
- 細かい制御が可能

**Cons**:
- 初期化時に複数APIコール必要
- ネットワークラウンドトリップの増加

**Rejected理由**: クライアント初期化のユースケースでは、一度に取得する方が効率的

### Alternative 2: GET /session/state に統合

**Pros**:
- エンドポイント数が増えない

**Cons**:
- 認証が必要になる（初期化前に取得できない）
- 構造情報と演奏状態が混在

**Rejected理由**: 責任分離の原則に反する

### Alternative 3: clients情報にtokenも含める

**Pros**:
- 完全な情報を提供

**Cons**:
- セキュリティリスク
- 他のクライアントのtokenを第三者が取得可能

**Rejected理由**: セキュリティ上、tokenは秘匿すべき

---

## Testing

### テストケース

1. **基本構造確認**:
   ```python
   response = client.get("/config")
   assert "clients" in response.json()
   assert "destinations" in response.json()
   ```

2. **クライアント情報の形式**:
   ```python
   clients = response.json()["clients"]
   assert all("client_id" in c for c in clients)
   assert all("client_token" not in c for c in clients)  # tokenは非公開
   ```

3. **Destination情報の形式**:
   ```python
   destinations = response.json()["destinations"]
   assert all("destination_id" in d for d in destinations)
   ```

4. **認証不要の確認**:
   ```python
   # 認証ヘッダーなしでアクセス可能
   response = client.get("/config")
   assert response.status_code == 200
   ```

### テスト結果

- ✅ 全テスト成功: **190 tests passed, 1 skipped**
- ✅ 既存機能への影響なし
- ✅ 新規テスト4件追加（TestConfigEndpoint）

---

## Documentation Updates

### 必須更新ドキュメント

1. **docs/API_REFERENCE.md**:
   - GET /config の clients, destinations フィールド追加
   - クライアント実装例の更新

2. **docs/architecture/external-interface.md** (必要に応じて):
   - 構造情報取得のフロー追加

---

## References

- [ADR-0015: Configurable SSE Position Update Frequency](./0015-configurable-sse-position-update-frequency.md)
- [ADR-0012: Package Architecture (Layered Design)](./0012-package-architecture-layered-design.md)
- [API_REFERENCE.md](../../API_REFERENCE.md)

---

**Updated**: 2026-03-02
**Related ADRs**: ADR-0015, ADR-0012
**Test Status**: ✅ 190 tests passed, 1 skipped
