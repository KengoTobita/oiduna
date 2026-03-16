"""Load tests for IPC layer throughput.

Tests cover:
- Command receiver throughput (messages/second)
- State publisher throughput (position updates)
- Bidirectional throughput (commands + state)
"""

import pytest
import asyncio
import time
from statistics import mean, median

from oiduna.infrastructure.ipc.serializer import IPCSerializer
from oiduna.infrastructure.ipc.command_receiver import CommandReceiver
from oiduna.infrastructure.ipc.state_publisher import StatePublisher


@pytest.mark.load
@pytest.mark.asyncio
async def test_command_receiver_throughput(mock_zmq_context):
    """Test command receiver can handle 1000 messages/second.

    Success criteria:
    - Process 1000 messages within 1 second
    - No errors during processing
    - Average latency < 1ms per message
    """
    receiver = CommandReceiver()
    receiver.connect()

    socket = mock_zmq_context.get_sockets()[0]
    serializer = IPCSerializer()

    # Prepare 1000 messages
    num_messages = 1000
    messages = [
        serializer.serialize_message("play", {"pattern_id": f"{i:04x}"})
        for i in range(num_messages)
    ]

    # Inject all messages
    for msg in messages:
        socket.inject_message(msg)

    # Measure throughput
    start_time = time.perf_counter()
    latencies = []

    for _ in range(num_messages):
        msg_start = time.perf_counter()
        result = await receiver.receive()
        msg_end = time.perf_counter()

        assert result is not None
        latencies.append((msg_end - msg_start) * 1000)  # Convert to ms

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate metrics
    throughput = num_messages / elapsed
    avg_latency = mean(latencies)
    median_latency = median(latencies)
    p99_latency = sorted(latencies)[int(0.99 * len(latencies))]

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Command Receiver Throughput Test")
    print(f"{'='*60}")
    print(f"Messages processed: {num_messages}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Throughput: {throughput:.1f} msg/s")
    print(f"Avg latency: {avg_latency:.3f}ms")
    print(f"Median latency: {median_latency:.3f}ms")
    print(f"P99 latency: {p99_latency:.3f}ms")
    print(f"{'='*60}\n")

    # Assertions
    assert throughput >= 1000, f"Throughput {throughput:.1f} msg/s < 1000 msg/s"
    assert avg_latency < 1.0, f"Average latency {avg_latency:.3f}ms >= 1.0ms"

    receiver.disconnect()


@pytest.mark.load
def test_state_publisher_throughput(mock_zmq_context):
    """Test state publisher can handle 120 BPM position updates.

    At 120 BPM, position updates happen ~8 times per second for 10 seconds.

    Success criteria:
    - Send 80 position updates (10 seconds at 120 BPM)
    - No send errors
    - Consistent timing (jitter < 10ms)
    """
    publisher = StatePublisher()
    publisher.connect()

    socket = mock_zmq_context.get_sockets()[0]

    # 120 BPM = 2 beats/second, update every 0.125s (8/sec)
    num_updates = 80
    update_interval = 0.125  # seconds

    send_times = []
    start_time = time.perf_counter()

    for i in range(num_updates):
        expected_time = start_time + (i * update_interval)

        # Wait until expected send time
        now = time.perf_counter()
        sleep_time = max(0, expected_time - now)
        if sleep_time > 0:
            time.sleep(sleep_time)

        # Send position update
        send_start = time.perf_counter()
        result = publisher.send_position(
            current_step=i % 256,
            bpm=120.0
        )
        assert result is True
        send_times.append(send_start)

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate timing jitter
    expected_times = [start_time + (i * update_interval) for i in range(num_updates)]
    jitters = [abs(actual - expected) * 1000 for actual, expected in zip(send_times, expected_times)]

    avg_jitter = mean(jitters)
    max_jitter = max(jitters)

    # Print metrics
    print(f"\n{'='*60}")
    print(f"State Publisher Throughput Test (120 BPM)")
    print(f"{'='*60}")
    print(f"Updates sent: {num_updates}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Expected time: {num_updates * update_interval:.3f}s")
    print(f"Update rate: {num_updates / elapsed:.1f} updates/s")
    print(f"Avg jitter: {avg_jitter:.3f}ms")
    print(f"Max jitter: {max_jitter:.3f}ms")
    print(f"{'='*60}\n")

    # Assertions
    assert avg_jitter < 10.0, f"Average jitter {avg_jitter:.3f}ms >= 10ms"
    assert max_jitter < 50.0, f"Max jitter {max_jitter:.3f}ms >= 50ms"

    publisher.disconnect()


