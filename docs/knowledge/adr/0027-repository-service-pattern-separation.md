# ADR-0027: Repository/Service Pattern による Session Domain の責務分離

**Status:** Accepted
**Date:** 2026-03-15
**Deciders:** Kengo Tobita, Claude Sonnet 4.5
**Related:** ADR-0010 (SessionContainer), ADR-0025 (Manager Error Handling), ADR-0023 (4-Layer Architecture)

---

## Context

Oiduna Session Domainは6つのManagerクラス（ClientManager, DestinationManager, EnvironmentManager, TrackManager, PatternManager, TimelineManager）で構成されていたが、各Managerがデータアクセス、ビジネスロジック、イベント発行の3つの責務を同時に担っていた。

### 問題点

#### 1. 責務の混在

```python
class TrackManager(BaseManager):
    """
    混在している責務:
    - データアクセス: session.tracks[track_id] への読み書き
    - バリデーション: Destination/Client存在チェック
    - イベント発行: _emit_change("track_created", ...)
    """

    def create(self, track_name: str, destination_id: str, client_id: str):
        # バリデーション
        if destination_id not in self.session.destinations:
            raise ValueError(...)

        # データアクセス
        track = Track(...)
        self.session.tracks[track_id] = track

        # イベント発行
        self._emit_change("track_created", {...})
```

#### 2. テストの困難性

- Managerをモック化すると、データアクセス、ビジネスロジック、イベント発行の全てをモック化する必要がある
- 単体テストで特定の責務のみをテストできない
- 依存関係が複雑（TrackManager → DestinationManager → Session）

#### 3. 再利用性の欠如

- 他のServiceからデータアクセスのみを行いたい場合でも、Manager全体の依存性を引き込む必要がある
- イベント発行なしでデータアクセスする方法がない

#### 4. トランザクション制御の困難性

- 複数のデータ操作をまとめてロールバックする仕組みがない
- Pattern移動（Track間移動）のような複雑な操作で、途中でエラーが発生した場合の復旧が困難

### 既存アーキテクチャ

```
FastAPI Routes
    ↓
SessionContainer
    ├─ ClientManager (データアクセス + ロジック + イベント)
    ├─ TrackManager (データアクセス + ロジック + イベント)
    ├─ PatternManager (データアクセス + ロジック + イベント)
    └─ ...
    ↓
Domain Models (Session, Track, Pattern)
```

---

## Decision

**Repository Pattern**と**Service Pattern**を導入し、Session Domainを2層に分離する。

### 新アーキテクチャ

```
FastAPI Routes
    ↓
SessionContainer (Dependency Injection)
    ├─ Service層（ビジネスロジック）
    │   ├─ ClientService
    │   ├─ TrackService
    │   ├─ PatternService
    │   └─ TimelineService
    │   ↓
    └─ Repository層（データアクセス）
        ├─ ClientRepository
        ├─ TrackRepository
        ├─ PatternRepository
        └─ TimelineRepository
        ↓
Domain Models (Session, Track, Pattern)
```

### 責務分担

#### Repository層（データアクセス専用）

- `session.tracks[track_id]` への直接的な読み書きのみ
- 単純なCRUD操作（save, get, exists, list, delete）
- **バリデーションなし**
- **イベント発行なし**
- **ビジネスロジックなし**

例:
```python
class TrackRepository(BaseRepository):
    """Pure data access to session.tracks."""

    def save(self, track: Track) -> None:
        self.session.tracks[track.track_id] = track

    def get(self, track_id: str) -> Optional[Track]:
        return self.session.tracks.get(track_id)

    def exists(self, track_id: str) -> bool:
        return track_id in self.session.tracks
```

#### Service層（ビジネスロジック）

- バリデーション（Destination/Client存在チェック等）
- 複数Repositoryの調整（カスケード削除、Track間移動等）
- ID生成（IDGenerator使用）
- イベント発行（SessionChangePublisher経由）
- トランザクション制御（ロールバック処理）

例:
```python
class TrackService(BaseService):
    """Business logic for tracks."""

    def __init__(
        self,
        track_repo: TrackRepository,
        destination_repo: DestinationRepository,
        client_repo: ClientRepository,
        id_generator: IDGenerator,
        change_publisher: Optional[SessionChangePublisher] = None,
    ):
        super().__init__(change_publisher)
        self.track_repo = track_repo
        self.destination_repo = destination_repo
        self.client_repo = client_repo
        self.id_generator = id_generator

    def create(self, track_name: str, destination_id: str, client_id: str):
        # 1. バリデーション
        if not self.destination_repo.exists(destination_id):
            raise ValueError(f"Destination {destination_id} not found")
        if not self.client_repo.exists(client_id):
            raise ValueError(f"Client {client_id} not found")

        # 2. ID生成
        track_id = self.id_generator.generate_track_id()

        # 3. データ保存
        track = Track(track_id=track_id, track_name=track_name, ...)
        self.track_repo.save(track)

        # 4. イベント発行
        self._emit_change("track_created", {...})

        return track
```

