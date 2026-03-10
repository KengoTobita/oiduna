"""Tests for RuntimeState (ScheduledMessageBatch architecture)."""

from oiduna_loop.state.runtime_state import (
    PlaybackState,
    Position,
    RuntimeState,
)
from oiduna_scheduler.scheduler_models import ScheduledMessage


class TestPosition:
    """Test Position dataclass."""

    def test_default_values(self) -> None:
        """Test default position values."""
        pos = Position()
        assert pos.step == 0
        assert pos.bar == 0
        assert pos.beat == 0

    def test_advance(self) -> None:
        """Test advancing position."""
        pos = Position()
        pos.advance(256)
        assert pos.step == 1
        assert pos.beat == 0
        assert pos.bar == 0

    def test_advance_beat_boundary(self) -> None:
        """Test advancing to beat boundary."""
        pos = Position(step=3)
        pos.advance(256)
        assert pos.step == 4
        assert pos.beat == 1
        assert pos.bar == 0

    def test_advance_bar_boundary(self) -> None:
        """Test advancing to bar boundary."""
        pos = Position(step=15)
        pos.advance(256)
        assert pos.step == 16
        assert pos.beat == 0
        assert pos.bar == 1

    def test_advance_wrap_around(self) -> None:
        """Test wrapping around at loop end."""
        pos = Position(step=255)
        pos.advance(256)
        assert pos.step == 0
        assert pos.beat == 0
        assert pos.bar == 0

    def test_reset(self) -> None:
        """Test resetting position."""
        pos = Position(step=100, bar=5, beat=2)
        pos.reset()
        assert pos.step == 0
        assert pos.bar == 0
        assert pos.beat == 0

    def test_to_dict(self) -> None:
        """Test converting position to dict."""
        pos = Position(step=16, bar=1, beat=0)
        d = pos.to_dict()
        assert d["step"] == 16
        assert d["bar"] == 1
        assert d["beat"] == 0
        assert "timestamp" in d


class TestRuntimeStateBasics:
    """Test basic RuntimeState functionality."""

    def test_default_values(self) -> None:
        """Test default state values."""
        state = RuntimeState()
        assert state.playback_state == PlaybackState.STOPPED
        assert state.position.step == 0
        assert state.bpm == 120.0
        assert state.step_duration > 0
        assert state.cps > 0

    def test_playing_property(self) -> None:
        """Test playing property."""
        state = RuntimeState()
        assert not state.playing

        state.playback_state = PlaybackState.PLAYING
        assert state.playback_state == PlaybackState.PLAYING
        assert state.playing

        state.playback_state = PlaybackState.PAUSED
        assert state.playback_state == PlaybackState.PAUSED
        assert not state.playing

    def test_set_bpm(self) -> None:
        """Test BPM setting."""
        state = RuntimeState()
        state.set_bpm(140.0)
        assert state.bpm == 140.0

        # Test timing calculations updated
        assert state.step_duration == 60.0 / 140.0 / 4
        assert state.cps == 140.0 / 60.0 / 4

    def test_bpm_clamping(self) -> None:
        """Test BPM is clamped to valid range."""
        state = RuntimeState()

        state.set_bpm(0.5)  # Too low
        assert state.bpm == 1.0

        state.set_bpm(1000.0)  # Too high
        assert state.bpm == 999.0

    def test_advance_step(self) -> None:
        """Test advancing step."""
        state = RuntimeState()
        assert state.position.step == 0

        state.advance_step()
        assert state.position.step == 1

    def test_reset_position(self) -> None:
        """Test resetting position."""
        state = RuntimeState()
        state.position.step = 100
        state.reset_position()
        assert state.position.step == 0


class TestTrackRegistration:
    """Test track registration for mute/solo filtering."""

    def test_register_track(self) -> None:
        """Test registering a track."""
        state = RuntimeState()
        state.register_track("kick")

        assert "kick" in state._known_track_ids
        assert state.is_track_active("kick")

    def test_register_multiple_tracks(self) -> None:
        """Test registering multiple tracks."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.register_track("snare")

        assert len(state._known_track_ids) == 3
        assert state.is_track_active("kick")
        assert state.is_track_active("hihat")
        assert state.is_track_active("snare")

    def test_unknown_track_inactive(self) -> None:
        """Test unknown tracks are inactive."""
        state = RuntimeState()
        assert not state.is_track_active("unknown")


class TestMuteFiltering:
    """Test mute filtering logic."""

    def test_set_track_mute(self) -> None:
        """Test muting a track."""
        state = RuntimeState()
        state.register_track("kick")

        result = state.set_track_mute("kick", True)
        assert result is True
        assert not state.is_track_active("kick")

    def test_set_track_mute_unknown_track(self) -> None:
        """Test muting unknown track returns False."""
        state = RuntimeState()
        result = state.set_track_mute("unknown", True)
        assert result is False

    def test_unmute_track(self) -> None:
        """Test unmuting a track."""
        state = RuntimeState()
        state.register_track("kick")
        state.set_track_mute("kick", True)

        state.set_track_mute("kick", False)
        assert state.is_track_active("kick")

    def test_filter_messages_no_mute(self) -> None:
        """Test filtering with no mute."""
        state = RuntimeState()
        state.register_track("kick")

        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "kick", "s": "bd"}
            )
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 1

    def test_filter_messages_with_mute(self) -> None:
        """Test filtering muted tracks."""
        state = RuntimeState()
        state.register_track("kick")
        state.set_track_mute("kick", True)

        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "kick", "s": "bd"}
            )
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 0  # Muted

    def test_filter_messages_mixed(self) -> None:
        """Test filtering with some tracks muted."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.set_track_mute("hihat", True)

        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "kick", "s": "bd"}
            ),
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "hihat", "s": "hh"}
            ),
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 1
        assert filtered[0].params["track_id"] == "kick"