@pytest.mark.load
@pytest.mark.asyncio
async def test_bidirectional_throughput(mock_zmq_context):
    """Test simultaneous command receiving and state publishing.

    Success criteria:
    - Receive 100 commands/second while sending 10 state updates/second
    - Run for 5 seconds (500 commands, 50 state updates)
    - No errors on either channel
    """
    receiver = CommandReceiver()
    publisher = StatePublisher()

    receiver.connect()
    publisher.connect()

    # Get receiver socket for message injection
    receiver_socket = mock_zmq_context.get_sockets()[0]
    serializer = IPCSerializer()

    # Prepare test parameters
    duration = 5.0  # seconds
    command_rate = 100  # commands/second
    state_rate = 10  # state updates/second

    num_commands = int(duration * command_rate)
    num_states = int(duration * state_rate)

    # Inject all commands upfront
    for i in range(num_commands):
        msg = serializer.serialize_message("compile", {"pattern": f"bd*{i % 16}"})
        receiver_socket.inject_message(msg)

    # Track metrics
    commands_received = 0
    states_sent = 0
    errors = []

    start_time = time.perf_counter()

    # Run concurrent tasks
    async def receive_commands():
        nonlocal commands_received
        try:
            for _ in range(num_commands):
                result = await receiver.receive()
                if result:
                    commands_received += 1
        except Exception as e:
            errors.append(f"Receive error: {e}")

    async def send_states():
        nonlocal states_sent
        try:
            for i in range(num_states):
                # Send every 0.1 seconds (10/sec)
                await asyncio.sleep(0.1)
                result = publisher.send_position(
                    current_step=i % 256,
                    bpm=120.0
                )
                if result:
                    states_sent += 1
        except Exception as e:
            errors.append(f"Send error: {e}")

    # Run both tasks concurrently
    await asyncio.gather(
        receive_commands(),
        send_states()
    )

    end_time = time.perf_counter()
    elapsed = end_time - start_time

    # Calculate metrics
    command_throughput = commands_received / elapsed
    state_throughput = states_sent / elapsed

    # Print metrics
    print(f"\n{'='*60}")
    print(f"Bidirectional Throughput Test")
    print(f"{'='*60}")
    print(f"Duration: {elapsed:.3f}s")
    print(f"Commands received: {commands_received}/{num_commands}")
    print(f"Command throughput: {command_throughput:.1f} msg/s")
    print(f"States sent: {states_sent}/{num_states}")
    print(f"State throughput: {state_throughput:.1f} updates/s")
    print(f"Errors: {len(errors)}")
    if errors:
        for err in errors:
            print(f"  - {err}")
    print(f"{'='*60}\n")

    # Assertions
    assert len(errors) == 0, f"Encountered {len(errors)} errors during test"
    assert commands_received == num_commands, f"Only received {commands_received}/{num_commands} commands"
    assert states_sent == num_states, f"Only sent {states_sent}/{num_states} states"
    assert command_throughput >= 90, f"Command throughput {command_throughput:.1f} < 90 msg/s"
    assert state_throughput >= 9, f"State throughput {state_throughput:.1f} < 9 updates/s"

    receiver.disconnect()
    publisher.disconnect()
