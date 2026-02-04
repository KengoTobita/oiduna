# MARS Distribution Development Prompt

このプロンプトは、MARS（Modular Audio Real-time Scripting）ディストリビューションを開発する際に、AIアシスタントに提供する包括的なコンテキストです。

## プロジェクト概要

MARS_for_oidunaは、Oidunaループエンジンのためのパターン記述DSL（Domain Specific Language）です。ユーザーが直感的な構文で音楽パターンを記述し、それをOidunaのCompiledSession形式にコンパイルして送信します。

## アーキテクチャ

```
┌──────────────────┐
│ Monaco Editor    │  ← ユーザーがMARSコードを書く
│ (Web UI)         │
└────────┬─────────┘
         │ HTTP POST /compile
         ↓
┌──────────────────┐
│ MARS API Server  │  ← FastAPI server (port 3000)
│ - Larkパーサー    │
│ - コンパイラ      │
│ - Oidunaクライアント│
└────────┬─────────┘
         │ HTTP POST /playback/pattern
         ↓
┌──────────────────┐
│ Oiduna API       │  ← ループエンジン (port 8000)
│ - 既に実装済み    │
└────────┬─────────┘
         │ OSC/MIDI
         ↓
┌──────────────────┐
│ SuperDirt / DAW  │  ← オーディオ出力
└──────────────────┘
```

## Oiduna API 仕様

### ベースURL
```
http://localhost:8000
```

### 主要エンドポイント

#### 1. パターンのロード
```bash
POST /playback/pattern
Content-Type: application/json

{
  "environment": {"bpm": 120},
  "tracks": {
    "bd": {
      "sound": "bd",
      "orbit": 0,
      "gain": 1.0,
      "pan": 0.5,
      "mute": false,
      "solo": false,
      "sequence": [
        {"pitch": "0", "start": 0, "length": 1},
        {"pitch": "0", "start": 4, "length": 1}
      ]
    }
  },
  "sequences": {}
}
```

#### 2. 再生制御
```bash
POST /playback/start    # 再生開始
POST /playback/stop     # 停止
POST /playback/pause    # 一時停止
POST /playback/bpm      # BPM変更
  Body: {"bpm": 140}
```

#### 3. ステータス取得
```bash
GET /playback/status
```

#### 4. トラック制御
```bash
POST /tracks/{track_id}/mute
  Body: {"muted": true}

POST /tracks/{track_id}/solo
  Body: {"solo": true}
```

完全なAPIリファレンス: `/home/tobita/study/livecoding/oiduna/docs/api-examples.md`

## CompiledSession スキーマ

MARSコンパイラが生成すべきJSON形式:

```typescript
interface CompiledSession {
  environment: {
    bpm: number;
    [key: string]: any;  // 追加のグローバルパラメータ
  };
  tracks: Record<string, Track>;
  sequences: Record<string, Sequence>;
}

interface Track {
  sound: string;      // SuperDirtサウンド名
  orbit: number;      // 0-11
  gain: number;       // 0.0-1.0
  pan: number;        // 0.0-1.0
  mute: boolean;
  solo: boolean;
  sequence: Event[];
  // SuperDirtパラメータを追加可能:
  cutoff?: number;
  resonance?: number;
  delay?: number;
  reverb?: number;
}

interface Event {
  pitch: string;      // MIDI note or "0" for percussion
  start: number;      // ステップ数（0始まり）
  length: number;     // 長さ（ステップ数）
  velocity?: number;  // 0-127
}
```

完全なスキーマ: `/home/tobita/study/livecoding/oiduna/docs/data-model.md`

## MARS DSL 構文仕様（v5）

### 基本パターン記法

```mars
// Track定義
Track(track_id="bd", sound="bd", orbit=0)

// パターン代入
bd = x8888          // x = trigger, 8 = rest

// barタイミングで適用
@bar apply bd
```

### 階層的パターン構文

```mars
// 基本
bd = x888

// ネスト（4x展開）
bd = [x888 x8x8]

// 二重ネスト（16x展開）
hh = [[x8x8 x8xx] [xxxx 88x8]]
```

### エフェクトパラメータ

```mars
Track(
  track_id="bd",
  sound="bd",
  orbit=0,
  gain=1.0,
  cutoff=2000,
  resonance=0.2,
  delay=0.3
)
```

### 文法（Lark）

```lark
start: statement+

statement: track_def
         | pattern_assign
         | apply_cmd

track_def: "Track" "(" param_list ")"
pattern_assign: NAME "=" pattern
apply_cmd: "@" TIMING "apply" NAME

pattern: PATTERN_STR
       | "[" pattern+ "]"

param_list: param ("," param)*
param: NAME "=" value

value: STRING | NUMBER | BOOLEAN
TIMING: "bar" | "beat" | "now"
PATTERN_STR: /[x8.]+/

%import common.CNAME -> NAME
%import common.ESCAPED_STRING -> STRING
%import common.NUMBER
%import common.WS
%ignore WS
```

