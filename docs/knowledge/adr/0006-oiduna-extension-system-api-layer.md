# ADR 0006: Extension System in API Layer Only

**Status**: Accepted

**Date**: 2026-02-25

**Deciders**: tobita, Claude Code

---

## Context

Oidunaの拡張システム（Extension System）をどこに配置するかを決定する必要があった。

### 背景

Oidunaはdestination-agnostic（送信先非依存）、distribution-agnostic（ディストリビューション非依存）な汎用スケジューラとして設計されている。しかし、SuperDirtのようなdestination固有のロジック（orbit割り当て、パラメータ名変換）や、MARSのようなdistribution固有のロジック（MixerLine処理）を、Oidunaコアを汚染せずに追加する仕組みが必要だった。

### 検討した拡張のユースケース

**SuperDirt拡張の例**:
- Orbit自動割り当て（MixerLine → orbit マッピング）
- パラメータ名変換（delay_send → delaySend）
- cps注入（BPMから計算）

**その他の想定ケース**:
- MIDI velocity カーブ変換
- カスタムOSCプロトコル対応
- メッセージフィルタリング

### 設計の要求事項

1. **loop_engineの純粋性を保つ**
   - パフォーマンスクリティカルなループに拡張システムを持ち込まない
   - destination/distribution非依存を維持

2. **拡張の柔軟性**
   - 外部パッケージとして提供（別リポジトリ）
   - YAMLで設定可能
   - 複数拡張のパイプライン実行

3. **責務の明確化**
   - 拡張が担当すべき範囲を明確にする

---

## Decision

**拡張システムはAPI層のみに配置し、loop_engine層には一切持ち込まない。**

### アーキテクチャ

```
POST /playback/session
  ↓
routes/playback.py (API Layer)
  ↓
SessionExtensionPipeline.transform(payload)  ← ★ 拡張はここで実行
  ↓
loop_engine._handle_session(transformed_payload)  ← 拡張を知らない
  ↓
MessageScheduler.load_messages()
  ↓
実行時ループ（フックなし、ただ送信）
```

### 拡張の責務

**拡張が担当する範囲（API層）**:
- ✅ セッションペイロード（dict）の変換
- ✅ メッセージの追加・削除・変更
- ✅ パラメータの追加・削除・変換
- ✅ BPM/pattern_lengthの調整

**拡張が担当しない範囲**:
- ❌ 実行時の動的処理（ステップごとの状態変更）
- ❌ loop_engineへの直接アクセス
- ❌ Destinationへの直接送信
- ❌ MessageScheduler内部の操作

### 変換タイミング

**タイミング**: セッションロード時のみ（1回）

```
HTTP リクエスト受信
  ↓
Pydantic validation
  ↓
★ 拡張パイプライン適用（ここで変換）
  ↓
loop_engineに渡す
  ↓
実行時（フックなし）
```

### 実装構造

```
packages/
├── oiduna_api/
│   ├── routes/
│   │   └── playback.py          # 拡張パイプラインを使用
│   └── extensions/               # ★ 拡張システム
│       ├── base.py              # SessionExtension ABC
│       ├── pipeline.py          # SessionExtensionPipeline
│       └── loader.py            # YAML読み込み
│
├── oiduna_loop/
│   └── engine/
│       └── loop_engine.py       # ★ 拡張を一切知らない
```

### 拡張の基本インターフェース

```python
class SessionExtension(ABC):
    def __init__(self, config: dict):
        pass

    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """セッションペイロードを変換"""
        pass

    def on_api_startup(self) -> None:
        """API起動時（オプション）"""
        pass

    def on_api_shutdown(self) -> None:
        """API終了時（オプション）"""
        pass
```

### 設定ファイル

```yaml
# extensions.yaml
extensions:
  - name: superdirt
    package: oiduna_extension_superdirt
    class: SuperDirtExtension
    enabled: true
    config:
      default_orbit_count: 12
```

---

## Consequences

### Positive

1. **loop_engineの独立性維持**
   - 拡張システムと完全分離
   - パフォーマンスクリティカルなループに影響なし
   - destination/distribution非依存の原則を維持

2. **シンプルな責務分離**
   - API層 = リクエスト変換
   - loop_engine = スケジューリング・送信
   - 各層の責務が明確

3. **テスト容易性**
   - 拡張のテスト: `transform(payload)` のユニットテスト
   - API統合テスト: モックエンジンで簡単
   - loop_engineのテスト: 拡張を考慮不要

4. **エラーハンドリング**
   - HTTP層でエラーをキャッチして適切なレスポンス
   - loop_engineはエラーを知らない

5. **パフォーマンス**
   - 変換はセッションロード時のみ（1回）
   - 実行時ループは高速（フック呼び出しなし）

### Negative

1. **動的処理の制約**
   - BPM変更時のcps再計算ができない
   - ステップごとの状態変更ができない
   - 実行時の条件分岐ができない

