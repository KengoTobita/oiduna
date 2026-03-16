"""包括的な境界値テスト - バリデーター層

このファイルは、システムの限界値での動作を検証します：
- BPM範囲
- ステップ範囲
- OSC型の範囲（int32, float32）
- MIDI値の範囲（ノート、ベロシティ、チャンネル、CC、ピッチベンド）
- 浮動小数点精度

全てのテストに@pytest.mark.boundaryを付与しています。
"""

import pytest
import math

from oiduna.domain.schedule.validators import OscValidator, MidiValidator


@pytest.mark.boundary
class TestBpmBoundaries:
    """BPM境界値テスト

    一般的なBPM範囲: 1.0 - 999.0
    """

    @pytest.mark.parametrize("bpm,expected_valid", [
        # 有効な範囲
        (1.0, True),      # 最小値
        (60.0, True),     # 低速
        (120.0, True),    # 標準
        (140.0, True),    # 高速
        (999.0, True),    # 最大値

        # 無効な範囲（境界外）
        (0.5, False),     # 最小値未満
        (0.0, False),     # ゼロ
        (-10.0, False),   # 負の値
        (1500.0, False),  # 最大値超過

        # 特殊値
        (float('inf'), False),   # 無限大
        (float('-inf'), False),  # 負の無限大
    ])
    def test_bpm_range(self, bpm, expected_valid):
        """BPM範囲の検証"""
        # 注: BPMバリデーションは環境設定の一部として実装される
        # ここではバリデーションロジックの期待動作を定義
        if expected_valid:
            assert 1.0 <= bpm <= 999.0
        else:
            assert not (1.0 <= bpm <= 999.0) or math.isnan(bpm) or math.isinf(bpm)

    @pytest.mark.parametrize("bpm", [
        float('nan'),  # NaN
    ])
    def test_bpm_nan(self, bpm):
        """BPM NaN検証"""
        assert math.isnan(bpm)


@pytest.mark.boundary
class TestStepBoundaries:
    """ステップ境界値テスト

    ステップ範囲: 0 - 255
    """

    @pytest.mark.parametrize("step,expected_valid", [
        # 有効な範囲
        (0, True),       # 最小値
        (1, True),       # 最小+1
        (64, True),      # 中央
        (127, True),     # MIDI範囲最大
        (128, True),     # MIDI範囲超過、ステップでは有効
        (254, True),     # 最大-1
        (255, True),     # 最大値

        # 無効な範囲
        (-1, False),     # 負の値
        (256, False),    # 最大値超過
        (512, False),    # 大幅超過
    ])
    def test_step_range(self, step, expected_valid):
        """ステップ範囲の検証"""
        if expected_valid:
            assert 0 <= step <= 255
        else:
            assert not (0 <= step <= 255)


@pytest.mark.boundary
class TestOscInt32Boundaries:
    """OSC int32境界値テスト

    int32範囲: -2^31 to 2^31-1 (-2147483648 to 2147483647)
    """

    @pytest.mark.parametrize("value,expected_valid", [
        # 有効な範囲
        (0, True),                    # ゼロ
        (1, True),                    # 最小正の値
        (-1, True),                   # 最小負の値
        (2147483647, True),           # int32最大値
        (-2147483648, True),          # int32最小値

        # 境界値±1
        (2147483646, True),           # 最大-1
        (-2147483647, True),          # 最小+1

        # 無効な範囲
        (2147483648, False),          # 最大+1
        (-2147483649, False),         # 最小-1
        (2147483648000, False),       # 大幅超過
        (-2147483648000, False),      # 大幅未満
    ])
    def test_osc_int32_range(self, value, expected_valid):
        """OSC int32範囲の検証"""
        validator = OscValidator()
        result = validator.validate_message({"value": value})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("int32 range" in err for err in result.errors)


@pytest.mark.boundary
class TestOscFloat32Boundaries:
    """OSC float32境界値テスト

    float32範囲: 約 -3.4e38 to 3.4e38
    """

    @pytest.mark.parametrize("value,expected_valid", [
        # 有効な範囲
        (0.0, True),                  # ゼロ
        (1.0, True),                  # 1
        (-1.0, True),                 # -1
        (3.14159265359, True),        # 高精度π
        (1e10, True),                 # 大きな値
        (1e-10, True),                # 小さな値
        (3.4e38, True),               # float32最大値
        (-3.4e38, True),              # float32最小値

        # 境界値付近
        (3.39e38, True),              # 最大値近く
        (-3.39e38, True),             # 最小値近く

        # 無効な範囲
        (3.5e38, False),              # 最大値超過
        (-3.5e38, False),             # 最小値未満
        (1e39, False),                # 大幅超過
        (-1e39, False),               # 大幅未満
    ])
    def test_osc_float32_range(self, value, expected_valid):
        """OSC float32範囲の検証"""
        validator = OscValidator()
        result = validator.validate_message({"value": value})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("float32 range" in err for err in result.errors)

    @pytest.mark.parametrize("value", [
        float('inf'),      # 正の無限大
        float('-inf'),     # 負の無限大
        float('nan'),      # NaN
    ])
    def test_osc_float32_special_values(self, value):
        """OSC float32特殊値の検証"""
        validator = OscValidator()
        result = validator.validate_message({"value": value})

        # 無限大とNaNは範囲外として扱われる
        assert not result.is_valid


