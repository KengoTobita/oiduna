"""
Oiduna Loop Service Entry Point

Run as:
    python -m oiduna_loop
    oiduna-loop (after pip install)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from types import FrameType

from .factory import create_loop_engine


def setup_logging(debug: bool = False) -> None:
    """Configure logging"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Oiduna Loop Service - Real-time audio loop engine"
    )
    parser.add_argument(
        "--osc-host",
        default="127.0.0.1",
        help="SuperDirt OSC host (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--osc-port",
        type=int,
        default=57120,
        help="SuperDirt OSC port (default: 57120)",
    )
    parser.add_argument(
        "--midi-port",
        default=None,
        help="MIDI output port name (default: first available)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--list-midi",
        action="store_true",
        help="List available MIDI ports and exit",
    )

    args = parser.parse_args()

    # List MIDI ports and exit
    if args.list_midi:
        from .output import MidiSender
        ports = MidiSender.list_ports()
        if ports:
            print("Available MIDI output ports:")
            for port in ports:
                print(f"  - {port}")
        else:
            print("No MIDI output ports available")
        return 0

    setup_logging(args.debug)
    logger = logging.getLogger(__name__)

    # Create engine via factory (DI pattern)
    engine = create_loop_engine(
        osc_host=args.osc_host,
        osc_port=args.osc_port,
        midi_port=args.midi_port,
    )

    # Handle shutdown signals
    def signal_handler(signum: int, frame: FrameType | None) -> None:
        logger.info("Shutdown signal received")
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start engine
    logger.info("Starting Oiduna Loop Service")
    logger.info(f"  OSC: {args.osc_host}:{args.osc_port}")

    try:
        engine.start()
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt")
    finally:
        engine.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
