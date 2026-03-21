# ADR 0013: Distribution-Oiduna Terminology Mapping Strategy

**Status**: Accepted

**Date**: 2026-03-21

**Deciders**: tobita, Claude Code

---

## Context

### Background

DistributionとOidunaの開発において、同じ概念に対して異なる用語が使用されており、統一が必要になりました。

**MARS（Distribution）の用語**:
- **Start**: ノートの開始位置
- **Pitch**: 音高（度数またはMIDI番号）
- **Length**: ノートの長さ（ステップ数）
- **Velocity**: 音の強さ（0.0-1.0）

**Oidunaの用語**:
- **step**: イベントの開始位置（0-255）
- **note**: 音高（MIDI番号、params内）
- **velocity** (MIDI) / **gain** (SuperDirt): 音の強さ（params内、送信先依存）
- **duration_ms** (MIDI) / **sustain** (SuperDirt): 音の長さ（params内、送信先依存）

### Problem

1. **用語の不一致**: 同じ概念に異なる名前を使用（Start vs step）
2. **送信先依存性**: OidunaのparamsはMIDI/SuperDirtで異なる用語を使用
3. **ドキュメントの不足**: 用語変換のガイドラインが明確でない
4. **実装の影響範囲**: どちら側が変換を担当すべきか不明確

### Constraints

- **Oidunaは既に実装完了**: 513テスト全パス、用語変更はコスト大
- **Distribution-Agnostic設計**: Oidunaは特定のDistributionに依存しない
- **送信先依存のparams**: MIDI/SuperDirtで異なるパラメータ名が必要
- **MARS側は柔軟**: TypeScript実装中、コンパイラで変換可能

---

## Decision

### 用語統一方針: **Oiduna用語を基準とし、Distribution側で変換**

Oidunaの用語体系を基準とし、Distribution（MARS等）側のコンパイラで用語変換を行う。

#### 1. Oiduna側: 現状維持（変更なし）

**構造レベル**:
- `step`: イベント開始位置（0-255）
- `cycle`: サイクル位置（float）
- `destination_id`: 送信先ID
- `params`: 送信先依存の辞書

**paramsレベル（送信先依存）**:

MIDI送信先:
```python
params = {
    "note": 60,          # 音高
    "velocity": 100,     # 強さ（0-127）
    "duration_ms": 250,  # 長さ（ミリ秒）
    "channel": 0
}
```

SuperDirt送信先:
```python
params = {
    "s": "bd",           # サウンド名
    "gain": 0.8,         # 強さ（0.0-1.0）
    "sustain": 0.25,     # 持続時間（cycles）
    "orbit": 0
}
```

#### 2. Distribution側: コンパイル時に用語変換

**MARS内部では直感的な用語を使用**:
```typescript
interface MarsInternalNote {
  Start: number;      // 開始位置
  Pitch: number;      // 音高
  Length: number;     // 長さ
  Velocity: number;   // 強さ
}
```

**Oidunaへの変換（OidunaMapper）**:
```typescript
function mapToScheduledMessage(
  note: MarsInternalNote,
  destinationId: string,
  bpm: number
): ScheduledMessage {
  const stepDurationMs = 60000 / bpm / 4;

  if (destinationId === 'superdirt') {
    return {
      destination_id: 'superdirt',
      step: note.Start,              // ← Start → step
      cycle: note.Start / 64.0,
      params: {
        s: 'bd',
        gain: note.Velocity,         // ← Velocity → gain
        sustain: note.Length / 64.0  // ← Length → sustain (cycles)
      }
    };
  } else if (destinationId.startsWith('midi_')) {
    return {
      destination_id: destinationId,
      step: note.Start,              // ← Start → step
      cycle: note.Start / 64.0,
      params: {
        note: note.Pitch,            // ← Pitch → note
        velocity: Math.round(note.Velocity * 127),  // ← Velocity → velocity
        duration_ms: note.Length * stepDurationMs,  // ← Length → duration_ms
        channel: 0
      }
    };
  }

  throw new Error(`Unknown destination: ${destinationId}`);
}
```

#### 3. ドキュメントに対応表を明記

以下のドキュメントに用語対応表を追記:

1. **DISTRIBUTION_GUIDE.md**: Distribution開発者向けマッピングガイド
2. **TERMINOLOGY.md**: 用語集にDistribution用語との対応を追記
3. **API_REFERENCE.md**: API利用者向けクイックリファレンス

---

## Rationale

### なぜOiduna用語を基準にするのか

1. **既に実装完了**
   - 513テスト全パス、型定義完了
   - step, note, velocity, duration_msは音楽的に自然

