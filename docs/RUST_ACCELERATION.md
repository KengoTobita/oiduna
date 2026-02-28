# Rust高速化ガイド

**最終更新:** 2026-02-28

このドキュメントは、Oidunaのコアデータ処理にRustを統合する戦略を簡潔にまとめたものです。

完全な技術的背景は [ADR-0011](knowledge/adr/0011-rust-acceleration-strategy.md) を参照してください。

---

## 🎯 基本方針

### なぜRust？なぜループエンジンではなくデータ変換？

**意外な発見:**
```
従来の想定: 「ループエンジンが最もクリティカル」
実際の測定: 「データ変換がボトルネック」

ループエンジン: ~2ms/step （すでに高速）
SessionCompiler: ~30ms/compile（大規模セッション時）
                 ↑
            これがGIL contention を引き起こす！
```

**Rust化の優先順位:**
1. **SessionCompiler** (最優先) → 10-20倍高速化
2. **MessageScheduler** (次点) → 5-10倍高速化
3. **MessageFilter** (オプション) → 2-5倍高速化

---

## 🏗️ アーキテクチャ

### 3層設計

```
┌─────────────────────────────────────────┐
│ 🔵 Layer 1: API (Python)                │
│    役割: HTTP、ビジネスロジック、拡張     │
│    拡張性: ★★★★★                       │
│                                         │
│    - FastAPI routes                     │
│    - SessionContainer CRUD              │
│    - BaseExtension.transform() ←拡張    │
└────────────┬────────────────────────────┘
             ▼
┌─────────────────────────────────────────┐
│ 🟠 Layer 2: Compilation (Rust)          │
│    役割: Session → Batch 変換            │
│    拡張性: ☆☆☆☆☆ (固定実装)             │
│                                         │
│    - RustSessionCompiler.compile()      │
│    - RustMessageScheduler.load()        │
│    - 10-20倍の高速化                     │
└────────────┬────────────────────────────┘
             ▼
┌─────────────────────────────────────────┐
│ 🔵 Layer 3: Loop (Python + Hooks)       │
│    役割: リアルタイム配信                 │
│    拡張性: ★★★★☆ (Hooks経由)            │
│                                         │
│    - LoopEngine (Python asyncio)        │
│    - before_send_hooks ←拡張            │
│    - タイミング、ドリフト補正             │
└─────────────────────────────────────────┘
```

**設計原則:**
- 🟠 **予測可能・高速が必要** → Rust
- 🔵 **柔軟性・拡張性が必要** → Python
- ✅ **境界を明確に** → 拡張APIは安定

---

## 🔧 実装例

### SessionCompiler (Rust版)

**現状（Python）:**
```python
def compile(session: Session) -> ScheduledMessageBatch:
    messages = []
    for track in session.tracks.values():           # O(T)
        for pattern in track.patterns.values():     # O(P)
            for event in pattern.events:            # O(E)
                # Dict merge (slow!)
                params = {**track.base_params, **event.params}
                messages.append(ScheduledMessage(...))
    return ScheduledMessageBatch(tuple(messages), ...)

# 性能: 10 tracks × 100 events = 2ms
#      50 tracks × 1000 events = 30ms (問題！)
```

**Rust実装:**
```rust
// packages/oiduna_session_rust/src/compiler.rs

#[pyclass]
pub struct RustSessionCompiler;

#[pymethods]
impl RustSessionCompiler {
    #[staticmethod]
    fn compile(py: Python, session: &PyAny) -> PyResult<PyObject> {
        let mut messages = Vec::with_capacity(1024);

        // Rust HashMap (Python dictより高速)
        for track in session.getattr("tracks")?.values() {
            for pattern in track.getattr("patterns")?.values() {
                // Fast skip
                if !pattern.getattr("active")?.extract::<bool>()? {
                    continue;
                }

                for event in pattern.getattr("events")? {
                    // Rust HashMap merge (5x faster)
                    let msg = create_message_fast(track, event)?;
                    messages.push(msg);
                }
            }
        }

        create_batch(py, messages, ...)
    }
}

// 性能: 10 tracks × 100 events = 0.2ms (10x)
//      50 tracks × 1000 events = 1.5ms (20x)
```

