# ADR 0009: Remove Incompatible Tracks API Router

**Status**: Accepted

**Date**: 2026-02-27

**Deciders**: tobita, Claude Code

---

## Context

ScheduledMessageBatch統合後、`packages/oiduna_api/routes/tracks.py`が旧アーキテクチャ（CompiledSession形式）に依存したまま残存していた。

### 背景

**ScheduledMessageBatch統合の影響**:
- `RuntimeState`から`tracks`と`sequences`属性が削除された
- `CompiledSession`形式が廃止され、フラットな`ScheduledMessageBatch`形式に統一
- `Track`と`EventSequence`オブジェクトが存在しなくなった

**tracks.pyの実装問題**:
```python
# GET /tracks endpoint (line 94-96)
eff = state.get_effective()  # ← get_effective()メソッドは存在しない
for track_id, track in eff.tracks.items():  # ← tracks属性は存在しない
    seq = eff.sequences.get(track_id)  # ← sequences属性は存在しない

# POST /tracks/{track_id}/mute endpoint (line 128)
engine._handle_mute({"track_id": track_id, "mute": req.muted})  # ← _handle_mute()は存在しない

# POST /tracks/{track_id}/solo endpoint (line 144)
engine._handle_solo({"track_id": track_id, "solo": req.solo})  # ← _handle_solo()は存在しない
```

### 問題の発見

ディスカッション中に以下の不整合が発見された：

1. **エンドポイントの動作不全**:
   - `GET /tracks` - AttributeError (state.get_effective()が存在しない)
   - `GET /tracks/{track_id}` - 同上
   - `POST /tracks/{track_id}/mute` - AttributeError (engine._handle_mute()が存在しない)
   - `POST /tracks/{track_id}/solo` - AttributeError (engine._handle_solo()が存在しない)

2. **アーキテクチャ不整合**:
   - tracks.pyが依存する`Track`と`EventSequence`データ構造が廃止済み
   - 現在のScheduledMessageBatch形式では「トラック」の概念が明示的に存在しない
   - `params.track_id`によるグループ化が可能だが、APIレベルでは未実装

3. **影響範囲**:
   - SSE `/stream`エンドポイントの`tracks`イベントも影響を受ける可能性
   - ドキュメント（REVIEW_JP.md）にも削除されたエンドポイントへの言及が残存

---

## Decision

**tracks.pyルーターを完全に削除する**

### 理由

1. **実行時エラーを排除**:
   - 存在しないメソッド呼び出しによる実行時エラーを防止
   - 誤ったAPI仕様を利用者に提示しない

2. **アーキテクチャの整合性を保つ**:
   - ScheduledMessageBatch形式に統一された現状に合致
   - 中途半端な互換層を維持しない（技術的負債の削減）

3. **将来の再設計に備える**:
   - トラック管理機能は将来的に必要
   - ScheduledMessageBatch対応の新設計で再実装する方針

### 削除したAPI

```http
GET    /tracks                  # トラック一覧
GET    /tracks/{track_id}       # トラック詳細
POST   /tracks/{track_id}/mute  # Mute設定
POST   /tracks/{track_id}/solo  # Solo設定
```

### 代替手段（現状）

トラック制御機能自体は`RuntimeState`に存在している：
- `RuntimeState.set_track_mute(track_id, muted)` - Mute設定
- `RuntimeState.set_track_solo(track_id, soloed)` - Solo設定
- `RuntimeState.filter_messages(messages)` - Mute/Soloフィルタリング

ただし、これらをHTTP API経由で呼び出す手段は削除された。

---

## Consequences

### Positive

1. **実行時安全性の向上**:
   - 存在しないメソッド呼び出しによるエラーが発生しなくなる
   - APIドキュメントと実装の不整合を排除

2. **コードベースの明確化**:
   - 動作しないコードを削除し、保守対象を削減（-150行）
   - ScheduledMessageBatch形式への統一が明確になる

3. **技術的負債の削減**:
   - 旧アーキテクチャへの依存を完全に削除
   - 将来の再設計時にレガシーコードとの互換性を考慮する必要がない

### Negative

1. **機能削減**:
   - トラック単位のMute/Solo操作がHTTP API経由で不可能になる
   - ライブコーディング時の細かい制御が制限される

2. **クライアント側の影響**:
   - MARS DSLや外部ツールが`/tracks`エンドポイントに依存していた場合、動作不全
   - （ただし、現状では動作していなかったため、実質的な影響は小さい）

3. **SSEイベントの不完全性**:
   - `/stream`の`tracks`イベントが不完全になる可能性
   - （要調査・修正）

### Mitigation

#### 短期（Phase 2）
- ドキュメント修正（REVIEW_JP.md等）
- 必要に応じて`/stream`のtracksイベント処理を修正

#### 中期（Phase 3-4）
- ScheduledMessageBatch対応のトラック管理API設計
- 部分更新API（`PATCH /playback/messages`等）と統合検討

#### 長期（将来）
新しいトラック管理API設計案：
```http
# オプション1: メッセージ単位の部分更新
PATCH /playback/messages?track_id=bd&param=gain&value=0.8

# オプション2: トラック情報の取得（track_idベース）
GET /playback/tracks?track_id=bd

# オプション3: RuntimeState直接操作
POST /playback/tracks/{track_id}/mute
POST /playback/tracks/{track_id}/solo
```

---

## Related ADRs

- [ADR 0007: Destination-Agnostic Core Architecture](0007-destination-agnostic-core-superdirt-migration.md) - ScheduledMessageBatch統合
- [ADR 0008: Code Quality Refactoring Strategy](0008-code-quality-refactoring-strategy.md) - 品質向上の一環

---

## References

- Issue: ScheduledMessageBatch統合後のアーキテクチャ不整合発見
- PR: refactor: remove broken tracks.py router (commit be40d93)
- Discussion: "oidunaの理解のためのディスカッション - /playback/session部分更新について"
