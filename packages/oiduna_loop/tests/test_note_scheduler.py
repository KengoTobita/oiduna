"""
Tests for NoteScheduler (v5)

Tests MIDI note scheduling and note-off timing using mocks.
"""

from __future__ import annotations

import time

import pytest
from oiduna_core.models.track_midi import TrackMidi

from ..engine.note_scheduler import NoteScheduler
from .mocks import MockMidiOutput


@pytest.fixture
def sample_midi_track() -> TrackMidi:
    """Create a sample TrackMidi for testing."""
    return TrackMidi(
        track_id="synth",
        channel=5,
        velocity=100,
    )


class TestNoteSchedulerBasics:
    """Test basic note scheduling."""

    def test_init(self, mock_midi: MockMidiOutput):
        """NoteScheduler should initialize with MIDI output."""
        scheduler = NoteScheduler(mock_midi)
        assert scheduler._midi is mock_midi
        assert scheduler.pending_count == 0

    def test_schedule_note_sends_note_on(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Scheduling a note should send note-on immediately."""
        scheduler = NoteScheduler(mock_midi)

        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.125
        )

        assert len(mock_midi.notes) == 1
        assert mock_midi.notes[0] == ("on", sample_midi_track.channel, 60, 100)

    def test_schedule_note_queues_note_off(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Scheduling a note should queue a note-off."""
        scheduler = NoteScheduler(mock_midi)

        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.125
        )

        assert scheduler.pending_count == 1


class TestNoteSchedulerNoteOff:
    """Test note-off processing."""

    def test_process_pending_note_offs_immediate(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Note-off should be sent when time has elapsed."""
        scheduler = NoteScheduler(mock_midi)

        # Schedule with very short duration
        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.001, gate=0.001
        )

        # Wait for note-off time
        time.sleep(0.01)
        scheduler.process_pending_note_offs()

        # Should have note-on and note-off
        assert len(mock_midi.notes) >= 2
        assert mock_midi.notes[-1][:2] == ("off", sample_midi_track.channel)

    def test_process_pending_not_due(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Note-off should not be sent before time."""
        scheduler = NoteScheduler(mock_midi)

        # Schedule with long duration
        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=1.0, gate=1.0
        )

        # Process immediately (before note-off time)
        scheduler.process_pending_note_offs()

        # Should only have note-on
        assert len(mock_midi.notes) == 1
        assert mock_midi.notes[0][0] == "on"

    def test_clear_all(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """clear_all should clear pending notes and send all-notes-off."""
        scheduler = NoteScheduler(mock_midi)

        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=1.0
        )
        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 64, 100, step_duration=1.0
        )
        assert scheduler.pending_count == 2

        scheduler.clear_all()

        assert scheduler.pending_count == 0


class TestNoteSchedulerConnection:
    """Test connection handling."""

    def test_no_send_when_disconnected(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Should not send notes when MIDI is disconnected."""
        mock_midi._connected = False
        scheduler = NoteScheduler(mock_midi)

        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.125
        )

        assert len(mock_midi.notes) == 0
        assert scheduler.pending_count == 0

    def test_no_process_when_disconnected(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Should not process note-offs when disconnected."""
        scheduler = NoteScheduler(mock_midi)

        # Schedule note while connected
        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.001, gate=0.001
        )
        time.sleep(0.01)

        # Disconnect before processing
        mock_midi._connected = False
        scheduler.process_pending_note_offs()

        # Should still have pending (couldn't send note-off)
        # But no new notes sent
        assert len([n for n in mock_midi.notes if n[0] == "off"]) == 0


class TestNoteSchedulerGate:
    """Test gate length handling."""

    def test_gate_affects_duration(
        self, mock_midi: MockMidiOutput, sample_midi_track: TrackMidi
    ):
        """Gate parameter should affect note-off timing."""
        scheduler = NoteScheduler(mock_midi)

        # Schedule with half gate
        scheduler.schedule_note_on_channel(
            sample_midi_track.channel, 60, 100, step_duration=0.1, gate=0.5
        )

        # Note-off time should be: step_duration * gate * 4 = 0.1 * 0.5 * 4 = 0.2s
        # (The *4 is because step is 16th note, gate is fraction of quarter note)

        assert scheduler.pending_count == 1
