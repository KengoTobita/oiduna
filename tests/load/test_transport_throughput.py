"""Load tests for transport layer throughput.

Tests cover:
- MIDI clock timing stability
- High note density handling
- OSC message bursts
- Sustained message throughput
"""

import pytest
import time
from statistics import mean, stdev

from oiduna.infrastructure.transport.midi_sender import MidiSender
from oiduna.infrastructure.transport.osc_sender import OscSender


@pytest.mark.load
def test_midi_clock_stability(mock_mido):
    """Test MIDI clock timing stability at 120 BPM for 60 seconds.

    At 120 BPM, MIDI clock should send 48 pulses per quarter note = 96 pulses/second.

    Success criteria:
    - Send 5760 clock messages (60 seconds at 120 BPM)
    - Average timing jitter < 1ms
    - Max jitter < 5ms
    - No dropped messages
    """
    sender = MidiSender()
    sender.connect()

    port = mock_mido.get_port()
    assert port is not None

    # 120 BPM = 2 beats/sec = 96 pulses/sec
    # Inter-pulse interval = 1/96 = ~10.4ms
    bpm = 120.0
    pulses_per_second = (bpm / 60.0) * 24 * 2  # 24 pulses per quarter note
    interval = 1.0 / pulses_per_second

    duration = 60.0  # seconds
    num_pulses = int(duration * pulses_per_second)

    send_times = []
    start_time = time.perf_counter()

    for i in range(num_pulses):
        expected_time = start_time + (i * interval)

        # Wait until expected send time
        now = time.perf_counter()
        sleep_time = max(0, expected_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)

        # Send clock pulse
        send_start = time.perf_counter()
        sender.send_clock()
        send_times.append(send_start)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate timing jitter
    expected_times = [start_time + (i * interval) for i in range(num_pulses)]
    jitters = [abs(actual - expected) * 1000 for actual, expected in zip(send_times, expected_times)]

    avg_jitter = mean(jitters)
    max_jitter = max(jitters)
    jitter_stdev = stdev(jitters) if len(jitters) > 1 else 0

    messages = port.get_messages()
    clock_messages = [m for m in messages if m.type == "clock"]

    # Print metrics
    print(f"\n{'='*60}")
    print(f"MIDI Clock Stability Test (120 BPM, 60s)")
    print(f"{'='*60}")
    print(f"Pulses sent: {num_pulses}")
    print(f"Clock messages: {len(clock_messages)}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Expected time: {duration:.3f}s")
    print(f"Actual rate: {num_pulses / elapsed:.1f} pulses/s")
    print(f"Expected rate: {pulses_per_second:.1f} pulses/s")
    print(f"Avg jitter: {avg_jitter:.3f}ms")
    print(f"Jitter stdev: {jitter_stdev:.3f}ms")
    print(f"Max jitter: {max_jitter:.3f}ms")
    print(f"{'='*60}\n")

    # Assertions
    assert len(clock_messages) == num_pulses, f"Expected {num_pulses} clock messages, got {len(clock_messages)}"
    assert avg_jitter < 1.0, f"Average jitter {avg_jitter:.3f}ms >= 1.0ms"
    assert max_jitter < 5.0, f"Max jitter {max_jitter:.3f}ms >= 5.0ms"

    sender.disconnect()


@pytest.mark.load
def test_note_density(mock_mido):
    """Test handling of high note density (100 notes/second for 10 seconds).

    Success criteria:
    - Send 1000 note on/off pairs (2000 messages)
    - All notes tracked correctly
    - No dropped messages
    - Throughput >= 100 notes/second
    """
    sender = MidiSender()
    sender.connect()

    port = mock_mido.get_port()
    assert port is not None

    num_notes = 1000
    note_interval = 0.01  # 100 notes/second

    notes_sent = 0
    start_time = time.perf_counter()

    for i in range(num_notes):
        note = 60 + (i % 12)  # C4 to B4
        channel = i % 16

        # Send note on
        sender.send_note_on(channel=channel, note=note, velocity=100)

        # Small delay
        time.sleep(note_interval / 2)

        # Send note off
        sender.send_note_off(channel=channel, note=note)

        notes_sent += 1

        # Small delay before next note
        time.sleep(note_interval / 2)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    messages = port.get_messages()
    note_on_messages = [m for m in messages if m.type == "note_on"]
    note_off_messages = [m for m in messages if m.type == "note_off"]

    throughput = notes_sent / elapsed

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Note Density Test (100 notes/s, 10s)")
    print(f"{'='*60}")
    print(f"Notes sent: {notes_sent}")
    print(f"Note ON messages: {len(note_on_messages)}")
    print(f"Note OFF messages: {len(note_off_messages)}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Throughput: {throughput:.1f} notes/s")
    print(f"Active notes remaining: {len(sender.get_active_notes())}")
    print(f"{'='*60}\n")

    # Assertions
    assert len(note_on_messages) == num_notes, f"Expected {num_notes} note_on, got {len(note_on_messages)}"
    assert len(note_off_messages) == num_notes, f"Expected {num_notes} note_off, got {len(note_off_messages)}"
    assert throughput >= 100, f"Throughput {throughput:.1f} notes/s < 100 notes/s"
    assert len(sender.get_active_notes()) == 0, "Not all notes were turned off"

    sender.disconnect()


