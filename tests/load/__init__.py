"""Load test suite for oiduna.

These tests are designed to validate system behavior under load and
are skipped by default. To run load tests, set the environment variable:

    RUN_LOAD_TESTS=1 pytest tests/load/ -v -s

Load tests measure:
- Throughput (messages/second)
- Latency (p50, p99)
- Timing stability (jitter for clock signals)
- Error rates under load
- Memory usage over time
- Concurrent client handling
"""
