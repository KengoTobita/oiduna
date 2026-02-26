# ADR-0003: Phase 1でのPythonタイミングエンジン継続

## ステータス

承認済み

## 日付

- 作成: 2026-02-22
- 承認: 2026-02-22

## コンテキスト

### 問題

Oiduna v2のロードマップでは、最終的に高精度タイミングエンジンをRustで実装する可能性が議論されています。Pythonのタイミング精度にはGIL（Global Interpreter Lock）やガベージコレクション（GC）による揺らぎがあり、理論的にはRustの方が優れています。

**Phase 1の実装で決定すべきこと：**
- Phase 1でRust化に着手するか、Pythonを継続するか
- どの部分をRustにするか（全体 vs 部分）
- 移行戦略をどうするか

### 制約

- **開発時間:** Phase 1は1週間以内に完了させる
- **開発者リソース:** 限定的（1人）
- **既存コードベース:** Pythonで約10,000行
- **技術的制約:** RustとPythonの相互運用にはFFI（Foreign Function Interface）が必要

### 要件

- **機能要件:**
  - 既存のパターン再生機能の維持
  - マルチコア処理との統合
  - リモートコントロールAPI

- **非機能要件:**
  - タイミング精度: ±5ms以内（現状で達成済み）
  - 開発速度: Phase 1完了まで1週間
  - 保守性: コードの理解・修正が容易

## 決定事項

**Phase 1ではPythonタイミングエンジンを継続し、Rust化はPhase 2以降で段階的に検討する。**

### 実装方針

1. **Phase 1（現在）:**
   - Pythonタイミングエンジンを維持
   - supernova統合、OSC確認プロトコル実装に集中
   - タイミング精度の測定・ベースライン確立

2. **Phase 2（将来）:**
   - タイミングエンジンのみRust化を検討
   - PyO3を使用してPython ↔ Rust連携
   - その他のロジック（API、パターン処理等）はPython維持

3. **Phase 3（さらに将来）:**
   - 必要に応じて段階的にRust化範囲を拡大
   - パフォーマンスボトルネックを特定してから判断

### Rust化の判断基準（Phase 2で評価）

以下の条件を**すべて**満たす場合のみRust化を実施：

1. **測定可能な問題:** タイミング揺らぎが±5msを超えるケースが頻発
2. **Pythonで解決不可:** Python最適化（asyncio、C拡張等）で解決できない
3. **コスト対効果:** 開発コスト（1-2ヶ月）に見合う改善が見込める
4. **移行リスク:** 段階的移行が可能で、後戻りも可能

**成功基準:**

- Phase 1の機能（supernova、リモートコントロール）を予定通り実装
- タイミング精度のベースライン測定完了
- Phase 2でのRust化判断材料が揃う

## 理由

### Phase 1でPythonを継続する理由

1. **開発速度優先:**
   - Phase 1の目標は「supernova統合」と「リモートコントロール」
   - Rust化は別の大規模プロジェクト（1-2ヶ月規模）
   - 限られた時間で両方は不可能

2. **現状のタイミング精度は十分:**
   - 現在±5ms以内を達成
   - ライブコーディング用途では許容範囲
   - 問題が顕在化していない段階での全面書き換えはリスク

3. **段階的アプローチ:**
   - まずsupernova統合でマルチコア処理を実現
   - 実測データを取得してからRust化の必要性を判断
   - 「最適化の第一原則: 測定してから最適化せよ」

4. **保守性:**
   - 既存チームがPythonに習熟
   - コードレビュー・修正が容易
   - 新規参加者のオンボーディングが簡単

5. **エコシステム:**
   - FastAPI、Pydantic等の豊富なライブラリ
   - SuperColliderとのOSC通信ライブラリ（pythonosc）が成熟
   - Rust版は自前実装が必要

### 将来的にRust化を検討する理由

1. **理論的な優位性:**
   - GIL・GCによる揺らぎがない
   - メモリ安全性
   - より厳密なタイミング制御

2. **プロフェッショナル用途:**
   - スタジオ録音等、より高精度が求められる用途への対応
   - 商用レベルの信頼性

3. **競合優位性:**
   - TidalCycles等の競合との差別化
   - 「高精度タイミングエンジン」としてのブランディング

## 代替案

### 案1: Phase 1でRust全面移行

**概要:** Phase 1でシステム全体をRustで書き直す

**長所:**
- 最終的な理想形を早期実現
- 段階的移行の複雑さを回避

**短所:**
- 開発期間が6ヶ月〜1年に延長
- SuperColliderエコシステムとの統合コスト
- FastAPI等のPythonライブラリが使えない
- 後戻りが困難

**却下理由:**
開発コストが高すぎ、Phase 1の目標達成が不可能。

### 案2: Phase 1でタイミングエンジンのみRust化

**概要:** タイミング部分だけRustで実装、PyO3でPythonと連携