#### SessionContainer（Dependency Injection）

- Repository層とService層の初期化
- Serviceに必要なRepositoryを注入
- APIはServiceのみを使用（Repositoryは内部使用のみ）

```python
class SessionContainer:
    def __init__(self, change_publisher: Optional[SessionChangePublisher] = None):
        self.session = Session()

        # Repository層
        self.track_repo = TrackRepository(self.session)
        self.destination_repo = DestinationRepository(self.session)
        self.client_repo = ClientRepository(self.session)

        # Service層（Repositoryを注入）
        self.tracks = TrackService(
            track_repo=self.track_repo,
            destination_repo=self.destination_repo,
            client_repo=self.client_repo,
            id_generator=self.session._id_generator,
            change_publisher=change_publisher,
        )
```

### 実装対象

6つのManager → 6つのRepository + 6つのService:

| Manager | Repository | Service |
|---------|------------|---------|
| ClientManager | ClientRepository | ClientService |
| DestinationManager | DestinationRepository | DestinationService |
| EnvironmentManager | EnvironmentRepository | EnvironmentService |
| TrackManager | TrackRepository | TrackService |
| PatternManager | PatternRepository | PatternService |
| TimelineManager | TimelineRepository | TimelineService |

### 高度な機能

#### 1. トランザクション制御（Pattern移動）

```python
class PatternService:
    def _move_pattern(self, pattern_id: str, new_track_id: str) -> None:
        # 1. 旧Trackから削除
        pattern = self.pattern_repo.get_by_id(pattern_id)
        old_track_id = pattern.track_id
        self.pattern_repo.remove_from_track(old_track_id, pattern_id)

        # 2. 新Trackに追加（失敗時はロールバック）
        pattern.track_id = new_track_id
        try:
            self.pattern_repo.save_to_track(new_track_id, pattern)
        except Exception as e:
            # ロールバック: 旧Trackに復元
            pattern.track_id = old_track_id
            self.pattern_repo.save_to_track(old_track_id, pattern)
            raise ValueError(f"Failed to move pattern: {e}")
```

#### 2. Soft Delete（Pattern）

```python
# 物理削除せず、archivedフラグで論理削除
def delete(self, pattern_id: str) -> bool:
    pattern = self.pattern_repo.get_by_id(pattern_id)
    if pattern:
        pattern.archived = True
        self.pattern_repo.save_to_track(pattern.track_id, pattern)
        self._emit_change("pattern_archived", {...})
        return True
    return False
```

#### 3. Lookahead検証（Timeline）

```python
TIMELINE_MIN_LOOKAHEAD = 8  # 最低8ステップ先

def cue_change(self, target_global_step: int, current_global_step: int, ...):
    min_target = current_global_step + TIMELINE_MIN_LOOKAHEAD
    if target_global_step < min_target:
        return (False, f"予約は最低{TIMELINE_MIN_LOOKAHEAD}ステップ先に設定してください", None)
```

#### 4. 権限チェック（Timeline）

```python
def cancel_change(self, change_id: str, client_id: str):
    change = self.timeline_repo.get_change_by_id(change_id)

    # 所有者のみキャンセル可能
    if change.client_id != client_id:
        return (False, f"Permission denied: change owned by {change.client_id}")

    return self.timeline_repo.cancel_change(change_id)
```

---

## Consequences

### メリット

#### 1. 責務の明確化

- Repository: データアクセスのみ
- Service: ビジネスロジック、バリデーション、イベント
- Container: 依存性組み立て
- API Route: HTTPハンドリング

各層が**単一責任**を持つ。

#### 2. テスタビリティの向上

```python
# 旧構造: Managerをモック化（複雑）
mock_manager = MagicMock()
mock_manager.create.return_value = Track(...)

# 新構造: Repositoryのみモック化（シンプル）
mock_repo = MockTrackRepository()
service = TrackService(mock_repo, ...)
result = service.create(...)
```

- 単体テスト: Service単独でテスト可能（Mock Repositoryを注入）
- 統合テスト: 実際のRepositoryを使用
- **149テストケース全合格**

#### 3. 再利用性の向上

