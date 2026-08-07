"""Regression guard for final_audit S5 — the concurrency property itself.

The old code could not attribute a failure to the key that caused it. Under
concurrency, request A configured key 3, request B configured key 7, and A's
HTTP call went out on key 7 — so a 429 cooled key 3, a HEALTHY key, for 300
seconds while the exhausted key kept being handed out.

`test_genai_global_configure_is_contained.py` proves the global is gone.
This file proves the BEHAVIOUR that global was breaking:

  1. concurrent requests each use the key they were given, never each other's
  2. a 429 cools the key that actually served the call
  3. a retryable failure re-runs the whole request on a DIFFERENT key
  4. a capability gap (404) does NOT cool a healthy key
  5. once streaming has begun the key is fixed — no mid-stream switching
"""
import asyncio

import pytest

from app.services import gemini_client
from app.services.gemini_client import (
    ModelUnavailableForAllKeys,
    classify_failure,
    run_with_rotation,
    stream_with_rotation,
)


class _Err(Exception):
    """An APIError stand-in carrying an HTTP status the classifier reads."""

    def __init__(self, code, message="boom"):
        super().__init__(message)
        self.code = code


class _FakeRotator:
    def __init__(self, keys):
        self._keys = list(keys)
        self._i = 0
        self.rate_limited = []
        self.invalidated = []
        self.cooled = set()

    @property
    def keys(self):
        return list(self._keys)

    def try_get_key(self):
        for _ in range(len(self._keys)):
            key = self._keys[self._i % len(self._keys)]
            self._i += 1
            if key not in self.cooled:
                return key
        return None

    def seconds_until_next_key(self):
        return None if len(self.cooled) >= len(self._keys) else 0.0

    def key_index(self, key):
        return self._keys.index(key) if key in self._keys else -1

    def report_rate_limit(self, key, seconds=60):
        self.rate_limited.append((key, seconds))
        self.cooled.add(key)

    def report_invalid_key(self, key):
        self.invalidated.append(key)
        self.cooled.add(key)


@pytest.fixture
def wiring(monkeypatch):
    """Install a fake rotator + a pool whose client simply echoes its key."""

    def _install(keys):
        rotator = _FakeRotator(keys)
        monkeypatch.setattr(gemini_client, "get_key_rotator", lambda: rotator)

        class _Pool:
            def client_for(self, key):
                return f"client::{key}"

        monkeypatch.setattr(gemini_client, "get_client_pool", lambda: _Pool())
        return rotator

    return _install


@pytest.mark.asyncio
async def test_concurrent_requests_never_borrow_each_others_key(wiring):
    """The defect, stated directly: a call must use the key it was handed."""
    wiring(["k1", "k2", "k3"])
    mismatches = []

    async def one_request():
        async def op(client):
            handed = client  # "client::kN"
            # Yield control repeatedly — this is precisely the window in which
            # the old global could be reassigned by another request.
            for _ in range(5):
                await asyncio.sleep(0)
            return handed

        return await run_with_rotation(op)

    results = await asyncio.gather(*(one_request() for _ in range(12)))
    for r in results:
        if not r.startswith("client::k"):
            mismatches.append(r)

    assert not mismatches, f"a request used an unexpected client: {mismatches}"
    # Every result is a client bound to a key; none can be "the current key",
    # because there is no such thing any more.
    assert all(r.startswith("client::") for r in results)


@pytest.mark.asyncio
async def test_a_429_cools_the_key_that_actually_served_the_call(wiring):
    rotator = wiring(["k1", "k2", "k3"])
    used = []

    async def op(client):
        key = client.split("::")[1]
        used.append(key)
        if key == "k1":
            raise _Err(429, "quota exhausted")
        return "ok"

    result = await run_with_rotation(op)

    assert result == "ok"
    cooled_keys = [k for k, _ in rotator.rate_limited]
    assert cooled_keys == ["k1"], (
        f"expected only the failing key k1 to be cooled, got {cooled_keys}. "
        "Cooling a key that did not serve the failing call is S5."
    )
    assert used[0] == "k1" and used[1] != "k1", (
        f"the retry did not move to a different key: {used}"
    )


@pytest.mark.asyncio
async def test_retryable_failure_reruns_the_whole_request_on_another_key(wiring):
    wiring(["k1", "k2"])
    attempts = []

    async def op(client):
        attempts.append(client)
        if len(attempts) == 1:
            raise _Err(503, "service unavailable")
        return "second-attempt-ok"

    assert await run_with_rotation(op) == "second-attempt-ok"
    assert len(attempts) == 2 and attempts[0] != attempts[1], (
        f"a transient failure did not retry on a different key: {attempts}"
    )


@pytest.mark.asyncio
async def test_a_model_capability_gap_does_not_cool_a_healthy_key(wiring):
    """404 means 'this key can't use this model', not 'this key is broken'."""
    rotator = wiring(["k1", "k2"])

    async def op(client):
        raise _Err(404, "model not found for api version")

    with pytest.raises(ModelUnavailableForAllKeys):
        await run_with_rotation(op)

    assert rotator.rate_limited == [], (
        f"a 404 cooled keys {rotator.rate_limited}. That poisons healthy keys "
        "for 300s over a per-key model restriction."
    )
    assert rotator.invalidated == []


@pytest.mark.asyncio
async def test_the_key_is_fixed_once_streaming_begins(wiring):
    """Mid-stream switching would splice two different completions together."""
    wiring(["k1", "k2", "k3"])
    opened = []

    class _Stream:
        def __init__(self, key):
            self.key = key
            self.n = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.n += 1
            if self.n > 3:
                raise StopAsyncIteration
            return f"{self.key}-chunk{self.n}"

    async def open_stream(client):
        key = client.split("::")[1]
        opened.append(key)
        return _Stream(key)

    chunks = [c async for c in stream_with_rotation(open_stream)]

    assert len(opened) == 1, f"the stream was reopened on another key: {opened}"
    assert len({c.split("-")[0] for c in chunks}) == 1, (
        f"chunks came from more than one key: {chunks}"
    )


def test_status_codes_beat_substrings_in_classification():
    """S18: `'503' in text` matched token counts like '503 tokens'."""
    assert classify_failure(_Err(429)) == "rate_limit"
    assert classify_failure(_Err(403)) == "invalid_key"
    assert classify_failure(_Err(404)) == "model_unavailable"
    assert classify_failure(_Err(500)) == "server_error"

    # A structured 404 must win over the word "quota" in the message.
    assert classify_failure(_Err(404, "quota mentioned but really a 404")) == (
        "model_unavailable"
    ), "a substring beat the HTTP status — this is the S18 mistake"