## MARS プロジェクト構造

```
MARS_for_oiduna/
├── pyproject.toml          # uv project config
├── README.md
├── mars_dsl/               # DSLコンパイラ
│   ├── __init__.py
│   ├── parser.py           # Larkパーサー
│   ├── compiler.py         # CompiledSession生成
│   ├── grammar.lark        # MARS文法定義
│   └── schema.py           # Pydanticスキーマ
├── mars_api/               # HTTP API server
│   ├── __init__.py
│   ├── server.py           # FastAPI app
│   ├── routes/
│   │   ├── compile.py      # POST /compile
│   │   └── monaco.py       # Monaco補完API
│   └── oiduna_client.py    # Oiduna API wrapper
├── mars_frontend/          # Web UI
│   ├── static/
│   │   ├── monaco/         # Monaco Editor
│   │   └── app.js
│   └── templates/
│       └── editor.html
└── tests/
    ├── test_parser.py
    ├── test_compiler.py
    └── test_integration.py
```

## 実装ステップ

### Phase 1: コンパイラコア (最優先)

1. **Larkパーサー作成** (`mars_dsl/parser.py`)
   - Track定義のパース
   - パターン代入のパース
   - @applyコマンドのパース

2. **コンパイラ作成** (`mars_dsl/compiler.py`)
   - パターン文字列 → Event[] 変換
   - 階層構文の展開 `[x888 x8x8]` → 16ステップ
   - CompiledSession生成

3. **ユニットテスト** (`tests/test_compiler.py`)
   ```python
   def test_simple_pattern():
       code = """
       Track(track_id="bd", sound="bd")
       bd = x888
       @bar apply bd
       """
       result = compile_mars(code)
       assert result["tracks"]["bd"]["sequence"][0]["start"] == 0
       assert len(result["tracks"]["bd"]["sequence"]) == 1
   ```

### Phase 2: HTTP API

4. **FastAPI サーバー** (`mars_api/server.py`)
   ```python
   from fastapi import FastAPI
   from mars_dsl.compiler import compile_mars
   from mars_api.oiduna_client import OidunaClient

   app = FastAPI()

   @app.post("/compile")
   async def compile_endpoint(body: dict):
       dsl_code = body["dsl"]
       session = compile_mars(dsl_code)
       return {"session": session}

   @app.post("/compile/apply")
   async def compile_and_apply(body: dict):
       dsl_code = body["dsl"]
       session = compile_mars(dsl_code)

       oiduna = OidunaClient("http://localhost:8000")
       oiduna.load_pattern(session)

       return {"status": "ok"}
   ```

5. **Oidunaクライアント** (`mars_api/oiduna_client.py`)
   ```python
   import httpx

   class OidunaClient:
       def __init__(self, base_url: str):
           self.base_url = base_url
           self.client = httpx.Client(base_url=base_url)

       def load_pattern(self, session: dict):
           response = self.client.post("/playback/pattern", json=session)
           response.raise_for_status()
           return response.json()

       def start(self):
           response = self.client.post("/playback/start")
           response.raise_for_status()

       def stop(self):
           response = self.client.post("/playback/stop")
           response.raise_for_status()
   ```

### Phase 3: Web UI

6. **Monaco Editor統合** (`mars_frontend/templates/editor.html`)
   - Monaco Editorの埋め込み
   - シンタックスハイライト（カスタム言語定義）
   - リアルタイムコンパイル（onChangeでPOST /compile）

7. **補完API** (`mars_api/routes/monaco.py`)
   ```python
   @app.get("/monaco/completions")
   async def get_completions(position: int, text: str):
       # Track名の補完
       # パラメータの補完
       return {"suggestions": [...]}
   ```

## 開発時の注意点

### 1. パターン展開アルゴリズム

```python
def expand_pattern(pattern: str, depth: int = 0) -> list[int]:
    """
    "x888" → [0, 4, 8, 12] (4ステップ間隔)
    "[x888 x8x8]" → [0, 4, 8, 12, 16, 18, 20, 22] (8個のイベント)
    """
    if pattern.startswith("["):
        # 再帰的に展開
        sub_patterns = parse_nested(pattern)
        results = []
        for i, sub in enumerate(sub_patterns):
            sub_events = expand_pattern(sub, depth + 1)
            offset = i * len(sub) * (4 ** depth)
            results.extend([e + offset for e in sub_events])
        return results
    else:
        # 基本パターン
        events = []
        for i, char in enumerate(pattern):
            if char == "x":
                events.append(i * (4 ** (depth + 1)))
        return events
```

### 2. エラーハンドリング

- **構文エラー**: Larkが自動で検出
- **未定義トラック**: コンパイル時にチェック
- **Oidunaエラー**: HTTP 500をキャッチして表示

```python
try:
    session = compile_mars(code)
except LarkError as e:
    return {"error": f"Syntax error: {e}"}
except KeyError as e:
    return {"error": f"Undefined track: {e}"}
```

