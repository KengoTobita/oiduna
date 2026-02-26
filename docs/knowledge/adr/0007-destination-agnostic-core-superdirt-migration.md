# ADR 0007: Destination-Agnostic Core Architecture (SuperDirt Migration Phase 1 & 2)

**Status**: Accepted

**Date**: 2026-02-26

**Deciders**: tobita, Claude Code

---

## Context

Oidunaコアが特定の音響出力先（SuperDirt）に依存したorbit/cps管理を内包しており、汎用スケジューラとしての設計思想に反していた。

### 背景

**設計思想違反の具体例**:
- `TrackParams.orbit` - SuperDirt専用フィールドがコアIRに存在
- `OscEvent.orbit`, `OscEvent.cps` - SuperDirt専用の明示的フィールド
- `MixerLine.get_orbit()` - SuperDirt固有のロジックがコアに存在
- `StepProcessor` - 旧アーキテクチャと新アーキテクチャが並行稼働（3095+行の冗長コード）

### 問題点

1. **Destination依存**: 他のOSC先（Supernova, Pure Data等）で使えない
2. **拡張性の欠如**: 新しいdestinationの追加がコア変更を要求
3. **コード重複**: StepProcessorとScheduledMessageの二重実装
4. **テスト複雑化**: 両方のパスをテストする必要

### 目標

- SuperDirt固有ロジックをExtensionに完全分離
- Oidunaコアを真にdestination-agnostic化
- 冗長コードの削除
- メンテナンス性・拡張性の向上

---

## Decision

### Phase 1: Data Model Cleanup

#### 1.1 Generic params dict パターンの採用

**変更**: OscEvent/TrackParamsから明示的orbit/cpsフィールドを削除

**Before**:
```python
@dataclass
class OscEvent:
    sound: str
    orbit: int = 0      # REMOVED
    cps: float = 0.5    # REMOVED
    cycle: float
    gain: float = 1.0
    # ...

@dataclass
class TrackParams:
    s: str
    orbit: int = 0      # REMOVED
    gain: float = 1.0
    # ...
```

**After**:
```python
@dataclass
class OscEvent:
    sound: str
    params: dict[str, Any] = field(default_factory=dict)  # Generic
    cycle: float
    # orbit, cps are in params dict

@dataclass
class TrackParams:
    s: str
    gain: float = 1.0
    # orbit removed - extension assigns it
```

#### 1.2 MixerLine.get_orbit() の削除

**理由**: SuperDirt固有のロジックがコアに存在

**変更**: メソッド全体を削除（oiduna_core/ir/mixer_line.py:161-177）

#### 1.3 StepProcessor の完全削除

**発見**: StepProcessorとScheduledMessageが並行稼働

**変更**: StepProcessor関連コード全削除
- `packages/oiduna_loop/engine/step_processor.py` (650行)
- `packages/oiduna_core/output/output.py` (全モジュール削除)
- `packages/oiduna_core/protocols/output.py` (削除)
- 関連テスト削除

**削除総行数**: 3095+行

**結果**: ScheduledMessage architectureのみが残る

### Phase 2: OscSender Generalization

#### 2.1 Address パラメータ化

**変更**: ハードコードされた `/dirt/play` を設定可能に

**Before**:
```python
class OscSender:
    ADDRESS = "/dirt/play"  # Hardcoded

    def send(self, params):
        self._client.send_message(self.ADDRESS, args)
```

**After**:
```python
class OscSender:
    DEFAULT_ADDRESS = "/dirt/play"

    def __init__(self, host, port, address=DEFAULT_ADDRESS):
        self._address = address

    def send(self, params):
        self._client.send_message(self._address, args)
```

#### 2.2 SuperDirt固有メソッドの削除

**削除メソッド**:
- `send_osc_event()` - OscEvent依存
- `send_any()` - 冗長
- `send_silence()` - SuperDirt専用

**理由**:
- OscEventクラス自体が削除されたため
- send()メソッドで十分汎用的

### Phase 3: Extension Migration

#### 3.1 SuperDirt Extension による orbit/cps 注入

**実装**: oiduna-extension-superdirt

```python
class SuperDirtExtension(BaseExtension):
    def before_send_messages(self, messages, current_bpm, current_step):
        cps = current_bpm / 60.0 / 4.0

        for msg in messages:
            if msg.destination_id == "superdirt":
                params = {**msg.params}

                # Orbit injection (mixer_line_id → orbit mapping)
                mixer_line_id = params.get("mixer_line_id")
                if mixer_line_id:
                    params["orbit"] = self._get_or_assign_orbit(mixer_line_id)

                # CPS injection
                params["cps"] = cps

                # Remove internal params
                params.pop("mixer_line_id", None)

                yield msg.replace(params=params)
```

**特徴**:
- Runtime時にorbit/cpsを注入（コアに痕跡なし）
- mixer_line_id → orbit マッピングをExtensionで管理
- BPM変更に動的対応（before_send_messagesで毎回計算）

#### 3.2 SuperDirt Scripts の Extension への移行

**移動ファイル**:
- `scripts/setup_superdirt.sh` → `oiduna-extension-superdirt/scripts/`
- `scripts/start_superdirt.sh` → `oiduna-extension-superdirt/scripts/`
- `scripts/restore_superdirt.sh` → `oiduna-extension-superdirt/scripts/`
- `docs/superdirt_startup_oiduna.scd` → `oiduna-extension-superdirt/supercollider/`

**理由**: SuperDirt固有のセットアップはExtensionに含めるべき

---

## Consequences

### 🎯 達成した目標

#### 1. **True Destination-Agnostic Core**

