# リクエストIDシステム設計

**作成日:** 2026-02-22
**カテゴリ:** Phase 2 設計ドキュメント

## 問題の背景

### Phase 1の制限

Phase 1では、OSC確認メッセージのマッチングに「名前」を使用しています：

```python
# Phase 1の実装
confirmation = await receiver.wait_for_confirmation(
    '/oiduna/synthdef/loaded',
    timeout=5.0,
    filter_func=lambda args: args[0] == req.name  # 名前でマッチング
)
```

**問題点：**

```
時刻: 12:00:00.000
クライアントA: POST /superdirt/synthdef {"name": "kick", "code": "...v1..."}

時刻: 12:00:00.100
クライアントB: POST /superdirt/synthdef {"name": "kick", "code": "...v2..."}

時刻: 12:00:00.500
SuperCollider: → /oiduna/synthdef/loaded ["kick", 1]  ← どちらの確認？

問題:
- クライアントAの確認なのか、クライアントBの確認なのか判別不可能
- 最初に待っているクライアントAが受け取ってしまう
- クライアントBはタイムアウトで失敗する
```

### 実際の使用シーン

**シーン1: 複数演奏者**
```
演奏者A（iPad）: 「kick」のSynthDefをロード中...
演奏者B（ノートPC）: 同じ「kick」を別バージョンでロード
→ 混乱！
```

**シーン2: ライブループ中の更新**
```
ループ再生中...
演奏者: 「snare」を微調整してリロード（3秒おきに試行錯誤）
→ リクエストが重なる可能性大
```

**シーン3: 自動化スクリプト**
```python
# セットアップスクリプトが複数のSynthDefを高速ロード
for synth in ["kick", "snare", "hat", "bass"]:
    load_synthdef(synth)  # 並行実行される可能性

# または複数スクリプトが同時実行
script_a.py & script_b.py &
```

---

## リクエストIDシステムの仕組み

### 基本フロー

```
1. クライアント → API
   POST /superdirt/synthdef
   {
     "name": "kick",
     "code": "..."
   }

2. API内部
   request_id = uuid.uuid4()  # "a1b2c3d4-..."

3. API → SuperCollider (OSC)
   /oiduna/synthdef/load
   [
     "a1b2c3d4-...",  # ← リクエストID追加
     "kick",
     "..."
   ]

4. SuperCollider処理
   var requestId = msg[1];
   var name = msg[2];
   var code = msg[3];

   // 処理...

5. SuperCollider → API (OSC確認)
   /oiduna/synthdef/loaded
   [
     "a1b2c3d4-...",  # ← 同じリクエストIDを返す
     "kick",
     1  // success
   ]

6. API内部
   confirmation = await receiver.wait_for_confirmation(
       '/oiduna/synthdef/loaded',
       filter_func=lambda args: args[0] == request_id  # IDでマッチング
   )

7. API → クライアント (HTTP)
   {
     "request_id": "a1b2c3d4-...",
     "status": "ok",
     "name": "kick",
     "loaded": true
   }
```

### 同時リクエストの解決

```
時刻: 12:00:00.000
クライアントA: POST {"name": "kick", ...}
  → request_id = "aaaa-1111"

時刻: 12:00:00.100
クライアントB: POST {"name": "kick", ...}
  → request_id = "bbbb-2222"

時刻: 12:00:00.500
SuperCollider: → ["aaaa-1111", "kick", 1]
  → クライアントAが正しく受け取る ✓

時刻: 12:00:00.600
SuperCollider: → ["bbbb-2222", "kick", 1]
  → クライアントBが正しく受け取る ✓

結果: 両方成功！
```

---

## A1-1. リクエストID導入

### 実装内容

#### 1. リクエストIDの生成（API側）

