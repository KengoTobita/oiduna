# ADR-0015: SSE Position Update Frequencyの設定可能化

**Status**: Accepted
**Date**: 2026-03-02
**Author**: Oiduna Development Team

---

## Context

Oidunaは、リアルタイム再生位置をSSE（Server-Sent Events）の`position`イベントで配信している。従来の実装では、**4ステップごと（1beatごと）**に固定されており、クライアント側のネットワーク負荷やCPU使用率に影響を与える可能性があった。

### 現状の課題

1. **固定頻度による非効率性**:
   - 4ステップごと（1beatごと）の配信が、一部のクライアントには過剰
   - BPM 120の場合、毎秒2イベント発生（120 BPM ÷ 60 秒 × 4 beats）
   - ネットワーク帯域とクライアントCPUを不必要に消費

2. **クライアント側のユースケース多様性**:
   - **高頻度要求**: リアルタイムビジュアライゼーション（1beatごと必要）
   - **低頻度要求**: セクション切り替え表示（1barごとで十分）

3. **補間可能性**:
   - クライアント側でBPMが既知であれば、1barごとの更新でも中間位置を推定可能
   - 高精度が不要な用途では、ネットワーク負荷を1/4に削減できる

### 設計要件

- クライアントが必要に応じて頻度を選択可能にする
- デフォルト動作は変更しない（後方互換性）
- リアルタイムに設定変更を反映する

---

## Decision

SSE `position`イベントの送信頻度を設定可能にする。

### 設定値

- **`"beat"`**: 4ステップごと（1beatごと）— **デフォルト**
- **`"bar"`**: 16ステップごと（1barごと）— ネットワーク負荷1/4削減

### 実装方針

1. **Environmentモデルに設定フィールド追加**:
   ```python
   position_update_interval: Literal["beat", "bar"] = "beat"
   ```

2. **RuntimeStateに設定を保持**:
   - LoopEngineが動的に頻度を判定

3. **新規APIエンドポイント追加**:
   - `GET /config`: 設定取得（認証不要）
   - `PATCH /session/environment`: 設定変更（認証必要）

4. **ループエンジン側の動的判定**:
   ```python
   interval = 16 if self.state.position_update_interval == "bar" else 4
   if current_step % interval == 0:
       await self._publisher.send_position(...)
   ```

---

## Consequences

### Positive

- ✅ **ネットワーク負荷削減**: `"bar"`設定で75%削減
- ✅ **クライアントCPU削減**: イベント処理頻度が1/4に
- ✅ **柔軟性向上**: ユースケースに応じた最適化が可能
- ✅ **後方互換性**: デフォルト`"beat"`で既存動作を維持
- ✅ **リアルタイム変更**: 再起動不要で設定変更可能

### Negative

- ⚠️ **API複雑化**: 新規パラメータとエンドポイントの追加
- ⚠️ **ドキュメント更新負荷**: API_REFERENCE、SSE_EVENTS等の更新が必要

### Neutral

- 🔄 **クライアント側の補間実装推奨**: `"bar"`設定時は中間位置を推定
- 🔄 **設定の永続化**: Environmentとして保存されるが、SessionContainer依存

---

## Alternatives Considered

### Alternative 1: 固定頻度維持（現状維持）

**Pros**:
- 実装変更不要
- シンプルな動作

**Cons**:
- 一部クライアントで不必要な負荷
- ユースケース多様性に対応できない

**Rejected理由**: ネットワーク負荷削減のニーズが存在し、実装コストが低い

### Alternative 2: クライアント側フィルタリング

**Pros**:
- サーバー側変更不要

**Cons**:
- ネットワーク帯域削減にならない
- 全クライアントがフィルタリングロジックを実装する必要

**Rejected理由**: ネットワーク帯域削減が主目的のため、サーバー側での制御が必要

### Alternative 3: 任意ステップ数指定（例: 1-64ステップ）

**Pros**:
- 極めて柔軟

**Cons**:
- 設定の複雑化
- 音楽的な境界（beat/bar）との不整合リスク

**Rejected理由**: 音楽的に意味のある境界（beat/bar）で十分

---

## Implementation

### 変更ファイル

#### 1. モデル層
- `packages/oiduna_models/environment.py`
  - `position_update_interval: Literal["beat", "bar"]` 追加

#### 2. セッション管理層
- `packages/oiduna_session/managers/environment_manager.py`
  - `update()` メソッドに `position_update_interval` パラメータ追加

#### 3. ループエンジン層
- `packages/oiduna_loop/state/runtime_state.py`
  - `position_update_interval: str = "beat"` フィールド追加
- `packages/oiduna_loop/engine/loop_engine.py`
  - `_publish_periodic_updates()` で動的頻度判定

#### 4. API層
- `packages/oiduna_api/routes/session.py`
  - `GET /config`: 新規エンドポイント（認証不要）
  - `PATCH /session/environment`: `position_update_interval` 対応

### API仕様

#### GET /config (新規)
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
  "api_version": "1.0"
}
```

#### PATCH /session/environment (拡張)
```http
PATCH /session/environment
Headers:
  X-Client-ID: alice_001
  X-Client-Token: <token>
Body:
{
  "position_update_interval": "bar"
}
```

### クライアント側推奨実装

```javascript
// 設定取得
const config = await fetch('/config').then(r => r.json());
const interval = config.environment.position_update_interval;

// SSE接続
const eventSource = new EventSource('/stream');
let lastPosition = { step: 0, beat: 0, bar: 0 };
let lastUpdateTime = Date.now();

eventSource.addEventListener('position', (e) => {
  lastPosition = JSON.parse(e.data);
  lastUpdateTime = Date.now();
});

// 補間（"bar"設定時に有用）
function getInterpolatedPosition() {
  const elapsed = (Date.now() - lastUpdateTime) / 1000;
  const stepDuration = 60 / (config.environment.bpm * 4);
  const estimatedStep = lastPosition.step + Math.floor(elapsed / stepDuration);

  return {
    step: estimatedStep % 256,
    beat: Math.floor(estimatedStep / 4) % 4,
    bar: Math.floor(estimatedStep / 16)
  };
}
```

### 検証基準

- ✅ `GET /config` が設定を正常に返す
- ✅ `PATCH /session/environment` で設定変更可能
- ✅ `"beat"` 設定時: 4ステップごとにpositionイベント発生
- ✅ `"bar"` 設定時: 16ステップごとにpositionイベント発生
- ✅ 全既存テストがパス（161 tests）
- ✅ デフォルト動作が`"beat"`で維持

---

## Documentation Updates

### 必須更新ドキュメント

1. **API_REFERENCE.md**:
   - `GET /config` エンドポイント追加
   - `PATCH /session/environment` に `position_update_interval` パラメータ追加
   - SSE `position` イベント頻度の説明更新

2. **SSE_EVENTS.md**:
   - `position` イベントの頻度設定について追記
   - クライアント側補間実装例の追加

3. **docs/architecture/external-interface.md**:
   - 新規エンドポイント `GET /config` の追加
   - Environment設定の外部インターフェース更新

4. **docs/architecture/layer-1-api.md**:
   - APIレイヤーの新機能追加
   - セッション管理機能の拡張

---

## References

- [ADR-0012: Package Architecture (Layered Design)](./0012-package-architecture-layered-design.md)
- [API_REFERENCE.md](../../API_REFERENCE.md)
- [SSE_EVENTS.md](../../SSE_EVENTS.md)
- [Layer 1: API Layer](../../architecture/layer-1-api.md)

---

**Updated**: 2026-03-02
**Related ADRs**: ADR-0012
**Test Status**: ✅ 161 tests passed