**Python統合（透過的Fallback）:**
```python
# packages/oiduna_session/compiler.py

try:
    from oiduna_session_rust import RustSessionCompiler
    _USE_RUST = True
except ImportError:
    _USE_RUST = False

class SessionCompiler:
    @staticmethod
    def compile(session: Session) -> ScheduledMessageBatch:
        if _USE_RUST:
            return RustSessionCompiler.compile(session)
        else:
            return SessionCompiler._compile_python(session)
```

**拡張への影響:** なし（透過的）

---

## 🎨 拡張フレームワーク保持

### Extension APIは変更なし

```python
class BaseExtension(ABC):
    # ════════════════════════════════════════════
    # API Layer: Rust compile() の「前」に実行
    # ════════════════════════════════════════════

    @abstractmethod
    def transform(self, payload: dict) -> dict:
        """
        Session変換（重い処理OK）

        - タイミング: POST /playback/sync 時
        - パフォーマンス: <50ms推奨
        - 言語: Pure Python（完全な柔軟性）

        用途:
        - Destination固有パラメータ追加
        - Distribution固有ロジック
        - カスタムTrack生成
        """
        pass

    # ════════════════════════════════════════════
    # Loop Layer: Rust処理の「後」に実行
    # ════════════════════════════════════════════

    def before_send_messages(self, messages, bpm, step):
        """
        送信直前の変換（軽量必須）

        - タイミング: 毎ステップ（31ms間隔）
        - パフォーマンス: <100μs厳守
        - 言語: Pure Python（軽量のみ）

        用途:
        - リアルタイムパラメータ注入（cps等）
        - BPM依存の調整
        """
        return messages
```