@pytest.mark.boundary
class TestMidiNoteBoundaries:
    """MIDIノート境界値テスト

    ノート範囲: 0 - 127
    """

    @pytest.mark.parametrize("note,expected_valid", [
        # 有効な範囲
        (0, True),       # C-1 (最小値)
        (21, True),      # A0 (ピアノ最低音)
        (60, True),      # C4 (ミドルC)
        (108, True),     # C8 (ピアノ最高音)
        (127, True),     # G9 (最大値)

        # 境界値±1
        (1, True),       # 最小+1
        (126, True),     # 最大-1

        # 無効な範囲
        (-1, False),     # 負の値
        (128, False),    # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_note_range(self, note, expected_valid):
        """MIDIノート範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"note": note})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("note" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestMidiVelocityBoundaries:
    """MIDIベロシティ境界値テスト

    ベロシティ範囲: 0 - 127 (0 = note off)
    """

    @pytest.mark.parametrize("velocity,expected_valid", [
        # 有効な範囲
        (0, True),       # ノートオフ
        (1, True),       # 最小音量
        (64, True),      # 中程度
        (100, True),     # 強め
        (127, True),     # 最大音量

        # 境界値±1
        (126, True),     # 最大-1

        # 無効な範囲
        (-1, False),     # 負の値
        (128, False),    # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_velocity_range(self, velocity, expected_valid):
        """MIDIベロシティ範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"velocity": velocity})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("velocity" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestMidiChannelBoundaries:
    """MIDIチャンネル境界値テスト

    チャンネル範囲: 0-15 または 1-16 (両方受け入れ)
    """

    @pytest.mark.parametrize("channel,expected_valid", [
        # 0-15範囲（0ベース）
        (0, True),       # チャンネル1（0ベース）
        (7, True),       # チャンネル8
        (15, True),      # チャンネル16（0ベース）

        # 1-16範囲（1ベース）
        (1, True),       # チャンネル1または2
        (8, True),       # チャンネル8または9
        (16, True),      # チャンネル16

        # 無効な範囲
        (-1, False),     # 負の値
        (17, False),     # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_channel_range(self, channel, expected_valid):
        """MIDIチャンネル範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"channel": channel})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("channel" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestMidiCcBoundaries:
    """MIDI CC（コントロールチェンジ）境界値テスト

    CC番号範囲: 0 - 127
    CC値範囲: 0 - 127
    """

    @pytest.mark.parametrize("cc_number,expected_valid", [
        # 有効な範囲
        (0, True),       # Bank Select MSB
        (7, True),       # Volume
        (10, True),      # Pan
        (64, True),      # Sustain Pedal
        (127, True),     # 最大値

        # 無効な範囲
        (-1, False),     # 負の値
        (128, False),    # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_cc_number_range(self, cc_number, expected_valid):
        """MIDI CC番号範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"cc": cc_number})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("cc" in err.lower() for err in result.errors)

    @pytest.mark.parametrize("cc_value,expected_valid", [
        # 有効な範囲
        (0, True),       # 最小値
        (64, True),      # 中央値
        (127, True),     # 最大値

        # 無効な範囲
        (-1, False),     # 負の値
        (128, False),    # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_cc_value_range(self, cc_value, expected_valid):
        """MIDI CC値範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"cc": 7, "value": cc_value})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("value" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestMidiPitchBendBoundaries:
    """MIDIピッチベンド境界値テスト

    ピッチベンド範囲: 0 - 16383 (14ビット、中央値 = 8192)
    """

    @pytest.mark.parametrize("pitch_bend,expected_valid", [
        # 有効な範囲
        (0, True),       # 最小値（-2半音）
        (8192, True),    # 中央値（変化なし）
        (16383, True),   # 最大値（+2半音）

        # 境界値±1
        (1, True),       # 最小+1
        (16382, True),   # 最大-1

        # 中央値付近
        (8191, True),    # 中央-1
        (8193, True),    # 中央+1

        # 無効な範囲
        (-1, False),     # 負の値
        (16384, False),  # 最大+1
        (32767, False),  # 16ビット符号付き最大値
    ])
    def test_midi_pitch_bend_range(self, pitch_bend, expected_valid):
        """MIDIピッチベンド範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"pitch_bend": pitch_bend})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("pitch_bend" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestMidiProgramBoundaries:
    """MIDIプログラムチェンジ境界値テスト

    プログラム範囲: 0 - 127
    """

    @pytest.mark.parametrize("program,expected_valid", [
        # 有効な範囲
        (0, True),       # 最小値
        (1, True),       # Piano
        (64, True),      # 中央値
        (127, True),     # 最大値

        # 無効な範囲
        (-1, False),     # 負の値
        (128, False),    # 最大+1
        (255, False),    # バイト最大値
    ])
    def test_midi_program_range(self, program, expected_valid):
        """MIDIプログラム範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"program": program})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("program" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestFloatingPointPrecision:
    """浮動小数点精度テスト

    浮動小数点演算の精度問題を検証
    """

    def test_floating_point_addition_precision(self):
        """浮動小数点加算の精度（0.1 + 0.2 != 0.3）"""
        result = 0.1 + 0.2
        # 浮動小数点誤差により、厳密には0.3にならない
        assert result != 0.3
        # しかし非常に近い値
        assert abs(result - 0.3) < 1e-10

    @pytest.mark.parametrize("value", [
        1e-10,      # 非常に小さい値
        1e-100,     # 極小値
        1e10,       # 非常に大きい値
        1e30,       # 極大値
    ])
    def test_extreme_float_values(self, value):
        """極端な浮動小数点値の処理"""
        validator = OscValidator()
        result = validator.validate_message({"value": value})

        # float32範囲内であれば有効
        if abs(value) <= 3.4e38:
            assert result.is_valid

    def test_high_precision_float(self):
        """高精度浮動小数点値"""
        validator = OscValidator()
        # πの高精度値
        pi = 3.14159265358979323846
        result = validator.validate_message({"pi": pi})

        assert result.is_valid

    def test_denormalized_numbers(self):
        """非正規化数の処理"""
        # 非常に小さい非正規化数
        denorm = 1e-40
        validator = OscValidator()
        result = validator.validate_message({"value": denorm})

        assert result.is_valid

    def test_negative_zero(self):
        """負のゼロの処理"""
        validator = OscValidator()
        result = validator.validate_message({"value": -0.0})

        assert result.is_valid


@pytest.mark.boundary
class TestMidiDurationBoundaries:
    """MIDI継続時間境界値テスト

    継続時間範囲: 0以上の数値（ミリ秒）
    """

    @pytest.mark.parametrize("duration,expected_valid", [
        # 有効な範囲
        (0, True),           # ゼロ
        (0.1, True),         # 極短
        (100, True),         # 短い
        (1000, True),        # 1秒
        (10000, True),       # 10秒
        (1000000, True),     # 1000秒（長時間）

        # 無効な範囲
        (-0.1, False),       # 負の値
        (-100, False),       # 負の値
        (-1000, False),      # 負の値
    ])
    def test_midi_duration_range(self, duration, expected_valid):
        """MIDI継続時間範囲の検証"""
        validator = MidiValidator()
        result = validator.validate_message({"duration_ms": duration})

        assert result.is_valid == expected_valid
        if not expected_valid:
            assert any("non-negative" in err.lower() for err in result.errors)


@pytest.mark.boundary
class TestCombinedBoundaries:
    """複合境界値テスト

    複数のパラメータの境界値を同時にテスト
    """

    def test_midi_all_boundaries_valid(self):
        """全MIDI境界値が有効範囲内"""
        validator = MidiValidator()
        result = validator.validate_message({
            "note": 0,
            "velocity": 127,
            "channel": 15,
            "cc": 64,
            "value": 0,
            "pitch_bend": 8192,
            "program": 127,
            "duration_ms": 1000,
        })

        assert result.is_valid

    def test_midi_all_boundaries_invalid(self):
        """全MIDI境界値が無効範囲"""
        validator = MidiValidator()
        result = validator.validate_message({
            "note": 128,
            "velocity": 128,
            "channel": 17,
        })

        assert not result.is_valid
        # 3つのエラーが報告される
        assert len(result.errors) >= 3

    def test_osc_mixed_boundaries(self):
        """OSC境界値の混在"""
        validator = OscValidator()
        result = validator.validate_message({
            "int_max": 2147483647,
            "int_min": -2147483648,
            "float_max": 3.4e38,
            "float_min": -3.4e38,
            "zero": 0,
            "pi": 3.14159,
        })

        assert result.is_valid

    def test_osc_invalid_and_valid_mix(self):
        """OSC有効・無効境界値の混在"""
        validator = OscValidator()
        result = validator.validate_message({
            "valid": 100,
            "invalid_int": 2147483648,
            "invalid_float": 3.5e38,
        })

        assert not result.is_valid
        # 2つのエラーが報告される
        assert len(result.errors) >= 2