class TestSoloFiltering:
    """Test solo filtering logic."""

    def test_set_track_solo(self) -> None:
        """Test soloing a track."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")

        result = state.set_track_solo("kick", True)
        assert result is True
        assert state.is_track_active("kick")
        assert not state.is_track_active("hihat")  # Not soloed

    def test_set_track_solo_unknown_track(self) -> None:
        """Test soloing unknown track returns False."""
        state = RuntimeState()
        result = state.set_track_solo("unknown", True)
        assert result is False

    def test_unsolo_track(self) -> None:
        """Test unsoloing a track."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.set_track_solo("kick", True)

        state.set_track_solo("kick", False)
        assert state.is_track_active("kick")
        assert state.is_track_active("hihat")

    def test_filter_messages_with_solo(self) -> None:
        """Test filtering with solo."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.set_track_solo("kick", True)

        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "kick", "s": "bd"}
            ),
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "hihat", "s": "hh"}
            ),
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 1
        assert filtered[0].params["track_id"] == "kick"

    def test_solo_overrides_mute(self) -> None:
        """Test solo takes priority over mute."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")

        # Mute kick, but also solo it
        state.set_track_mute("kick", True)
        state.set_track_solo("kick", True)

        # Solo overrides mute
        assert state.is_track_active("kick")
        assert not state.is_track_active("hihat")

    def test_multiple_solo_tracks(self) -> None:
        """Test multiple tracks can be soloed."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.register_track("snare")

        state.set_track_solo("kick", True)
        state.set_track_solo("hihat", True)

        assert state.is_track_active("kick")
        assert state.is_track_active("hihat")
        assert not state.is_track_active("snare")


class TestFilterMessagesEdgeCases:
    """Test edge cases for message filtering."""

    def test_filter_messages_without_track_id(self) -> None:
        """Test messages without track_id are not filtered."""
        state = RuntimeState()
        state.register_track("kick")
        state.set_track_mute("kick", True)

        # Message without track_id
        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"s": "bd"}  # No track_id
            )
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 1  # Not filtered

    def test_filter_messages_empty_list(self) -> None:
        """Test filtering empty message list."""
        state = RuntimeState()
        filtered = state.filter_messages([])
        assert len(filtered) == 0

    def test_filter_messages_unknown_track_id(self) -> None:
        """Test messages with unknown track_id are filtered out."""
        state = RuntimeState()
        state.register_track("kick")

        messages = [
            ScheduledMessage(
                destination_id="superdirt",
                cycle=0.0,
                step=0,
                params={"track_id": "unknown", "s": "bd"}
            )
        ]

        filtered = state.filter_messages(messages)
        assert len(filtered) == 0  # Unknown track_id = inactive


class TestGetActiveTracks:
    """Test get_active_track_ids method."""

    def test_get_active_track_ids_no_filtering(self) -> None:
        """Test getting active tracks with no filtering."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")

        active = state.get_active_track_ids()
        assert set(active) == {"kick", "hihat"}

    def test_get_active_track_ids_with_mute(self) -> None:
        """Test getting active tracks with mute."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.set_track_mute("hihat", True)

        active = state.get_active_track_ids()
        assert active == ["kick"]

    def test_get_active_track_ids_with_solo(self) -> None:
        """Test getting active tracks with solo."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.set_track_solo("kick", True)

        active = state.get_active_track_ids()
        assert active == ["kick"]


class TestStatusDict:
    """Test to_status_dict method."""

    def test_to_status_dict_basic(self) -> None:
        """Test basic status dict output."""
        state = RuntimeState()
        state.register_track("kick")

        status = state.to_status_dict()

        assert status["playing"] is False
        assert status["playback_state"] == "stopped"
        assert status["bpm"] == 120.0
        assert "position" in status
        assert status["active_tracks"] == ["kick"]
        assert status["known_tracks"] == ["kick"]
        assert status["muted_tracks"] == []
        assert status["soloed_tracks"] == []

    def test_to_status_dict_with_mute_solo(self) -> None:
        """Test status dict with mute/solo."""
        state = RuntimeState()
        state.register_track("kick")
        state.register_track("hihat")
        state.register_track("snare")
        state.set_track_mute("snare", True)
        state.set_track_solo("kick", True)

        status = state.to_status_dict()

        assert status["active_tracks"] == ["kick"]
        assert set(status["known_tracks"]) == {"kick", "hihat", "snare"}
        assert status["muted_tracks"] == ["snare"]
        assert status["soloed_tracks"] == ["kick"]
