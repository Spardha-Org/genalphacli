"""Shared heartbeat utility for long-running Temporal activities.

Usage:
    from worker.heartbeat import heartbeat_periodically

    @activity.defn
    def my_activity(input):
        activity.heartbeat("step_1")
        do_fast_thing()

        with heartbeat_periodically(interval=10.0, message="blocking_step"):
            do_blocking_thing()  # e.g., subprocess, large download

        activity.heartbeat("step_3")
        do_another_thing()
"""

from __future__ import annotations

import contextvars
import threading
from contextlib import contextmanager

from temporalio import activity


@contextmanager
def heartbeat_periodically(interval: float = 10.0, message: str = "working"):
    """Send heartbeats on a background thread while a blocking call runs.

    Uses contextvars.copy_context() to propagate the Temporal activity
    context to the new thread (required for activity.heartbeat() to work).
    """
    ctx = contextvars.copy_context()
    stop = threading.Event()

    def _beat():
        while not stop.is_set():
            try:
                ctx.run(activity.heartbeat, message)
            except Exception:
                pass  # Swallow errors — heartbeat is best-effort
            stop.wait(interval)

    t = threading.Thread(target=_beat, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=2.0)
