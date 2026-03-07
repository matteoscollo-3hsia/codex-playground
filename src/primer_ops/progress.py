from __future__ import annotations

import itertools
import sys
import threading
import time
from contextlib import contextmanager


def format_seconds(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins = int(seconds // 60)
    secs = seconds - mins * 60
    return f"{mins}m {secs:.0f}s"


@contextmanager
def spinner(message: str, interval_s: float = 0.1):
    stop = threading.Event()
    start = time.time()

    def run() -> None:
        for ch in itertools.cycle("|/-\\"):
            if stop.is_set():
                break
            elapsed = format_seconds(time.time() - start)
            sys.stdout.write(f"\r  {message} {ch}  {elapsed}")
            sys.stdout.flush()
            time.sleep(interval_s)

        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=1)


class LiveTimer:
    """Background elapsed-time ticker for long operations.

    Usage::

        timer = LiveTimer("Calling OpenAI...")
        timer.start()
        # ... do work ...
        timer.stop()
    """

    def __init__(self, message: str, interval_s: float = 0.5) -> None:
        self._message = message
        self._interval_s = interval_s
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        start = time.time()
        for ch in itertools.cycle("|/-\\"):
            if self._stop.is_set():
                break
            elapsed = format_seconds(time.time() - start)
            sys.stdout.write(f"\r  {self._message} {ch}  {elapsed}")
            sys.stdout.flush()
            time.sleep(self._interval_s)
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)


def print_sheet_bar(
    current: int,
    total: int,
    sheet_name: str,
    elapsed_s: float,
    width: int = 30,
) -> None:
    """Print a one-line sheet progress bar followed by a newline."""
    filled = round(width * current / max(total, 1))
    bar = "█" * filled + "░" * (width - filled)
    elapsed = format_seconds(elapsed_s)
    print(f"  [{bar}] {current}/{total}  {sheet_name}  ({elapsed})", flush=True)