**重要ポイント:**
- Extensions operate at **boundaries** (before/after Rust)
- Rust core is **transparent** (extensions don't see it)
- Performance gains are **automatic**

---

## 📦 開発ワークフロー

### 環境セットアップ

```bash
# Rust toolchain インストール（初回のみ）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# プロジェクトセットアップ
cd /home/tobita/study/livecoding/oiduna
```

### 開発時（Debugビルド）

```bash
# Rust拡張を開発モードでビルド
cd packages/oiduna_session_rust
maturin develop

# テスト実行
cd ../..
uv run pytest packages/oiduna_session/tests/
```

### リリース時（Releaseビルド）

```bash
# 本番用ビルド（最適化有効）
cd packages/oiduna_session
uv build

# Wheelファイルが生成される
# dist/oiduna_session_rust-0.1.0-*.whl
```

### uv統合の注意点

```toml
# pyproject.toml に追加（Rustソース変更を検知）

[tool.uv.cache-keys]
file = [
    "../oiduna_session_rust/Cargo.toml",
    "../oiduna_session_rust/src/**/*.rs"
]
```

---

## 📊 性能目標

### コンパイル時間

| セッションサイズ | 現状（Python） | 目標（Rust） | 改善率 |
|----------------|---------------|-------------|--------|
| 小（10 tracks, 100 events） | 2ms | 0.2ms | 10x |
| 中（30 tracks, 500 events） | 10ms | 0.8ms | 12.5x |
| 大（50 tracks, 1000 events） | 30ms | 1.5ms | 20x |

**成功基準:**
- ✅ 全compile操作 < 2ms
- ✅ 99th percentile < 5ms
- ✅ GIL contentionなし

---

## 🚀 実装ロードマップ

### Phase 1: SessionCompiler Rust化（最優先）

**実装対象:**
- `RustSessionCompiler.compile()`
- Fallback機構
- ベンチマーク

**期待効果:**
- 10-20倍高速化
- `/playback/sync` ボトルネック解消

**工数:** 3-5日

**拡張への影響:** なし

---

### Phase 2: MessageScheduler Rust化

**実装対象:**
- `RustMessageScheduler.load_messages()`
- `RustMessageScheduler.get_messages_at_step()`

**期待効果:**
- 5-10倍高速化
- メモリ効率向上

**工数:** 2-3日

**拡張への影響:** なし

---

### Phase 3: MessageFilter Rust化（オプション）

**実装対象:**
- `RustMessageFilter.filter()`

**期待効果:**
- 2-5倍高速化（Fast pathはすでに最適）

**工数:** 1-2日

**優先度:** 低（Phase 1-2の結果次第）

---

## 🔍 ベンチマーク方法

### 基本ベンチマーク

```python
# packages/oiduna_session/tests/benchmark_compile.py

import time
from oiduna_session import SessionCompiler

def benchmark_compile(session, label):
    start = time.perf_counter()
    batch = SessionCompiler.compile(session)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"{label}: {elapsed_ms:.2f}ms ({len(batch.messages)} messages)")
    return elapsed_ms

# 使用例
small_session = create_session(tracks=10, events_per_track=10)
benchmark_compile(small_session, "Small")

large_session = create_session(tracks=50, events_per_track=1000)
benchmark_compile(large_session, "Large")
```

### プロファイリング

```python
import cProfile
import pstats

pr = cProfile.Profile()
pr.enable()

batch = SessionCompiler.compile(session)

pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumtime')
stats.print_stats(10)  # Top 10 slowest functions
```

---

## ⚠️ 注意事項

### 1. Python 3.13へのアップグレード推奨

```bash
# 現状
$ python3 --version
Python 3.12.3

# pyproject.toml要件
requires-python = ">=3.13,<3.14"
```

**理由:**
- PyO3のPython 3.13サポートは完全
- Free-threading (nogil) 対応
- 将来性

### 2. プラットフォーム対応

**サポート予定:**
- ✅ Linux (x86_64, aarch64)
- ✅ macOS (x86_64, Apple Silicon)
- ✅ Windows (x86_64)

**配布方法:**
- Pre-built wheels (PyPI)
- Fallback to pure Python if unavailable

### 3. CI/CD更新

```yaml
# .github/workflows/test.yml に追加

- name: Install Rust
  uses: actions-rs/toolchain@v1
  with:
    toolchain: stable

- name: Build Rust extensions
  run: |
    cd packages/oiduna_session_rust
    maturin build --release
```

---

## 📚 参考資料

### 公式ドキュメント

- [PyO3 User Guide](https://pyo3.rs/)
- [Maturin Documentation](https://www.maturin.rs/)
- [Rust Book (日本語版)](https://doc.rust-jp.rs/book-ja/)

### Oiduna関連

- [ADR-0011: Rust Acceleration Strategy](knowledge/adr/0011-rust-acceleration-strategy.md) - 完全な技術決定記録
- [GIL_MITIGATION.md](architecture/GIL_MITIGATION.md) - GIL問題の詳細分析
- [ADR-0010: SessionContainer](knowledge/adr/0010-session-container-refactoring.md) - データモデル設計

### 実例

```python
# Extension開発者向け: Rust高速化は透過的

# Before (pure Python)
batch = SessionCompiler.compile(session)

# After (with Rust, automatic)
batch = SessionCompiler.compile(session)  # 自動で高速版使用

# Extension code は変更不要！
class MyExtension(BaseExtension):
    def transform(self, payload):
        # このコードは変更なし
        return payload
```

---

## ❓ FAQ

### Q1: 既存の拡張は動き続けますか？

**A:** はい、完全な後方互換性があります。
- Extension APIは変更なし
- Rustは内部実装の最適化のみ
- 拡張開発者は何も変更不要

### Q2: Rustがビルドできない環境では？

**A:** 自動的にPure Pythonにフォールバック
```python
try:
    from oiduna_session_rust import RustSessionCompiler
except ImportError:
    # Pure Python fallback (automatic)
    pass
```

### Q3: パフォーマンス測定はどうする？

**A:** 標準ベンチマークを使用
```bash
uv run pytest packages/oiduna_session/tests/benchmark_compile.py -v
```

### Q4: ループエンジンをRust化しないのはなぜ？

**A:** すでに高速で、Python asyncioで十分
- ループエンジン: 2ms/step（問題なし）
- データ変換: 30ms/compile（ボトルネック）
- 正しいボトルネックを最適化する

---

## 🎯 まとめ

**Rust高速化の本質:**

1. **焦点:** データ変換（ループエンジンではない）
2. **優先順位:** SessionCompiler > MessageScheduler
3. **保持:** Python拡張フレームワーク
4. **効果:** 10-20倍高速化、GIL問題解消
5. **透過性:** 拡張開発者は何も変更不要

**Golden Rule:**
> "Optimize the right bottleneck with the right tool"

Rust = データ処理の高速化
Python = 柔軟な拡張フレームワーク

---

**作成者:** Claude Sonnet 4.5
**最終更新:** 2026-02-28
**関連:** [ADR-0011](knowledge/adr/0011-rust-acceleration-strategy.md)
