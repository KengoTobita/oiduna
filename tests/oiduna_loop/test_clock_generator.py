"""
Tests for ClockGenerator
"""

from unittest.mock import Mock

import pytest
from oiduna_loop.engine.clock_generator import ClockGenerator


class TestClockGeneratorConstants:
    """Test clock generator constants"""

    def test_midi_ppq(self):
        assert ClockGenerator.MIDI_PPQ == 24

    def test_pulses_per_step(self):
        # 24 PPQ / 4 steps per quarter = 6
        assert ClockGenerator.PULSES_PER_STEP == 6


class TestClockGeneratorPureFunctions:
    """Test pure functions in ClockGenerator"""

    def test_calculate_pulse_duration_120bpm(self):
        # At 120 BPM:
        # - Step duration = 60 / 120 / 4 = 0.125 seconds
        # - Pulse duration = 0.125 / 6 = 0.0208333...
        midi_sender = Mock()
        clock = ClockGenerator(midi_sender)

        step_duration = 0.125  # 120 BPM
        pulse_duration = clock.calculate_pulse_duration(step_duration)

        assert pulse_duration == pytest.approx(0.125 / 6)

    def test_calculate_pulse_duration_60bpm(self):
        # At 60 BPM:
        # - Step duration = 60 / 60 / 4 = 0.25 seconds
        # - Pulse duration = 0.25 / 6
        midi_sender = Mock()
        clock = ClockGenerator(midi_sender)

        step_duration = 0.25  # 60 BPM
        pulse_duration = clock.calculate_pulse_duration(step_duration)

        assert pulse_duration == pytest.approx(0.25 / 6)

    def test_calculate_pulse_duration_140bpm(self):
        # At 140 BPM:
        # - Step duration = 60 / 140 / 4 = 0.107142857...
        midi_sender = Mock()
        clock = ClockGenerator(midi_sender)

        step_duration = 60.0 / 140.0 / 4
        pulse_duration = clock.calculate_pulse_duration(step_duration)

        expected = step_duration / 6
        assert pulse_duration == pytest.approx(expected)


class TestClockGeneratorMidiCommands:
    """Test MIDI command delegation"""

    def test_send_start_when_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = True
        clock = ClockGenerator(midi_sender)

        clock.send_start()

        midi_sender.send_start.assert_called_once()

    def test_send_start_when_not_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = False
        clock = ClockGenerator(midi_sender)

        clock.send_start()

        midi_sender.send_start.assert_not_called()

    def test_send_stop_when_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = True
        clock = ClockGenerator(midi_sender)

        clock.send_stop()

        midi_sender.send_stop.assert_called_once()

    def test_send_stop_when_not_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = False
        clock = ClockGenerator(midi_sender)

        clock.send_stop()

        midi_sender.send_stop.assert_not_called()

    def test_send_continue_when_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = True
        clock = ClockGenerator(midi_sender)

        clock.send_continue()

        midi_sender.send_continue.assert_called_once()

    def test_send_continue_when_not_connected(self):
        midi_sender = Mock()
        midi_sender.is_connected = False
        clock = ClockGenerator(midi_sender)

        clock.send_continue()

        midi_sender.send_continue.assert_not_called()
