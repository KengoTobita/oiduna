# Oiduna ディストリビューション設計ディスカッション

**日付:** 2026-02-22
**参加者:** Claude Code, ユーザー
**目的:** ディストリビューション作成のための設計方針を明確化

## ディストリビューションとは

### 定義

**Oiduna本体:**
- ループエンジン（タイミング、オーディオ出力）
- 汎用IR（Intermediate Representation）
- HTTP API（IR受付、再生制御）
- SuperDirt/MIDI統合

**ディストリビューション:**
- Oiduna本体を使用した「完結したシステム」
- DSLコンパイラ（Oiduna IRへの変換）
- プロジェクト管理（ファイルシステム、データベース等）
- 演奏者向けインターフェース（CLI、Web UI、API）
- セットアップ・デプロイメント手順

### MARS_for_oidunaの位置づけ

**2つの役割:**

1. **実用的なディストリビューション**
   - MARS DSLでOidunaを使用できる環境
   - プロジェクト/ソング/クリップ管理
   - 実際のライブコーディングで使用可能

2. **参考実装（デモ）**
   - ユーザーが独自ディストリビューションを作成する際の参考
   - ベストプラクティスの提示
   - 再利用可能なコンポーネントの提供

---

## ディストリビューションの典型的な構成要素

### 1. DSLコンパイラ

**役割:**
- ユーザーのDSL → Oiduna IR へ変換

**MARS_for_oidunaの例:**
```python
mars_dsl/
├── parser.py          # Larkパーサー
├── compiler.py        # コンパイラ本体
├── grammar/
│   └── mars_v5.lark   # DSL文法定義
└── transformers/      # AST → IR変換
```

**他の想定ディストリビューション例:**
- **TidalCycles風DSL:** Haskell風の関数型パターン記法
- **JavaScript DSL:** Strudel風のJavaScriptベース記法
- **ビジュアルDSL:** ノードベースのグラフィカル記法
- **MML風DSL:** テキストベースの音楽記法

### 2. プロジェクト管理

**役割:**
- ファイル構造の定義
- データの永続化
- バージョン管理

**MARS_for_oidunaの例:**
```
~/mars_projects/
└── my_live_set/
    ├── project.json      # プロジェクトメタデータ
    ├── songs/
    │   ├── track1/
    │   │   ├── song.json
    │   │   └── clips/
    │   │       ├── intro.json
    │   │       └── drop.json
    │   └── track2/
    └── assets/
        ├── samples/
        └── synthdefs/
```

**他の想定アプローチ:**
- **Git統合:** パターンをGitで管理
- **データベース:** SQLite/PostgreSQLでパターン管理
- **クラウド同期:** Google Drive、Dropbox等と連携
- **フラット構造:** 単純なファイル配置

### 3. API層

**役割:**
- ディストリビューション固有のAPIエンドポイント
- Oiduna本体APIとの橋渡し

**MARS_for_oidunaの例:**
```
MARS API (port 3000)
    ↓
POST /compile/apply
    ↓ (内部処理)
1. DSLをコンパイル
2. Oiduna IRに変換
3. POST http://oiduna:8000/scene
    ↓
Oiduna API (port 8000)
    ↓
SuperDirt/MIDI
```

### 4. ユーザーインターフェース

**CLI:**
```bash
mars compile pattern.mars
mars apply pattern.mars
mars project create my_set
```

**Web UI:**
- コードエディタ
- プロジェクトブラウザ
- ライブモニター

**API:**
- RESTful API
- WebSocket（リアルタイム通知）

### 5. セットアップ・デプロイメント

**MARS_for_oidunaの例:**
- `docs/oiduna-setup-guide.md` - Oidunaサーバーセットアップ
- `docs/environment-setup.md` - ネットワーク設定、mDNS
- `run_server.sh` - 起動スクリプト

---

## Oiduna本体が提供すべきインターフェース

### 現状（Phase 1完了時点）

#### A. IR受付API

