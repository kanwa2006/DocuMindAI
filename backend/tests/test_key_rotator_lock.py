"""Regression tests for DEBUG_MASTER_PLAN M-9.

GeminiKeyRotator.get_key() slept inside self._lock when all keys were
cooling, serializing every other caller behind one thread's full cooldown
wait (and blocking the event loop when reached from async contexts). The
wait now happens outside the lock with a state re-check afterwards.
"""
import time

import pytest

from app.services import llm_key_rotation as rotation_module
from app.services.llm_key_rotation import GeminiKeyRotator


def _make_rotator(keys):
    from itertools import cycle

    import threading

    r = GeminiKeyRotator.__new__(GeminiKeyRotator)
    r._keys = list(keys)
    r._bad_keys = set()
    r._cooling_keys = {}
    r._lock = threading.Lock()
    r._cycle = cycle(r._keys)
    return r


def test_normal_rotation_unaffected():
    r = _make_rotator(["k1", "k2"])
    got = {r.get_key() for _ in range(4)}
    assert got == {"k1", "k2"}


def test_all_invalid_raises():
    r = _make_rotator(["k1", "k2"])
    r._bad_keys = {"k1", "k2"}
    with pytest.raises(RuntimeError, match="invalid"):
        r.get_key()


def test_cooldown_sleep_happens_outside_the_lock(monkeypatch):
    r = _make_rotator(["k1"])
    r._cooling_keys = {"k1": time.time() + 0.05}

    lock_states = []
    real_sleep = time.sleep

    def recording_sleep(seconds):
        lock_states.append(r._lock.locked())
        real_sleep(min(seconds, 0.1))

    monkeypatch.setattr(rotation_module.time, "sleep", recording_sleep)
    key = r.get_key()

    assert key == "k1"
    assert lock_states, "expected at least one cooldown wait"
    assert all(state is False for state in lock_states), (
        "time.sleep must never run while holding the rotator lock"
    )


def test_other_threads_not_blocked_during_cooldown_wait():
    """report_rate_limit from another thread must complete while a get_key
    caller is waiting out a cooldown."""
    import threading

    r = _make_rotator(["k1"])
    r._cooling_keys = {"k1": time.time() + 0.4}

    waiter_done = threading.Event()
    reporter_done = threading.Event()

    def waiter():
        r.get_key()
        waiter_done.set()

    def reporter():
        time.sleep(0.05)  # let the waiter enter its cooldown wait first
        r.report_rate_limit("k1", retry_after_seconds=0)  # must not block
        reporter_done.set()

    t1 = threading.Thread(target=waiter)
    t2 = threading.Thread(target=reporter)
    t1.start(); t2.start()

    assert reporter_done.wait(timeout=0.3), (
        "report_rate_limit blocked behind a get_key cooldown wait (lock held during sleep)"
    )
    t1.join(timeout=2)
    assert waiter_done.is_set()