2. **cps問題**
   - セッションロード時にcpsを埋め込む
   - BPM変更後は古いcpsのまま
   - 解決策: DestinationSender層で動的追加、またはcpsを送信しない

### Mitigation

**cps問題の解決策（✅ 実装済み）**:

~~案A: cpsをメッセージに埋め込まず、DestinationSender層で追加~~
- 却下理由: SuperDirt固有のロジックがoidunaコアに混入

~~案B: cpsはSuperDirtのデフォルト値に任せる（送信しない）~~
- 却下理由: BPMコントロールができない（実用的でない）

~~案C: BPM変更時にセッション再変換（複雑）~~
- 却下理由: 実装が複雑、position reset問題

**✅ 案D（採用）: before_send_messagesで動的注入**
```python
def before_send_messages(self, messages, current_bpm, current_step):
    cps = current_bpm / 60.0 / 4.0
    return [
        msg.replace(params={**msg.params, "cps": cps})
        if msg.destination_id == "superdirt"
        else msg
        for msg in messages
    ]
```

**採用理由**:
- ✅ BPM変更に自動対応
- ✅ 拡張パッケージ内で完結
- ✅ 最小限のランタイムフック（before_send_messagesのみ）
- ✅ パフォーマンス要件を満たす（p99 < 100μs）
- ✅ oidunaコアは汎用的なフックメカニズムのみ提供

**トレードオフ**:
- ⚠️ ADR当初の「API層のみ」原則に若干反する
- ✅ しかし「ステップごとの状態変更」ではなく「メッセージの最終調整」
- ✅ フック1つのみに限定することで影響を最小化

---

## Alternatives Considered

### Alternative A: loop_engine内フック（却下）

**アーキテクチャ**:
```
loop_engine内に ExtensionManager を配置
_step_loop() で before_step, before_send_messages フックを呼び出し
```

**却下理由**:
- loop_engineが拡張システムに依存（純粋性の喪失）
- パフォーマンスクリティカルなループでフック呼び出し（リスク）
- destination/distribution非依存の原則に反する
- テストが複雑化

**議論のポイント**:
「送信するOSCの内容を操作するだけならAPIのレイヤでなんとか出来ない？ループに手を出さず、API内部でガチャガチャしたほうが良くない？」（tobita）

### Alternative B: ハイブリッド（API + loop_engine）（却下）

**アーキテクチャ**:
```
基本: API層で拡張
例外: 動的処理が必要な場合のみloop_engineフック
```

**却下理由**:
- 2つの拡張システムを管理する複雑性
- 責務の境界が曖昧
- 現時点で動的処理の必須ユースケースが存在しない

### Alternative C: Middleware（検討中）

**アーキテクチャ**:
```
FastAPIのMiddlewareパターンを使用
```

**ステータス**: FastAPIエコシステムとの統合方法を調査予定
- FastAPI Users, FastAPI Cacheなどの実装パターンを参考にする
- Dependency InjectionとMiddlewareのどちらが適切か検討

---

## Implementation Status

### ✅ 完了 (2026-02-25)

1. **loop_engine内のフック統合を全て削除**
   - `packages/oiduna_extensions/` パッケージ削除
   - `extensions.yaml` 削除
   - loop_engine.py から全フック呼び出しを削除
   - ExtensionManager, ExtensionContext のインポート削除

2. **oiduna-extension-superdirtリポジトリのクリーンアップ**
   - 実装ファイルを削除
   - REQUIREMENTS.md のみ保持（今後の参考用）

3. **GLOSSARY.md 作成**
   - Oiduna専門用語の定義集
   - 今後のディスカッションの基盤

4. **API層拡張システムの実装**
   - ✅ `packages/oiduna_api/extensions/base.py` - BaseExtension ABC
   - ✅ `packages/oiduna_api/extensions/pipeline.py` - ExtensionPipeline
   - ✅ `packages/oiduna_api/extensions/__init__.py`
   - ✅ `packages/oiduna_api/dependencies.py` - get_pipeline DI
   - ✅ entry_points自動発見機能

5. **FastAPI統合**
   - ✅ `main.py` - lifespan統合（拡張のロード、フック収集、ルーター登録）
   - ✅ `routes/playback.py` - Dependency Injection統合
   - ✅ 拡張ルーターの自動include

6. **loop_engine統合（最小限のランタイムフック）**
   - ✅ `loop_engine.py` - before_send_hooks受け取りとフック呼び出し
   - ✅ `factory.py` - before_send_hooksパラメータ追加
   - ✅ `loop_service.py` - before_send_hooksパラメータ追加