**POST /scene**
- 汎用IRの受付
- セッション全体の更新

```json
{
  "environment": {"bpm": 120},
  "tracks": [
    {"id": "bd", "sound": "bd", "sequence": [...]}
  ]
}
```

#### B. 再生制御API

- **POST /playback/play** - 再生開始
- **POST /playback/stop** - 停止
- **POST /playback/pause** - 一時停止
- **PUT /playback/bpm** - BPM変更

#### C. SuperDirtリモートコントロール（Phase 1）

- **POST /superdirt/synthdef** - SynthDefロード
- **POST /superdirt/sample/load** - サンプルロード
- **GET /superdirt/buffers** - バッファリスト

#### D. ヘルスチェック

- **GET /health** - サーバー状態確認

### Phase 2以降で追加すべきインターフェース

#### E. メタデータAPI（Phase 2）

**GET /superdirt/synthdefs**
- ロード済みSynthDefリスト

**GET /superdirt/samples**
- ロード済みサンプルカテゴリ一覧

**GET /superdirt/samples/{category}/metadata**
- サンプルメタデータ（長さ、フォーマット等）

#### F. WebSocket通知（Phase 3）

**WS /stream**
- リアルタイムイベント通知
- パフォーマンスメトリクス
- エラー通知

#### G. プラグインシステム（Phase 4+）

ディストリビューションが独自の処理を挿入できる仕組み：

**例：カスタムトランスフォーマー**
```python
# ディストリビューション側でフック登録
oiduna.register_transform("pre_pattern", custom_transform)

# Oiduna本体が呼び出し
def apply_pattern(ir: dict):
    ir = hooks.run("pre_pattern", ir)  # カスタム変換
    engine.load_pattern(ir)
```

---

## ディストリビューション設計ガイドライン

### 原則1: Oiduna IRを中心に設計する

**Good:**
```
ユーザーDSL → コンパイラ → Oiduna IR → Oiduna API
```

**Bad:**
```
ユーザーDSL → 独自フォーマット → 独自変換 → Oiduna API
```

**理由:**
- Oiduna IRは汎用的に設計されている
- IR準拠により、Oiduna本体のアップデートに追従しやすい
- 他のディストリビューションとの相互運用性

### 原則2: レイヤーを明確に分離する

```
┌─────────────────────────────┐
│  ユーザーインターフェース層   │ (CLI, Web UI, API)
├─────────────────────────────┤
│  ディストリビューション層      │ (DSLコンパイラ, プロジェクト管理)
├─────────────────────────────┤
│  Oiduna API層               │ (HTTP API)
├─────────────────────────────┤
│  Oiduna エンジン層          │ (ループエンジン, IR処理)
├─────────────────────────────┤
│  オーディオ出力層            │ (SuperDirt, MIDI)
└─────────────────────────────┘
```

**各層の責務:**

**ユーザーインターフェース層:**
- ユーザー入力の受付
- 視覚的フィードバック
- ディストリビューションAPIの呼び出し

**ディストリビューション層:**
- DSL解析・コンパイル
- プロジェクト/ファイル管理
- Oiduna IRの生成

**Oiduna API層:**
- HTTPリクエスト処理
- IRバリデーション
- エンジンへの橋渡し

**Oiduna エンジン層:**
- タイミング制御
- パターン展開
- オーディオ出力スケジューリング

**オーディオ出力層:**
- OSC/MIDI送信
- SuperDirt/ハードウェアとの通信

### 原則3: 設定の外部化

**環境変数で制御可能に:**
```bash
# Oiduna本体の場所
OIDUNA_URL=http://localhost:8000

# ディストリビューション固有の設定
MARS_PROJECT_DIR=~/mars_projects
MARS_API_PORT=3000
```

**設定ファイル:**
```json
// distribution.json
{
  "oiduna": {
    "url": "http://localhost:8000",
    "timeout": 5000
  },
  "project": {
    "default_dir": "~/mars_projects",
    "schema_version": "0.3.0"
  },
  "api": {
    "port": 3000,
    "cors_origins": ["*"]
  }
}
```