**長所:**
- タイミング精度向上
- API等はPython維持で開発速度確保

**短所:**
- FFIの複雑性（デバッグ困難）
- Phase 1の期限内完了が困難
- 現時点でタイミング問題が顕在化していない

**却下理由:**
問題が明確でない段階での最適化は時期尚早。まず測定が必要。

### 案3: C拡張でタイミングエンジン実装

**概要:** Pythonの C API を使ってタイミング部分を実装

**長所:**
- Pythonとの統合が容易
- Rustより学習コスト低い

**短所:**
- メモリ安全性がRustより劣る
- モダンな言語機能がない
- Rustより性能劣る可能性

**却下理由:**
CよりRustの方が安全性・性能で優れる。Rust化するなら最初からRust。

## 影響

### プラスの影響

- **開発速度:** Phase 1を予定通り完了可能
- **リスク低減:** 既知の技術スタックで安定開発
- **柔軟性:** 実測データを見てから判断可能
- **段階的改善:** supernova統合だけでも性能向上

### マイナスの影響

- **理論的限界:** Pythonのタイミング精度限界（GIL、GC）
- **将来の移行コスト:** Rust化する場合は後から実装

### リスク

- **リスク:** Phase 2でRust化が必要になった際の移行コスト
  - **軽減策:** 段階的移行を前提とした設計、明確なインターフェース定義

- **リスク:** タイミング問題が後から顕在化
  - **軽減策:** Phase 1で精度測定、ベンチマーク確立

- **リスク:** 競合製品がRust化して性能差が開く
  - **軽減策:** supernova統合で当面の性能向上、Phase 2で再評価

### 移行コスト

- **Phase 1:** コストゼロ（既存コード継続）
- **Phase 2（Rust化する場合）:**
  - 工数: 1-2ヶ月
  - PyO3学習コスト
  - テスト・検証コスト

## 検証方法

### Phase 1での測定項目

1. **タイミング精度測定:**
   ```python
   # 期待タイミング vs 実際のOSC送信時刻
   jitter = actual_time - expected_time
   ```
   - 目標: ±5ms以内を95%以上のケースで達成

2. **レイテンシ測定:**
   - パターン送信 → SuperDirt出力までの遅延
   - 目標: <10ms

3. **長時間安定性:**
   - 1時間連続再生でタイミング揺らぎを記録
   - GCの影響を測定

4. **CPU使用率:**
   - タイミングエンジンのCPU使用率
   - ボトルネック特定

### Phase 2での判断基準

上記測定結果を元に、以下を評価：

- **問題の有無:** タイミング揺らぎが実用上問題になっているか
- **Python最適化の余地:** asyncio最適化、C拡張等で改善可能か
- **Rust化のコスト対効果:** 開発コストに見合う改善が見込めるか

**判断基準:**
- 揺らぎ >±5ms が頻発 → Rust化を検討
- 揺らぎ <±5ms → Python継続

## 関連するADR

- [ADR-0001: supernova マルチコア処理] - Phase 1の主要目標
- [ADR-0002: OSC確認プロトコル] - Phase 1の主要目標

## 参考資料

- [PyO3 - Rust bindings for Python](https://pyo3.rs/)
- [Python GIL and Timing](https://realpython.com/python-gil/)
- [Rust for Python Programmers](https://github.com/rochacbruno/py2rs)
- [TidalCycles Architecture](https://tidalcycles.org/docs/innards/architecture/)

## メモ

### Phase 2でのRust化アプローチ（検討中）

**オプション1: タイミングコアのみRust化**
```
Python (API, Pattern Processing)
    ↓ PyO3
Rust (Timing Engine)
    ↓ OSC
SuperCollider
```

**オプション2: 段階的全面移行**
```
Phase 2a: Timing Engine → Rust
Phase 2b: Pattern Processing → Rust
Phase 2c: API → Rust（Axum等）
```

**推奨:** オプション1（タイミングコアのみ）
- コスト低い
- Python資産を活用
- 後戻り可能

### 技術選択肢

- **FFI:** PyO3（Rust ↔ Python）
- **OSCライブラリ:** rosc（Rust）
- **タイミング:** tokio::time::interval（Rust）
- **ビルド:** maturin（PyO3プロジェクトビルド）

### 測定ツール

Phase 1で実装すべき測定ツール：

```python
# タイミング精度ロガー
class TimingLogger:
    def log_event(self, expected: float, actual: float):
        jitter = actual - expected
        self.jitters.append(jitter)

    def report(self):
        print(f"Mean jitter: {mean(self.jitters):.3f}ms")
        print(f"95th percentile: {percentile(self.jitters, 95):.3f}ms")
        print(f"Max jitter: {max(self.jitters):.3f}ms")
```

## 履歴

- 2026-02-22: 初稿作成（ステータス: 提案中）
- 2026-02-22: Phase 1実装方針確定により承認（ステータス: 承認済み）
