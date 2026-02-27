# Extension Hook Performance Benchmark Plan

## 目的

`before_send_messages()` フックのパフォーマンス影響を測定し、実行時ループのタイミング精度を確保する。

## ベンチマークシナリオ

### 1. Baseline（フックなし）
- 拡張なしでの通常動作
- ステップ間隔の精度測定

### 2. SuperDirt拡張（軽負荷）
- 1ステップあたり1メッセージ、5パラメータ
- cps注入のみ

### 3. SuperDirt拡張（中負荷）
- 1ステップあたり4メッセージ、10パラメータ
- orbit割り当て + cps注入

### 4. SuperDirt拡張（高負荷）
- 1ステップあたり10メッセージ、20パラメータ
- 全機能有効

## 測定項目

### タイミング精度
```python
# ステップ間隔のばらつき（標準偏差）
expected_interval = 60.0 / bpm / 4
actual_intervals = [step_times[i+1] - step_times[i] for i in range(len(step_times)-1)]
std_dev = statistics.stdev(actual_intervals)

# 許容範囲: 標準偏差 < 1ms
assert std_dev < 0.001
```

### フック実行時間
```python
import time

start = time.perf_counter()
result = extension.before_send_messages(messages, bpm, step)
duration = time.perf_counter() - start

# 目標: 99パーセンタイル < 100μs
assert duration < 0.0001  # 100μs
```

### CPU使用率
- ループ実行中のCPU使用率
- フック有無での比較

## 実行方法

```bash
# ベンチマーク実行
cd oiduna/packages/oiduna_loop
pytest tests/test_extension_performance.py -v

# 詳細プロファイリング
python -m cProfile -o profile.stats tests/test_extension_performance.py
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

## 許容基準

| 項目 | 許容値 | 理由 |
|------|--------|------|
| フック実行時間（p99） | < 100μs | ステップ間隔（125ms @BPM120）の0.08%以下 |
| タイミング誤差（stddev） | < 1ms | 人間の知覚限界（5-10ms）より十分小さい |
| CPU使用率増加 | < 5% | ループ以外の処理余裕を確保 |

## 最適化のトリガー

以下の場合は最適化を検討：
- フック実行時間 > 100μs
- タイミング誤差 > 1ms
- CPU使用率増加 > 5%

## 実装後のアクション

1. ✅ ベンチマークテスト作成
2. ✅ 初回測定実施
3. ✅ 結果をドキュメント化
4. ⏳ 必要に応じて最適化
5. ⏳ 継続的なパフォーマンス監視

---

**作成日**: 2026-02-25