### 原則4: ドキュメントの充実

**ディストリビューションに必要なドキュメント:**

1. **セットアップガイド**
   - Oiduna本体のインストール
   - ディストリビューション固有のセットアップ
   - 環境変数・設定

2. **DSLリファレンス**
   - 文法説明
   - サンプルコード
   - ベストプラクティス

3. **APIドキュメント**
   - エンドポイント一覧
   - リクエスト/レスポンス例
   - エラーコード

4. **アーキテクチャドキュメント**
   - システム構成図
   - データフロー
   - 拡張ポイント

**MARS_for_oidunaの実例:**
- `docs/oiduna-setup-guide.md`
- `docs/environment-setup.md`
- `README.md` (API仕様)

---

## 再利用可能なコンポーネント

### Oiduna本体が提供すべきライブラリ

#### 1. oiduna_core

**現状:**
- IRモデル（Pydantic）
- データ構造定義

**Phase 2以降で拡張:**
```python
# oiduna_core/validation.py
def validate_ir(ir: dict) -> ValidationResult:
    """IRの妥当性チェック"""

# oiduna_core/transform.py
def optimize_pattern(ir: dict) -> dict:
    """IRの最適化（重複除去等）"""

# oiduna_core/utils.py
def merge_sessions(session1: dict, session2: dict) -> dict:
    """セッションのマージ"""
```

#### 2. oiduna_client

**新規作成（Phase 2-3）:**

```python
# oiduna_client/client.py

from typing import Optional
import httpx

class OidunaClient:
    """Oiduna HTTP APIクライアント"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self._client = httpx.AsyncClient()

    async def apply_scene(self, scene: dict) -> dict:
        """シーン適用"""
        response = await self._client.post(
            f"{self.base_url}/scene",
            json=scene
        )
        response.raise_for_status()
        return response.json()

    async def play(self) -> dict:
        """再生開始"""
        response = await self._client.post(f"{self.base_url}/playback/play")
        response.raise_for_status()
        return response.json()

    async def load_synthdef(self, name: str, code: str) -> dict:
        """SynthDefロード"""
        response = await self._client.post(
            f"{self.base_url}/superdirt/synthdef",
            json={"name": name, "code": code}
        )
        response.raise_for_status()
        return response.json()

    async def get_health(self) -> dict:
        """ヘルスチェック"""
        response = await self._client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
```

**使用例（ディストリビューション側）:**
```python
from oiduna_client import OidunaClient

# ディストリビューションのコンパイラ
compiled_ir = my_compiler.compile(user_dsl)

# Oidunaクライアント経由で送信
client = OidunaClient()
await client.apply_scene(compiled_ir)
await client.play()
```

#### 3. oiduna_utils

**新規作成（Phase 2-3）:**

```python
# oiduna_utils/project.py

class ProjectManager:
    """プロジェクト管理の基盤クラス（ディストリビューションが継承）"""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    def create_project(self, name: str, metadata: dict):
        """プロジェクト作成（テンプレート）"""
        ...

    def load_project(self, name: str) -> dict:
        """プロジェクトロード"""
        ...

# oiduna_utils/dsl_base.py

class DSLCompilerBase:
    """DSLコンパイラの基底クラス"""

    def compile(self, source: str) -> dict:
        """DSL → Oiduna IR"""
        raise NotImplementedError

    def validate(self, source: str) -> ValidationResult:
        """DSL構文チェック"""
        raise NotImplementedError
```

**ディストリビューション側での使用:**
```python
from oiduna_utils import ProjectManager, DSLCompilerBase

class MarsCompiler(DSLCompilerBase):
    """MARS DSLコンパイラ（独自実装）"""

    def compile(self, source: str) -> dict:
        # MARS固有のコンパイル処理
        ...

class MarsProjectManager(ProjectManager):
    """MARSプロジェクト管理（拡張）"""

    def create_song(self, project: str, song: str):
        # MARS固有のソング管理
        ...
```