```python
# routes/superdirt.py

import uuid

@router.post("/synthdef")
async def load_synthdef(req: SynthDefLoadRequest, ...):
    # 1. リクエストID生成
    request_id = str(uuid.uuid4())

    # 2. OSC送信時にリクエストIDを含める
    sender._client.send_message(
        '/oiduna/synthdef/load',
        [request_id, req.name, req.code]  # request_idを先頭に
    )

    # 3. 確認待機（リクエストIDでフィルタ）
    confirmation = await receiver.wait_for_confirmation(
        '/oiduna/synthdef/loaded',
        timeout=settings.superdirt_confirmation_timeout,
        filter_func=lambda args: args[0] == request_id  # IDマッチング
    )

    # 4. レスポンスにリクエストIDを含める
    return SynthDefLoadResponse(
        request_id=request_id,  # 追加
        status="ok",
        name=req.name,
        loaded=True
    )
```

#### 2. SuperCollider側の対応

```supercollider
// superdirt_startup_oiduna_v2.scd

OSCdef(\oiduna_synthdef_load, { |msg|
    var requestId = msg[1].asString;  // リクエストID取得
    var name = msg[2].asString;
    var code = msg[3].asString;
    var responseAddr = NetAddr("127.0.0.1", ~oidunaResponsePort);

    fork {
        try {
            code.interpret;
            s.sync;
            // 確認にリクエストIDを含める
            responseAddr.sendMsg(
                '/oiduna/synthdef/loaded',
                requestId,  // リクエストIDを返す
                name,
                1
            );
        } { |error|
            responseAddr.sendMsg(
                '/oiduna/synthdef/loaded',
                requestId,  // エラー時も返す
                name,
                0,
                error.errorString
            );
        };
    };
}, '/oiduna/synthdef/load');
```

#### 3. レスポンスモデルの拡張

```python
class SynthDefLoadResponse(BaseModel):
    request_id: str  # 追加
    status: str
    name: str
    loaded: bool
    message: str | None = None
```

### メリット

1. **同時リクエスト対応:** 同名のSynthDefを複数クライアントが同時ロード可能
2. **トレーサビリティ:** リクエストIDでログを追跡可能
3. **デバッグ性:** 問題発生時にリクエストを特定しやすい
4. **将来の拡張性:** 非同期処理、長時間処理への対応が容易

---

## A1-2. リクエストキュー管理

### 背景

高負荷時に大量のリクエストが同時に来た場合：

```
同時に100個のSynthDefロードリクエスト
→ SuperColliderが処理しきれない
→ タイムアウト多発
→ システムが不安定に
```

### 解決策: キュー管理

```python
# services/request_queue.py

import asyncio
from collections import deque

class RequestQueue:
    def __init__(self, max_concurrent: int = 5):
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._queue = deque()

    async def execute(self, coro):
        """同時実行数を制限してコルーチンを実行"""
        async with self._semaphore:
            return await coro
```

**使用例:**

```python
# routes/superdirt.py

# グローバルキュー（アプリケーション起動時に作成）
synthdef_queue = RequestQueue(max_concurrent=5)

@router.post("/synthdef")
async def load_synthdef(req: SynthDefLoadRequest, ...):
    # キュー経由で実行（同時5個まで）
    return await synthdef_queue.execute(
        _load_synthdef_impl(req, loop_service)
    )
```

**効果:**

```
100個のリクエスト受信
→ 5個ずつ並行処理
→ SuperColliderに過負荷をかけない
→ 安定動作

待機中のリクエスト:
- Position 1-5: 処理中
- Position 6-10: 待機中（すぐ次）
- Position 11-100: 待機中
```

---

## A1-3. 優先度付きキュー

### 背景

ライブコーディング中の使用シーン：

```
演奏中...
演奏者: 新しいSynthDefを試したい（急ぎ！）
バックグラウンド: 大量のサンプルローディング中（重い、時間かかる）

問題:
- サンプルロードが先に開始されている
- SynthDefロードが待たされる
- 演奏のタイミングを逃す！
```

### 解決策: 優先度付きキュー