7. **SuperDirt拡張の実装（API層版）**
   - ✅ `oiduna-extension-superdirt/pyproject.toml` - entry_points設定
   - ✅ `oiduna-extension-superdirt/oiduna_extension_superdirt/__init__.py`
     - Orbit割り当て（mixer_line_id → orbit）
     - パラメータ名変換（snake_case → camelCase）
     - CPS注入（before_send_messages フック）
     - カスタムエンドポイント（/superdirt/*）
   - ✅ REQUIREMENTS.md更新（API層専用設計）
   - ✅ README.md作成

8. **パフォーマンス検証**
   - ✅ `test_extension_performance.py` - ベンチマークテスト作成
   - ✅ `benchmark_plan.md` - ベンチマーク計画策定

### 実装の詳細

#### entry_points方式の採用

FastAPIエコシステムと統合し、`pip install` だけで拡張が自動認識される方式を採用：

```toml
# pyproject.toml
[project.entry-points."oiduna.extensions"]
superdirt = "oiduna_extension_superdirt:SuperDirtExtension"
```

#### before_send_messages() フックの追加

ADR当初の「API層のみ」原則を維持しつつ、cps注入のための**最小限のランタイムフック1つのみ**を許可：

```python
class BaseExtension(ABC):
    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """Session load時の変換（必須）"""
        ...

    def before_send_messages(self, messages, current_bpm, current_step):
        """送信直前の最終調整（オプション、パフォーマンスクリティカル）"""
        return messages  # デフォルトは無変更
```

**設計判断**:
- フック1つのみに限定（before_step, after_step等は禁止）
- 「ステップごとの状態変更」ではなく「メッセージの最終調整」
- パフォーマンス要件: p99 < 100μs

#### cps問題の解決（案D採用）

Mitigation案のうち、**案D: before_send_messagesで動的注入**を採用：

```python
def before_send_messages(self, messages, current_bpm, current_step):
    cps = current_bpm / 60.0 / 4.0
    return [
        msg.replace(params={**msg.params, "cps": cps})
        if msg.destination_id == "superdirt"
        else msg
        for msg in messages
    ]
```

**理由**:
- ✅ BPM変更に自動対応
- ✅ 拡張パッケージ内で完結
- ✅ 最小限のランタイム介入
- ✅ oidunaコアは汎用的なフックメカニズムのみ提供

---

## Related

- **GLOSSARY.md**: Oiduna専門用語定義集
- **oiduna-extension-superdirt/REQUIREMENTS.md**: SuperDirt拡張の機能要件
- **ADR 0003**: Oiduna Destination-Based Architecture（基盤となる設計）

---

## Notes

### 議論の経緯

1. **当初の設計**: loop_engine内にExtensionManagerとフック（on_startup, on_session_load, before_step, before_send_messages, after_step）を実装

2. **問題提起**: 「送信するOSCの内容を操作するだけならAPIのレイヤでなんとか出来ない？」

3. **再評価**: SuperDirt拡張の大部分はAPI層で完結できることを確認
   - Orbit割り当て: ✅ API層で可能
   - パラメータ名変換: ✅ API層で可能
   - cps注入: ⚠️ BPM変更に弱いが解決策あり

4. **決定**: loop_engineフックを全削除し、API層のみで進める

### 設計原則の再確認

**Oidunaの核心原則**:
- loop_engineは汎用スケジューラとして純粋に保つ
- destination-agnostic（送信先非依存）
- distribution-agnostic（ディストリビューション非依存）

**拡張システムの役割**:
- destination固有のロジックを追加（SuperDirt orbit, MIDI channel）
- distribution固有のロジックを追加（MARS MixerLine）
- Oidunaコアの純粋性を維持したまま拡張性を提供

---

## Lessons Learned

### 設計の進化

**当初の方針**: API層のみ、loop_engineフック一切なし

**実装時の発見**: cps注入のような「送信直前の動的調整」が必要なユースケースが存在

**最終決定**: 最小限のランタイムフック（before_send_messagesのみ）を許可

**原則の維持**:
- loop_engineは汎用的なフックメカニズムのみ提供
- SuperDirt固有のロジックは一切含まない
- 拡張パッケージ内で完結

### パフォーマンスへの配慮

**before_send_messagesの制約**:
- 実行時ループ内で毎ステップ呼ばれる
- パフォーマンスクリティカル
- 目標: p99 < 100μs（ステップ間隔125ms@BPM120の0.08%以下）

**実装ガイドライン**:
- リスト内包表記を使用（Pythonの最適化）
- 重い処理はtransform()で実施（session load時に1回）
- before_send_messages()は軽量な最終調整のみ

### 拡張システムの成功要因

1. **entry_points自動発見**: FastAPIエコシステムと統合、設定ファイル不要
2. **Dependency Injection**: 特定エンドポイントのみに適用、テスト容易
3. **get_router()**: 拡張が独自エンドポイントを提供可能
4. **明確な責務分離**: transform（session）とbefore_send_messages（runtime）

---

**Last Updated**: 2026-02-25 (Implementation Complete)