### 3. Pydanticバリデーション

```python
from pydantic import BaseModel, Field

class Track(BaseModel):
    sound: str
    orbit: int = Field(ge=0, le=11)
    gain: float = Field(ge=0.0, le=1.0)
    pan: float = Field(ge=0.0, le=1.0)
    mute: bool = False
    solo: bool = False
    sequence: list[Event]

class CompiledSession(BaseModel):
    environment: dict
    tracks: dict[str, Track]
    sequences: dict
```

## テスト例

### 統合テスト

```python
import pytest
from mars_dsl.compiler import compile_mars
from mars_api.oiduna_client import OidunaClient

def test_full_workflow():
    # MARSコードをコンパイル
    code = """
    Track(track_id="bd", sound="bd", orbit=0)
    bd = x888
    @bar apply bd
    """

    session = compile_mars(code)

    # Oidunaに送信
    client = OidunaClient("http://localhost:8000")
    client.load_pattern(session)
    client.start()

    # ステータス確認
    status = client.get_status()
    assert status["playing"] == True
    assert "bd" in status["active_tracks"]
```

### パーサーテスト

```python
def test_nested_pattern():
    code = "bd = [x888 x8x8]"
    tree = parser.parse(code)
    result = compiler.transform(tree)

    # 8個のイベントが生成される
    assert len(result["tracks"]["bd"]["sequence"]) == 5
    # 最初のイベントはstep 0
    assert result["tracks"]["bd"]["sequence"][0]["start"] == 0
```

## 依存関係

```toml
[project]
name = "mars-for-oiduna"
version = "0.1.0"
dependencies = [
    "lark>=1.1.9",
    "pydantic>=2.0.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.27.0",
    "httpx>=0.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "mypy>=1.8.0",
]
```

## 起動方法

```bash
# ターミナル1: Oidunaを起動
cd /home/tobita/study/livecoding/oiduna
uv run python -m oiduna_api.main

# ターミナル2: MARSを起動
cd /home/tobita/study/livecoding/MARS_for_oiduna
uv run python -m mars_api.server

# ブラウザで http://localhost:3000 を開く
```

## デバッグのヒント

### 1. コンパイル結果の確認

```python
import json

session = compile_mars(code)
print(json.dumps(session, indent=2))
```

### 2. Oiduna APIのテスト

```bash
# 直接curlでテスト
curl -X POST http://localhost:8000/playback/pattern \
  -H "Content-Type: application/json" \
  -d @compiled_session.json
```

### 3. ログの有効化

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

## リファレンス資料

1. **Oiduna API完全ガイド**
   - `/home/tobita/study/livecoding/oiduna/docs/api-examples.md`
   - `/home/tobita/study/livecoding/oiduna/docs/data-model.md`

2. **Distribution開発ガイド**
   - `/home/tobita/study/livecoding/oiduna/docs/distribution-guide.md`

3. **Interactive Docs**
   - Oiduna: http://localhost:8000/docs
   - MARS: http://localhost:3000/docs (実装後)

4. **外部ドキュメント**
   - Lark Parser: https://lark-parser.readthedocs.io/
   - FastAPI: https://fastapi.tidalcycles.org/
   - Monaco Editor: https://microsoft.github.io/monaco-editor/

## AIアシスタントへの指示

このプロンプトを使用する際は、以下の点に注意してください：

1. **段階的実装**: Phase 1（コンパイラ）から順に実装する
2. **テスト駆動**: 各機能にユニットテストを書く
3. **エラーハンドリング**: ユーザーフレンドリーなエラーメッセージ
4. **ドキュメント**: 各関数にdocstringを追加
5. **型ヒント**: すべてのPython関数に型アノテーションを付ける

### 実装時のプロンプト例

```
MARS_for_oidunaプロジェクトのPhase 1を実装してください。

1. mars_dsl/grammar.lark を作成
   - Track定義、パターン代入、@applyコマンドをサポート

2. mars_dsl/parser.py を作成
   - Larkパーサーのラッパー

3. mars_dsl/compiler.py を作成
   - パターン文字列をEvent[]に変換
   - CompiledSession形式で出力

4. tests/test_compiler.py を作成
   - 基本パターン、ネストパターンのテスト

参照:
- Oiduna API: /home/tobita/study/livecoding/oiduna/docs/api-examples.md
- スキーマ: /home/tobita/study/livecoding/oiduna/docs/data-model.md
```

## まとめ

このプロンプトには以下が含まれています：

- ✅ Oiduna API仕様（完全版）
- ✅ CompiledSessionスキーマ
- ✅ MARS DSL構文仕様
- ✅ プロジェクト構造
- ✅ 実装ステップ（Phase 1-3）
- ✅ コード例（Python）
- ✅ テスト例
- ✅ デバッグ方法
- ✅ リファレンスドキュメントへのパス

このプロンプトをAIアシスタントに提供すれば、MARS_for_oidunaプロジェクトを最初から実装できます。