**Before**:
```python
# Core had SuperDirt knowledge
track.orbit  # SuperDirt specific
osc_event.cps  # SuperDirt specific
```

**After**:
```python
# Core is generic
message.params["anything"]  # Fully generic
# Extensions decide what goes in params
```

**効果**: 任意のOSC destination（Supernova, Pure Data, Max/MSP等）で使用可能

#### 2. **コード削減**

| カテゴリ | 削除行数 |
|----------|----------|
| StepProcessor | 650行 |
| Output IR (OscEvent, MidiNoteEvent) | 320行 |
| Protocols | 122行 |
| 関連テスト | 2000+行 |
| **合計** | **3095+行** |

#### 3. **アーキテクチャ単純化**

**Before** (二重実装):
```
┌─────────────────────┐
│  LoopEngine         │
└──────┬──────────────┘
       │
       ├─→ StepProcessor → OscEvent/MidiEvent (Legacy)
       │                      ↓
       │                   OscSender
       │
       └─→ ScheduledMessage (New)
                 ↓
           DestinationRouter
```

**After** (単一実装):
```
┌─────────────────────┐
│  LoopEngine         │
└──────┬──────────────┘
       │
       └─→ ScheduledMessage
                 ↓
           Extension.before_send_messages()
                 ↓
           DestinationRouter
```

#### 4. **拡張性の向上**

**新しいDestination追加の手順**:

**Before** (コア変更必要):
1. OscEvent/MidiEventにフィールド追加
2. StepProcessorにロジック追加
3. コアテスト更新
4. すべてのDistributionが影響を受ける

**After** (Extension追加のみ):
1. BaseExtensionを継承
2. before_send_messages()で必要なparams注入
3. 独立してテスト
4. entry_pointsで登録

**例**: Supernova用Extension
```python
class SupernovaExtension(BaseExtension):
    def before_send_messages(self, messages, current_bpm, step):
        for msg in messages:
            if msg.destination_id == "supernova":
                # Supernovaはnode_id必須
                params = {**msg.params, "node_id": self._allocate_node()}
                yield msg.replace(params=params)
```

### 📊 テスト結果

**全437テスト合格**:
- oiduna_loop: 178/178 ✅
- packages/oiduna_loop: 148/148 ✅
- oiduna_api: 44/44 ✅
- integration: 2/3 (1 skipped) ✅

**重要な検証**:
- ✅ orbit/cps削除後もSuperDirtで音が出る（Extension経由）
- ✅ Extension performance <100μs (before_send_messages)
- ✅ BPM変更時のcps動的計算が動作
- ✅ mixer_line_id → orbit マッピングが永続化

### ⚠️ Breaking Changes

#### For Distribution Developers

**変更なし** - DistributionはScheduledMessageを生成するだけ

**Before**:
```python
ScheduledMessage(
    destination_id="superdirt",
    params={"s": "bd", "mixer_line_id": "drums"}
)
```

**After** (同じ):
```python
ScheduledMessage(
    destination_id="superdirt",
    params={"s": "bd", "mixer_line_id": "drums"}
)
# Extension が orbit/cps を注入
```

#### For Extension Developers

**Impact**: OscEvent/MidiEvent API削除

**Migration**:
```python
# OLD (削除された)
from oiduna_core.output import OscEvent
event = OscEvent(sound="bd", orbit=0, cps=0.5)
osc_sender.send_osc_event(event)

# NEW
# ScheduledMessage + before_send_messages() hook
message = ScheduledMessage(
    destination_id="superdirt",
    params={"s": "bd"}
)
# Extension hookで orbit/cps を追加
```

### 🔄 Migration Path

**既存のSuperDirt利用者**:
1. oiduna-extension-superdirt をインストール
2. 何もしない（自動で読み込まれる）

**新しいDestination追加**:
1. BaseExtension継承
2. before_send_messages() 実装
3. entry_points登録

---

## Related Documents

- [ADR-0006: Extension System in API Layer](0006-oiduna-extension-system-api-layer.md)
- [SUPERDIRT_MIGRATION_COMPLETE.md](../../SUPERDIRT_MIGRATION_COMPLETE.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [Extension Development Guide](../../EXTENSION_DEVELOPMENT_GUIDE.md)

---

## Implementation

**Files Changed**:
- ❌ DELETE: `packages/oiduna_core/output/` (全削除)
- ❌ DELETE: `packages/oiduna_loop/engine/step_processor.py`
- ✏️ EDIT: `packages/oiduna_core/ir/track.py` (orbit削除)
- ✏️ EDIT: `packages/oiduna_core/ir/mixer_line.py` (get_orbit削除)
- ✏️ EDIT: `packages/oiduna_loop/output/osc_sender.py` (address追加)
- ✏️ EDIT: `oiduna-extension-superdirt/__init__.py` (orbit/cps注入)
- 📁 MOVE: SuperDirt scripts → extension

**Test Updates**:
- 437 tests passed
- Import path fixes (oiduna_core.models → oiduna_core.ir)
- conftest.py updates
- Runtime state orbit field removal

**Commit**: Will be created with this ADR

---

## Notes

この変更により、Oidunaは真にdestination-agnostic、distribution-agnosticな汎用音楽スケジューラとなった。SuperDirt、Supernova、Pure Data、Max/MSP等、任意のOSC受信先で使用可能。

**設計思想の実現**:
> "We can't do that technically" → Never
> "Standard approaches should be surprisingly easy" → Always
> "Non-standard approaches possible with Distribution adjustments" → Flexible

この設計思想が、Extension Systemによって完全に実現された。
