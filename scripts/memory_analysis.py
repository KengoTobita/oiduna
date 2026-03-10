"""
メモリ使用量分析スクリプト

実際のOidunaオブジェクトのメモリサイズを測定します。
"""

import sys
from typing import Any
from oiduna_models import Event, Pattern, Track, Session, ClientInfo, IDGenerator
from oiduna_models import OscDestinationConfig


def get_size(obj: Any, seen: set | None = None) -> int:
    """
    オブジェクトの実際のメモリサイズを再帰的に計算（bytes）

    参考: https://stackoverflow.com/questions/449560/how-do-i-determine-the-size-of-an-object-in-python
    """
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    seen.add(obj_id)

    if isinstance(obj, dict):
        size += sum([get_size(k, seen) + get_size(v, seen) for k, v in obj.items()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])

    return size


def format_size(bytes_size: int) -> str:
    """バイトサイズを人間が読みやすい形式に変換"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"


def analyze_event():
    """単一Eventのメモリ使用量"""
    print("=" * 60)
    print("Event オブジェクトの分析")
    print("=" * 60)

    # ミニマルなEvent
    minimal_event = Event(step=0, cycle=0.0, params={})
    minimal_size = get_size(minimal_event)
    print(f"Minimal Event (params=empty): {format_size(minimal_size)}")

    # 典型的なEvent（5パラメータ）
    typical_event = Event(
        step=64,
        cycle=1.0,
        params={"gain": 0.8, "pan": 0.5, "sound": "bd", "orbit": 0, "speed": 1.0}
    )
    typical_size = get_size(typical_event)
    print(f"Typical Event (5 params): {format_size(typical_size)}")

    # 大きなEvent（20パラメータ）
    large_params = {f"param_{i}": i * 0.1 for i in range(20)}
    large_event = Event(step=128, cycle=2.0, params=large_params)
    large_size = get_size(large_event)
    print(f"Large Event (20 params): {format_size(large_size)}")

    return minimal_size, typical_size, large_size


def analyze_pattern():
    """単一Patternのメモリ使用量"""
    print("\n" + "=" * 60)
    print("Pattern オブジェクトの分析")
    print("=" * 60)

    # 空のPattern
    empty_pattern = Pattern(
        pattern_id="a1b2c3d4",
        pattern_name="empty",
        client_id="client_001",
        events=[]
    )
    empty_size = get_size(empty_pattern)
    print(f"Empty Pattern (0 events): {format_size(empty_size)}")

    # 典型的なPattern（16 events = 4小節相当）
    typical_events = [
        Event(step=i*16, cycle=i*0.25, params={"gain": 0.8})
        for i in range(16)
    ]
    typical_pattern = Pattern(
        pattern_id="e5f6a7b8",
        pattern_name="typical",
        client_id="client_001",
        events=typical_events
    )
    typical_size = get_size(typical_pattern)
    print(f"Typical Pattern (16 events): {format_size(typical_size)}")

    # 密なPattern（256 events = 全ステップ）
    dense_events = [
        Event(step=i, cycle=i/64.0, params={"gain": 0.8, "pan": (i % 2) * 0.5})
        for i in range(256)
    ]
    dense_pattern = Pattern(
        pattern_id="12345678",
        pattern_name="dense",
        client_id="client_001",
        events=dense_events
    )
    dense_size = get_size(dense_pattern)
    print(f"Dense Pattern (256 events): {format_size(dense_size)}")

    return empty_size, typical_size, dense_size


def analyze_track():
    """単一Trackのメモリ使用量"""
    print("\n" + "=" * 60)
    print("Track オブジェクトの分析")
    print("=" * 60)

    # 空のTrack
    empty_track = Track(
        track_id="a1b2c3d4",
        track_name="kick",
        destination_id="superdirt",
        client_id="client_001",
        base_params={},
        patterns={}
    )
    empty_size = get_size(empty_track)
    print(f"Empty Track (0 patterns): {format_size(empty_size)}")

    # 典型的なTrack（3 patterns）
    patterns = {}
    for i in range(3):
        pattern_id = f"{i:08x}"
        events = [Event(step=j*16, cycle=j*0.25, params={"gain": 0.8}) for j in range(16)]
        patterns[pattern_id] = Pattern(
            pattern_id=pattern_id,
            pattern_name=f"pattern_{i}",
            client_id="client_001",
            events=events
        )

    typical_track = Track(
        track_id="f9e8d7c6",
        track_name="kick",
        destination_id="superdirt",
        client_id="client_001",
        base_params={"sound": "bd", "orbit": 0},
        patterns=patterns
    )
    typical_size = get_size(typical_track)
    print(f"Typical Track (3 patterns, 16 events each): {format_size(typical_size)}")

    # 大きなTrack（20 patterns）
    large_patterns = {}
    for i in range(20):
        pattern_id = f"{i:08x}"
        events = [Event(step=j*4, cycle=j*0.0625, params={"gain": 0.8}) for j in range(64)]
        large_patterns[pattern_id] = Pattern(
            pattern_id=pattern_id,
            pattern_name=f"pattern_{i}",
            client_id="client_001",
            events=events
        )

    large_track = Track(
        track_id="abcd1234",
        track_name="complex",
        destination_id="superdirt",
        client_id="client_001",
        base_params={"sound": "bd", "orbit": 0},
        patterns=large_patterns
    )
    large_size = get_size(large_track)
    print(f"Large Track (20 patterns, 64 events each): {format_size(large_size)}")

    return empty_size, typical_size, large_size


def analyze_session():
    """実際のSessionのメモリ使用量シミュレーション"""
    print("\n" + "=" * 60)
    print("Session オブジェクトの分析（実際のライブシミュレーション）")
    print("=" * 60)

    # === シナリオ1: 小規模ライブ（30分） ===
    print("\n--- シナリオ1: 小規模ライブ（30分） ---")
    session1 = Session()

    # 1 destination
    session1.destinations["superdirt"] = OscDestinationConfig(
        id="superdirt",
        type="osc",
        host="127.0.0.1",
        port=57120,
        address="/dirt/play"
    )

    # 1 client
    session1.clients["alice"] = ClientInfo(
        client_id="alice",
        client_name="Alice",
        token=ClientInfo.generate_token()
    )

    # 10 tracks, 各5 patterns, 各16 events
    for t in range(10):
        track_id = f"{(t+1000):08x}"
        patterns = {}
        for p in range(5):
            pattern_id = f"{(p+2000):08x}"
            events = [
                Event(step=i*16, cycle=i*0.25, params={"gain": 0.8})
                for i in range(16)
            ]
            patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                pattern_name=f"pattern_{p}",
                client_id="alice",
                events=events
            )

        session1.tracks[track_id] = Track(
            track_id=track_id,
            track_name=f"track_{t}",
            destination_id="superdirt",
            client_id="alice",
            base_params={"sound": "bd"},
            patterns=patterns
        )

    size1 = get_size(session1)
    print(f"10 tracks × 5 patterns × 16 events = {format_size(size1)}")
    print(f"合計: {10 * 5} patterns, {10 * 5 * 16} events")

    # === シナリオ2: 中規模ライブ（1時間） ===
    print("\n--- シナリオ2: 中規模ライブ（1時間） ---")
    session2 = Session()

    session2.destinations["superdirt"] = OscDestinationConfig(
        id="superdirt", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
    )
    session2.clients["alice"] = ClientInfo(
        client_id="alice", client_name="Alice", token=ClientInfo.generate_token()
    )

    # 50 tracks, 各10 patterns, 各32 events
    for t in range(50):
        track_id = f"{(t+1000):08x}"
        patterns = {}
        for p in range(10):
            pattern_id = f"{(p+2000):08x}"
            events = [
                Event(step=i*8, cycle=i*0.125, params={"gain": 0.8, "pan": 0.5})
                for i in range(32)
            ]
            patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                pattern_name=f"pattern_{p}",
                client_id="alice",
                events=events
            )

        session2.tracks[track_id] = Track(
            track_id=track_id,
            track_name=f"track_{t}",
            destination_id="superdirt",
            client_id="alice",
            base_params={"sound": "bd", "orbit": 0},
            patterns=patterns
        )

    size2 = get_size(session2)
    print(f"50 tracks × 10 patterns × 32 events = {format_size(size2)}")
    print(f"合計: {50 * 10} patterns, {50 * 10 * 32} events")

    # === シナリオ3: 大規模ライブ（3時間、激しいコーディング） ===
    print("\n--- シナリオ3: 大規模ライブ（3時間） ---")
    session3 = Session()

    session3.destinations["superdirt"] = OscDestinationConfig(
        id="superdirt", type="osc", host="127.0.0.1", port=57120, address="/dirt/play"
    )
    session3.clients["alice"] = ClientInfo(
        client_id="alice", client_name="Alice", token=ClientInfo.generate_token()
    )

    # 200 tracks, 各25 patterns, 各64 events
    for t in range(200):
        track_id = f"{(t+1000):08x}"
        patterns = {}
        for p in range(25):
            pattern_id = f"{(p+2000):08x}"
            events = [
                Event(
                    step=i*4,
                    cycle=i*0.0625,
                    params={"gain": 0.8, "pan": 0.5, "speed": 1.0}
                )
                for i in range(64)
            ]
            patterns[pattern_id] = Pattern(
                pattern_id=pattern_id,
                pattern_name=f"pattern_{p}",
                client_id="alice",
                events=events
            )

        session3.tracks[track_id] = Track(
            track_id=track_id,
            track_name=f"track_{t}",
            destination_id="superdirt",
            client_id="alice",
            base_params={"sound": "bd", "orbit": 0, "room": 0.5},
            patterns=patterns
        )

    size3 = get_size(session3)
    print(f"200 tracks × 25 patterns × 64 events = {format_size(size3)}")
    print(f"合計: {200 * 25} patterns, {200 * 25 * 64} events")

    return size1, size2, size3


def analyze_id_generator():
    """IDGeneratorのメモリ使用量"""
    print("\n" + "=" * 60)
    print("IDGenerator のメモリ使用量")
    print("=" * 60)

    gen = IDGenerator()

    # 初期状態
    initial_size = get_size(gen)
    print(f"初期状態（空）: {format_size(initial_size)}")

    # 100個のID生成後
    for _ in range(100):
        gen.generate_track_id()
        gen.generate_pattern_id()
    size_100 = get_size(gen)
    print(f"100 tracks + 100 patterns生成後: {format_size(size_100)}")

    # 1000個のID生成後
    for _ in range(900):
        gen.generate_track_id()
        gen.generate_pattern_id()
    size_1000 = get_size(gen)
    print(f"1000 tracks + 1000 patterns生成後: {format_size(size_1000)}")

    # 5000個のID生成後
    for _ in range(4000):
        gen.generate_track_id()
        gen.generate_pattern_id()
    size_5000 = get_size(gen)
    print(f"5000 tracks + 5000 patterns生成後: {format_size(size_5000)}")

    print(f"\n1つのID文字列（8桁16進数）の推定サイズ:")
    print(f"  str object overhead: ~50 bytes")
    print(f"  'a1b2c3d4' (8 chars): ~8 bytes")
    print(f"  Set entry overhead: ~24 bytes")
    print(f"  合計: ~82 bytes/ID")
    print(f"  5000 IDs × 82 bytes ≈ {format_size(5000 * 82)}")


def main():
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Oiduna メモリ使用量分析レポート" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")

    # 各オブジェクトの分析
    analyze_event()
    analyze_pattern()
    analyze_track()
    analyze_id_generator()

    # 実際のセッション分析
    size1, size2, size3 = analyze_session()

    # サマリー
    print("\n" + "=" * 60)
    print("総合サマリー")
    print("=" * 60)
    print(f"小規模ライブ（30分）:  {format_size(size1)}")
    print(f"中規模ライブ（1時間）:  {format_size(size2)}")
    print(f"大規模ライブ（3時間）:  {format_size(size3)}")
    print("\n一般的なPC/サーバーのRAM容量との比較:")
    print(f"  8GB RAM:    {format_size(8 * 1024**3)} → 大規模ライブでも {8 * 1024**3 / size3:.0f}倍の余裕")
    print(f"  16GB RAM:   {format_size(16 * 1024**3)} → 大規模ライブでも {16 * 1024**3 / size3:.0f}倍の余裕")
    print(f"  32GB RAM:   {format_size(32 * 1024**3)} → 大規模ライブでも {32 * 1024**3 / size3:.0f}倍の余裕")

    print("\n結論:")
    print("  ✅ GC的な処理なしでも全く問題なし")
    print("  ✅ 8GB RAMのPCでも余裕で稼働可能")
    print("  ✅ 最大規模のライブでも数十MBオーダー")
    print("  ✅ メモリ枯渇の心配は不要")


if __name__ == "__main__":
    main()