---

## ディストリビューション作成のステップ

### Step 1: コンセプト定義

**決定すべきこと:**
- 対象ユーザー（初心者 vs 上級者）
- DSLの方針（テキスト vs ビジュアル vs ハイブリッド）
- プロジェクト管理の要否
- デプロイメント方法（ローカル vs サーバー vs クラウド）

### Step 2: DSL設計

**文法定義:**
```lark
// your_dsl.lark
start: statement+

statement: track_def
         | pattern_def
         | apply_command

track_def: "Track" "(" STRING ")" ":" properties
...
```

**コンパイラ実装:**
```python
# your_dsl/compiler.py

class YourCompiler(DSLCompilerBase):
    def compile(self, source: str) -> dict:
        # パース
        tree = self.parser.parse(source)

        # Oiduna IRに変換
        ir = self.transform(tree)

        return ir
```

### Step 3: プロジェクト管理（オプション）

**ファイル構造定義:**
```
~/your_projects/
└── my_project/
    ├── project.json
    └── patterns/
        └── pattern1.your
```

**永続化:**
```python
class YourProjectManager(ProjectManager):
    def save_pattern(self, name: str, dsl: str):
        path = self.project_dir / "patterns" / f"{name}.your"
        path.write_text(dsl)
```

### Step 4: API実装（オプション）

**FastAPI:**
```python
from fastapi import FastAPI
from oiduna_client import OidunaClient

app = FastAPI()
client = OidunaClient()
compiler = YourCompiler()

@app.post("/compile/apply")
async def compile_and_apply(req: CompileRequest):
    ir = compiler.compile(req.dsl)
    await client.apply_scene(ir)
    await client.play()
    return {"status": "ok"}
```

### Step 5: ドキュメント作成

- セットアップガイド
- DSLチュートリアル
- サンプルコード
- トラブルシューティング

### Step 6: テスト

```python
# tests/test_compiler.py

def test_basic_compilation():
    compiler = YourCompiler()
    ir = compiler.compile('''
        Track("kick"):
            sound = bd
    ''')

    # Oiduna IRとして妥当か
    from oiduna_core.validation import validate_ir
    assert validate_ir(ir).is_valid
```

---

## MARS_for_oidunaから学ぶべきベストプラクティス

### 1. 明確なレイヤー分離

```
mars_dsl/      # DSLコンパイラ（Oiduna非依存）
mars_api/      # API層（Oiduna依存）
tests/         # 統合テスト
docs/          # ドキュメント
```

### 2. テスト戦略

```python
# ユニットテスト（Oiduna不要）
def test_pattern_compilation():
    compiler = MarsCompiler()
    result = compiler.compile("bd = x8888")
    assert result.success

# 統合テスト（Oiduna必要）
@pytest.mark.integration
async def test_end_to_end():
    # Oidunaが動いていることを前提
    client = OidunaClient()
    await client.apply_scene(...)
```

### 3. 環境設定の外部化

```python
# mars_api/config.py

class Settings(BaseSettings):
    oiduna_url: str = "http://localhost:8000"
    project_dir: Path = Path.home() / "mars_projects"
    api_port: int = 3000

    class Config:
        env_file = ".env"
```

### 4. ドキュメントの充実

- ✓ セットアップガイド（Oiduna + ディストリビューション）
- ✓ DSLリファレンス
- ✓ APIドキュメント
- ✓ 環境設定ガイド

---

## Oiduna本体への要求事項（設計方針）

### Phase 2で実装すべき

#### 1. oiduna_clientパッケージ

**目的:** ディストリビューションが簡単にOidunaを制御できるように

**提供機能:**
- 全APIエンドポイントのPythonラッパー
- 型ヒント完備
- エラーハンドリング
- 非同期対応

**配置:**
```
oiduna/
└── packages/
    └── oiduna_client/
        ├── __init__.py
        ├── client.py
        ├── models.py  # リクエスト/レスポンスモデル
        └── exceptions.py
```