```python
import heapq
from enum import IntEnum

class Priority(IntEnum):
    URGENT = 0     # 演奏中の即時変更
    HIGH = 1       # SynthDefロード
    NORMAL = 2     # 通常のサンプルロード
    LOW = 3        # バックグラウンド処理

class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._counter = 0

    async def execute(self, coro, priority: Priority = Priority.NORMAL):
        """優先度付きで実行"""
        # heapqは最小値を優先するので、優先度の値が小さいほど先に処理
        item = (priority, self._counter, coro)
        heapq.heappush(self._queue, item)
        self._counter += 1

        # 実行...
```

**使用例:**

```python
# SynthDef（高優先度）
await queue.execute(
    load_synthdef(...),
    priority=Priority.HIGH
)

# サンプル（通常優先度）
await queue.execute(
    load_samples(...),
    priority=Priority.NORMAL
)

# バックグラウンドタスク（低優先度）
await queue.execute(
    cleanup_old_samples(...),
    priority=Priority.LOW
)
```

**実行順序:**

```
キューの状態:
1. [HIGH] SynthDef "kick" ロード
2. [URGENT] エフェクトパラメータ変更（演奏中！）
3. [NORMAL] サンプル "drums" ロード
4. [LOW] 古いサンプルのクリーンアップ

実行順序:
1. URGENT: エフェクトパラメータ変更 ← 最優先
2. HIGH: SynthDef "kick" ロード
3. NORMAL: サンプル "drums" ロード
4. LOW: クリーンアップ
```

---

## 実装の段階的アプローチ

### Phase 2.0: リクエストID（必須）

**工数:** 2-3日

**内容:**
- リクエストID生成
- SuperCollider側対応
- 確認マッチング修正

**完了条件:**
- 同時リクエストが正しく処理される
- すべてのエンドポイントが対応

### Phase 2.1: 基本的なキュー管理（推奨）

**工数:** 1-2日

**内容:**
- Semaphoreベースの同時実行数制限
- 設定可能な最大同時実行数

**完了条件:**
- 高負荷時に安定動作
- タイムアウトが減少

### Phase 2.2: 優先度付きキュー（オプション）

**工数:** 2-3日

**内容:**
- 優先度enum定義
- heapqベースのキュー実装
- APIに優先度パラメータ追加（オプション）

**完了条件:**
- 高優先度リクエストが優先処理される
- 演奏中の即時変更が遅延しない

---

## ユーザーへの質問

### Q1. Phase 2での優先度

以下のどれを Phase 2 に含めるべきか？

**A. リクエストIDのみ**（最小限）
- 工数: 2-3日
- 同時リクエスト対応のみ

**B. リクエストID + 基本キュー**（推奨）
- 工数: 4-5日
- 同時リクエスト + 高負荷対応

**C. リクエストID + 基本キュー + 優先度**（フル装備）
- 工数: 6-8日
- 同時リクエスト + 高負荷 + 優先制御

### Q2. 使用シーンの想定

実際の使用でどのシーンが多いか？

**シーン1:** 単一演奏者、順次処理
- → リクエストIDのみで十分

**シーン2:** 単一演奏者、試行錯誤で連続ロード
- → リクエストID + 基本キュー

**シーン3:** 複数演奏者、または自動化スクリプト使用
- → リクエストID + 基本キュー + 優先度

### Q3. 演奏中の即時性

演奏中に「今すぐSynthDef変更したい」シーンは頻繁にあるか？

**Yes:** 優先度付きキューが有用
**No:** 基本キューで十分

---

## 推奨実装プラン

### Phase 2.0（必須）

**リクエストID導入**
- すべてのエンドポイント対応
- SuperCollider側修正
- テスト追加

### Phase 2.1（推奨）

**基本的なキュー管理**
- Semaphoreベースの同時実行制限
- 設定可能な上限（デフォルト: 5）

### Phase 2.2（条件付き）

**優先度付きキュー**
- 実際の演奏で必要性が明確になった場合に実装
- Phase 3以降でも可

---

**次のアクション:**
1. 使用シーンの確認
2. Phase 2での実装範囲決定
3. 詳細設計・実装開始