@pytest.mark.load
def test_osc_message_burst(mock_osc_client):
    """Test handling of OSC message bursts (100 messages in rapid succession).

    Success criteria:
    - Send 100 OSC messages with varying parameter counts
    - All messages sent successfully
    - Total time < 100ms
    - No errors
    """
    sender = OscSender()
    sender.connect()

    client = mock_osc_client.get_client()
    assert client is not None

    num_messages = 100
    messages_sent = 0
    errors = 0

    start_time = time.perf_counter()

    for i in range(num_messages):
        # Vary parameter count from 1 to 20
        num_params = (i % 20) + 1
        params = {f"param_{j}": j * 0.1 for j in range(num_params)}
        params["s"] = f"sound_{i % 10}"

        result = sender.send(params)
        if result:
            messages_sent += 1
        else:
            errors += 1

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    received_messages = client.get_messages()
    throughput = messages_sent / elapsed

    # Print metrics
    print(f"\n{'='*60}")
    print(f"OSC Message Burst Test")
    print(f"{'='*60}")
    print(f"Messages sent: {messages_sent}/{num_messages}")
    print(f"Messages received: {len(received_messages)}")
    print(f"Errors: {errors}")
    print(f"Total time: {elapsed * 1000:.1f}ms")
    print(f"Throughput: {throughput:.1f} msg/s")
    print(f"Avg time per message: {(elapsed / num_messages) * 1000:.3f}ms")
    print(f"{'='*60}\n")

    # Assertions
    assert errors == 0, f"Encountered {errors} errors during send"
    assert messages_sent == num_messages, f"Only sent {messages_sent}/{num_messages}"
    assert len(received_messages) == num_messages, f"Only received {len(received_messages)}/{num_messages}"
    assert elapsed < 0.1, f"Burst took {elapsed * 1000:.1f}ms >= 100ms"

    sender.disconnect()


@pytest.mark.load
def test_sustained_osc_throughput(mock_osc_client):
    """Test sustained OSC message throughput (1000 messages/second for 10 seconds).

    Success criteria:
    - Send 10,000 messages over 10 seconds
    - Maintain ~1000 msg/s throughput
    - No errors
    - Consistent timing (no significant slowdown)
    """
    sender = OscSender()
    sender.connect()

    client = mock_osc_client.get_client()
    assert client is not None

    duration = 10.0  # seconds
    target_rate = 1000  # messages/second
    interval = 1.0 / target_rate

    num_messages = int(duration * target_rate)

    messages_sent = 0
    errors = 0
    send_times = []

    start_time = time.perf_counter()

    for i in range(num_messages):
        expected_time = start_time + (i * interval)

        # Wait until expected send time
        now = time.perf_counter()
        sleep_time = max(0, expected_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)

        # Send message
        send_start = time.perf_counter()
        result = sender.send({
            "s": f"bd",
            "n": i % 16,
            "gain": 0.8,
            "pan": (i % 100) / 100.0
        })

        if result:
            messages_sent += 1
            send_times.append(send_start)
        else:
            errors += 1

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate timing consistency (check for slowdown)
    # Compare first half vs second half throughput
    half = len(send_times) // 2
    first_half_duration = send_times[half] - send_times[0]
    second_half_duration = send_times[-1] - send_times[half]

    first_half_rate = half / first_half_duration
    second_half_rate = half / second_half_duration

    received_messages = client.get_messages()
    throughput = messages_sent / elapsed

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Sustained OSC Throughput Test (1000 msg/s, 10s)")
    print(f"{'='*60}")
    print(f"Messages sent: {messages_sent}/{num_messages}")
    print(f"Messages received: {len(received_messages)}")
    print(f"Errors: {errors}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Throughput: {throughput:.1f} msg/s")
    print(f"First half rate: {first_half_rate:.1f} msg/s")
    print(f"Second half rate: {second_half_rate:.1f} msg/s")
    print(f"Rate variation: {abs(first_half_rate - second_half_rate):.1f} msg/s")
    print(f"{'='*60}\n")

    # Assertions
    assert errors == 0, f"Encountered {errors} errors during send"
    assert messages_sent == num_messages, f"Only sent {messages_sent}/{num_messages}"
    assert throughput >= 950, f"Throughput {throughput:.1f} msg/s < 950 msg/s"

    # Check for consistent rate (no significant slowdown)
    rate_variation = abs(first_half_rate - second_half_rate)
    assert rate_variation < 100, f"Rate variation {rate_variation:.1f} msg/s >= 100 msg/s (slowdown detected)"

    sender.disconnect()