2. **Destination-Agnostic設計の維持**
   - `params: dict[str, Any]`は送信先依存で正しい設計
   - MIDI仕様（note, velocity）とSuperDirt仕様（s, gain）を尊重

3. **拡張性の確保**
   - 将来の他のDistribution（TidalCycles風、Sonic Pi風など）も同じAPIを使用可能
   - カスタム送信先も追加可能

### なぜDistribution側で変換するのか

1. **責任の明確な分離**
   - Oiduna: 低レベルプレイヤー（送信先非依存）
   - Distribution: 高レベルDSL（音楽的抽象化）

2. **実装の柔軟性**
   - Distribution側はコンパイラで変換ロジックを集約
   - Oidunaはシンプルに保たれる

3. **変更の影響範囲**
   - Distribution側の変更はDistribution内で完結
   - Oidunaの変更は全Distributionに影響

---

## Consequences

### Positive

1. **実装コードへの影響ゼロ**
   - Oidunaのコード変更不要
   - 513テスト全パス維持

2. **明確な責任分離**
   - Oiduna: 用語体系を持つ、変換しない
   - Distribution: 用語変換を担当

3. **ドキュメントの充実**
   - Distribution開発者が即座に参照可能
   - 実装例（TypeScript/Python）を提供

4. **将来の拡張性**
   - 他のDistributionも同じパターンを採用可能
   - カスタム送信先も同様の方式で対応

### Negative

1. **Distribution側の実装負担**
   - 各Distributionが用語変換を実装する必要
   - ただし、実装例とドキュメントで軽減

2. **用語の二重管理**
   - Distribution用語とOiduna用語の両方を理解する必要
   - ドキュメントの対応表で軽減

### Risks

1. **用語変換ミス**
   - **軽減策**: TypeScriptの型チェック、単体テスト

2. **ドキュメントの陳腐化**
   - **軽減策**: 用語変更時はドキュメントも同時更新

---

## Alternatives Considered

### 代替案A: Oiduna用語をMARSに合わせる

**内容**: Oidunaのstepをstartに変更、paramsもMARS用語に統一

**長所**:
- MARSユーザーにとって直感的

**短所**:
- 既存実装の全面変更が必要（513テスト修正）
- MIDI/SuperDirt仕様との乖離
- 他のDistributionへの押し付け

**判断**: ❌ 採用しない（実装コスト大、拡張性低）

### 代替案B: 両方の用語をサポート

**内容**: Oiduna APIがstart/stepの両方を受け付ける

**長所**:
- Distribution側の変換が不要

**短所**:
- Oidunaの複雑化
- エイリアス管理のオーバーヘッド
- 送信先依存のparamsには適用不可

**判断**: ❌ 採用しない（Destination-Agnostic設計に反する）

### 代替案C: 中間フォーマットを定義

**内容**: Distribution用語とOiduna用語の中間フォーマットを定義

**長所**:
- 両者から独立

**短所**:
- 複雑性の増加
- 二重変換のオーバーヘッド
- 実装済みのOiduna用語を捨てる

**判断**: ❌ 採用しない（不要な複雑性）

---

## Implementation

### Phase 1: ドキュメント整備（完了）

- [x] DISTRIBUTION_GUIDE.mdに用語対応表を追記
- [x] TERMINOLOGY.mdに用語マッピング説明を追記
- [x] API_REFERENCE.mdに用語対応セクション追加

**コミット**: `01f09b9` - docs: add Distribution-Oiduna terminology mapping guide

### Phase 2: MARS側実装（進行中）

- [ ] OidunaMapperクラスの実装
- [ ] 用語変換ロジックの単体テスト
- [ ] 統合テスト（MARS DSL → Oiduna ScheduledMessage）

### Phase 3: 他のDistributionへの展開（将来）

- [ ] TidalCycles風Distributionでの適用例
- [ ] Sonic Pi風Distributionでの適用例

---

## Related ADRs

- [ADR 0007: Destination-Agnostic Core](./0007-destination-agnostic-core-superdirt-migration.md) - Destination-Agnostic設計の基盤
- [ADR 0012: Package Architecture](./0012-package-architecture-layered-design.md) - ScheduledMessage形式の定義

---

## References

- [DISTRIBUTION_GUIDE.md](../../DISTRIBUTION_GUIDE.md#distribution用語とoiduna用語の対応)
- [TERMINOLOGY.md](../../TERMINOLOGY.md#distribution用語とparams用語の対応)
- [API_REFERENCE.md](../../API_REFERENCE.md#distribution用語とoiduna-api用語の対応)
- [scheduler_models.py](../../../../packages/oiduna_scheduler/scheduler_models.py) - ScheduledMessage定義

---

**Last Updated**: 2026-03-21
**Author**: tobita, Claude Code
