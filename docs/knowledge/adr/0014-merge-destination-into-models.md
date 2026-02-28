# ADR-0014: oiduna_destinationパッケージのoiduna_modelsへの統合

**Status**: Accepted
**Date**: 2026-03-01
**Author**: Oiduna Development Team

---

## Context

Oidunaプロジェクトでは、データモデルを以下の2パッケージに分けて管理していた:

- **oiduna_models**: Session, Track, Pattern, Event等のコアモデル（797行、9ファイル）
- **oiduna_destination**: OscDestinationConfig, MidiDestinationConfig等の送信先設定（113行、3ファイル）

### 現状の課題

1. **機能的重複**: 両パッケージともPydanticモデルによるデータ定義を担当
2. **依存関係の複雑化**: oiduna_modelsがoiduna_destinationに依存
3. **パッケージ分割の必然性欠如**: 規模が小さく（113行）、統合しても問題ない
4. **インポート階層の冗長性**: `from oiduna_destination.destination_models import ...`

### Layer 5の再定義

アーキテクチャレビューの過程で、Layer 5は単なる「データフロー」の一部ではなく、システム全体の**Foundation（基盤）**として機能していることが明確になった。この観点から、データモデルは一元管理されるべきである。

---

## Decision

`oiduna_destination`パッケージを`oiduna_models`パッケージに統合する。

### 統合内容

1. **コード移動**:
   - `oiduna_destination/destination_models.py` → `oiduna_models/destination_models.py`
   - `oiduna_destination/loader.py` → `oiduna_models/loader.py`

2. **テスト移動**:
   - `tests/oiduna_destination/` → `packages/oiduna_models/tests/`

3. **インポート更新**（22ファイル）:
   - Before: `from oiduna_destination.destination_models import DestinationConfig`
   - After: `from oiduna_models import DestinationConfig`

4. **ドキュメント更新**:
   - `layer-5-data.md`: DestinationConfig統合、Foundationコンセプト追加
   - `README.md`: Layer 5エントリ更新
   - `ADR-0012`: Foundationコンセプト追加

---

## Consequences

### Positive

- ✅ **シンプルなパッケージ構成**: データモデルが1パッケージに集約
- ✅ **明確な責任**: `oiduna_models`が唯一のデータ定義層
- ✅ **短いインポートパス**: `from oiduna_models import ...`
- ✅ **保守性向上**: 関連モデルが同一パッケージ内に配置
- ✅ **Foundationコンセプトの強化**: Layer 5の基盤としての役割が明確化

### Negative

- ⚠️ **既存コードの影響**: 22ファイルのインポート更新が必要
- ⚠️ **一時的なテスト失敗リスク**: 移行中のインポートエラー

### Neutral

- 🔄 **パッケージ数削減**: 10パッケージ → 9パッケージ
- 🔄 **テスト数不変**: 統合前後で513テスト維持

---

## Alternatives Considered

### Alternative 1: 現状維持（パッケージ分離）

**Pros**:
- 変更不要（リスクゼロ）
- 既存のインポートパスが維持される

**Cons**:
- パッケージ分割の正当性が乏しい
- 依存関係が複雑化
- Foundationコンセプトと不整合

**Rejected理由**: パッケージ分割の必然性がなく、統合メリットが大きい

### Alternative 2: oiduna_modelsをoiduna_destinationに統合

**Pros**:
- データモデルの一元化

**Cons**:
- oiduna_destinationは規模が小さく（113行）、中心的パッケージとして不適切
- 命名が送信先に特化しすぎており、Sessionなどのコアモデルを含むには不適

**Rejected理由**: oiduna_modelsの方が中心的パッケージとして適切

---

## Implementation

### Phase構成（7フェーズ）

1. **Phase 1**: バックアップと準備（5分）
2. **Phase 2**: コードファイル移動（15分）
3. **Phase 3**: インポート更新（30分）
4. **Phase 4**: テスト再編成（20分）
5. **Phase 5**: 旧パッケージ削除（10分）
6. **Phase 6**: ドキュメント更新（40分）
7. **Phase 7**: 検証とコミット（20分）

**総推定時間**: 2.5-3時間

### 検証基準

- ✅ 全513テストがパス
- ✅ `oiduna_destination`への参照が0件
- ✅ ドキュメント内のリンクが正常
- ✅ インポートエラーが0件

---

## References

- [ADR-0012: Package Architecture (Layered Design)](./0012-package-architecture-layered-design.md)
- [Layer 5: データ層](../../architecture/layer-5-data.md)
- [EXTENSION_GUIDE](../../architecture/EXTENSION_GUIDE.md)

---

**Updated**: 2026-03-01
**Related ADRs**: ADR-0012