#### 2. IRバリデーション関数

**目的:** ディストリビューション側で事前にIRをチェック

```python
from oiduna_core.validation import validate_ir, ValidationResult

ir = compiler.compile(dsl)
result = validate_ir(ir)

if not result.is_valid:
    for error in result.errors:
        print(f"Error: {error}")
```

#### 3. メタデータAPI

- GET /superdirt/synthdefs
- GET /superdirt/samples
- GET /superdirt/samples/{category}/metadata

**目的:** ディストリビューションがロード済みリソースを把握

### Phase 3で検討すべき

#### 4. WebSocket通知

**目的:** リアルタイムフィードバック

```python
# ディストリビューション側
async with client.subscribe("/events") as ws:
    async for event in ws:
        if event.type == "pattern_applied":
            print("Pattern applied!")
```

#### 5. プラグインシステム

**目的:** ディストリビューションが独自処理を挿入

```python
# ディストリビューション側でフック登録
oiduna.hooks.register("pre_compile", my_preprocessor)
oiduna.hooks.register("post_apply", my_logger)
```

---

## ディスカッションポイント

### Q1. oiduna_clientの実装優先度

Phase 2で実装すべきか？

**A: Phase 2で実装（推奨）**
- ディストリビューション作成が容易に
- 公式クライアントとしてベストプラクティス提示
- 工数: 2-3日

**B: Phase 3以降**
- 各ディストリビューションが独自実装
- Oiduna本体の開発に集中

### Q2. IRバリデーション関数の範囲

どこまで検証すべきか？

**A: 基本的な構造チェックのみ（推奨）**
- 必須フィールドの存在
- 型の妥当性
- 工数: 1-2日

**B: 詳細な意味チェック**
- トラック名の重複
- 参照整合性
- 工数: 3-4日

### Q3. プラグインシステムの必要性

Phase 3以降で必要か？

**A: 当面不要（推奨）**
- ディストリビューションはAPI経由で十分
- 複雑性が増す

**B: 将来的に実装**
- より高度なカスタマイズが可能
- エコシステムの拡大

### Q4. ディストリビューションテンプレートの提供

Oidunaリポジトリにテンプレートを含めるか？

**A: 含める（推奨）**
```
oiduna/
└── distribution_templates/
    ├── minimal/       # 最小限のテンプレート
    ├── dsl_only/      # DSLコンパイラのみ
    └── full_stack/    # プロジェクト管理含む
```

**B: MARS_for_oidunaを参照実装として推奨**
- ドキュメントでリンク
- Oiduna本体はシンプルに保つ

### Q5. ディストリビューションの認証・認可

複数ディストリビューションが同一Oidunaにアクセスする場合の制御は？

**A: Phase 2では不要**
- ローカル環境想定
- 単一ディストリビューション

**B: Phase 4で検討**
- APIキー認証
- レート制限
- マルチテナント対応

---

## 次のアクション

### 短期（Phase 2）

1. **oiduna_client実装**
   - 全APIエンドポイントのラッパー
   - 型ヒント、ドキュメント
   - サンプルコード

2. **IRバリデーション関数**
   - 基本的な構造チェック
   - 分かりやすいエラーメッセージ

3. **メタデータAPI**
   - GET /superdirt/synthdefs
   - GET /superdirt/samples
   - GET /superdirt/samples/{category}/metadata

4. **ディストリビューション作成ガイド**
   - ドキュメント作成
   - サンプルコード
   - ベストプラクティス

### 中期（Phase 3）

5. **WebSocket通知**
   - リアルタイムイベント配信

6. **ディストリビューションテンプレート**
   - minimal/dsl_only/full_stack

### 長期（Phase 4+）

7. **プラグインシステム（検討）**
8. **認証・認可（検討）**
9. **マルチテナント対応（検討）**

---

**記録者:** Claude Code
**ステータス:** ディスカッション進行中
**次回:** ユーザーフィードバック受領後、Phase 2詳細設計