```python
# 他のServiceから直接Repositoryを使える
class PatternService:
    def __init__(self, pattern_repo, track_repo, ...):
        self.track_repo = track_repo  # TrackRepositoryを再利用

    def validate_track_exists(self, track_id):
        return self.track_repo.exists(track_id)
```

#### 4. 拡張性

新機能追加時の変更範囲が明確:

1. Repository追加（データアクセス）
2. Service追加（ビジネスロジック）
3. SessionContainerに登録
4. API Route追加

各層が独立しているため、**変更の影響範囲が限定的**。

#### 5. 型安全性

```python
# Protocolによる型チェック
change_publisher: SessionChangePublisher  # mypy がチェック

# Pydanticモデルによる実行時検証
track = Track(track_id="invalid")  # ValidationError
```

#### 6. トランザクション制御

Service層でロールバック処理を実装可能:
- Pattern移動の例: 新Track追加失敗時に旧Trackへ復元
- 複数Repository操作を1つのトランザクションとして扱える

#### 7. API互換性維持

```python
# API Routeは変更なし
@router.post("/tracks")
async def create_track(container: SessionContainer = Depends(get_container)):
    track = container.tracks.create(...)  # インターフェース同じ
    return track
```

SessionContainerのインターフェース（`container.tracks.create()`）を維持したため、既存のAPI Routeは**無変更**で動作。

### デメリット

#### 1. ファイル数の増加

- 旧構造: 6 Managers
- 新構造: 6 Repositories + 6 Services = **12ファイル**

対策: 明確な責務分離により、各ファイルのコードは短く理解しやすい。

#### 2. 学習コスト

新規開発者がRepository/Serviceの違いを理解する必要がある。

対策: ADR（本ドキュメント）で責務を明記。

### 実装統計

- **Repository層**: 8ファイル（base + 6リポジトリ + \_\_init\_\_）
- **Service層**: 8ファイル（base + 6サービス + \_\_init\_\_）
- **テストファイル**: 14ファイル
- **テストケース**: 149個（全合格）
- **実装期間**: 7フェーズ（約4週間相当の作業を集中実施）

### 関連ADR

- **ADR-0010**: SessionContainer Refactoring（Manager導入の基礎）
- **ADR-0025**: Phase 2 Manager Error Handling（Manager改善の試み）
- **ADR-0023**: Unified 4-Layer Architecture（全体アーキテクチャ）

---

## Implementation Notes

### ディレクトリ構造

```
src/oiduna/domain/session/
├── container.py                # SessionContainer（Repository + Service初期化）
├── types.py                    # SessionChangePublisher Protocol
├── repositories/               # Repository層
│   ├── __init__.py
│   ├── base.py                # BaseRepository
│   ├── client_repository.py
│   ├── destination_repository.py
│   ├── environment_repository.py
│   ├── track_repository.py
│   ├── pattern_repository.py
│   └── timeline_repository.py
└── services/                   # Service層
    ├── __init__.py
    ├── base.py                # BaseService（_emit_change実装）
    ├── client_service.py
    ├── destination_service.py
    ├── environment_service.py
    ├── track_service.py
    ├── pattern_service.py
    └── timeline_service.py
```

### デザインパターン

1. **Repository Pattern**: データアクセスのカプセル化
2. **Service Pattern**: ビジネスロジックのカプセル化
3. **Dependency Injection**: SessionContainerが依存性を注入
4. **Protocol (PEP 544)**: SessionChangePublisherで型安全なインターフェース
5. **Soft Delete**: Pattern削除にarchivedフラグ使用

### 段階的移行

7フェーズで段階的に実施:

1. **Phase 1**: インフラ構築（BaseRepository, BaseService, テストフィクスチャ）
2. **Phase 2**: シンプルなManager移行（Client, Destination, Environment）
3. **Phase 3**: 中程度のManager移行（Track）
4. **Phase 4**: 複雑なManager移行（Pattern, Timeline）
5. **Phase 5**: SessionContainer統合
6. **Phase 6**: API統合テスト
7. **Phase 7**: 旧Manager削除とクリーンアップ

---

## Conclusion

Repository/Service Pattern導入により、Oiduna Session Domainは以下を達成:

- ✅ 責務の明確化（各層が単一責任）
- ✅ テスタビリティ向上（149テスト全合格）
- ✅ 再利用性向上（Repositoryの独立使用）
- ✅ 拡張性向上（変更影響範囲の限定）
- ✅ 型安全性（Protocol + Pydantic）
- ✅ API互換性維持（既存エンドポイント無変更）

このアーキテクチャは、今後のOidunaの成長に対応できる堅牢な基盤となる。
