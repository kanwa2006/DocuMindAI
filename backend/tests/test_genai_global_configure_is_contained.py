"""Regression guard for final_audit S5 — RESOLVED via per-key clients.

**The defect.** `genai.configure(api_key=...)` mutated PROCESS-GLOBAL SDK
state, and `google.generativeai` resolved its client from that global AT CALL
TIME, not when `GenerativeModel` was constructed. With concurrency >= 2:

    request A: configure(key 3) -> dispatch
    request B: configure(key 7)
    request A's HTTP call goes out ... on KEY 7

A 429 was then attributed to key 3 and a HEALTHY key was cooled for 300s while
key 7 kept being handed out. Under load the pool degraded progressively and no
log explained it.

**Scope.** The register named two writers. This ratchet found FIVE, across two
process types — the three Beat-scheduled automation jobs were never listed.
`auto_key_rotation` was the worst: it deliberately walks every key and left the
global set to whichever it tested last, in the same worker process as
`embedding_service`.

**The fix (owner chose Option A).** `google.genai.Client(api_key=...)` binds
the key to the CLIENT, so a request can only ever call with its own key. All
five sites migrated; see `services/gemini_client.py`.

**What this file now guards.** `KNOWN_GLOBAL_CONFIGURE_SITES` is EMPTY, and
that emptiness IS the assertion: not one module mutates the global any more.
The allowlist may only shrink, and it has reached zero — so any reappearance
is a regression, not a known exception.
"""
import ast
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]

# Empty by design — see the module docstring. Do not add to this set.
KNOWN_GLOBAL_CONFIGURE_SITES: set = set()


def _configure_sites() -> dict:
    """Every `genai.configure(...)` call in app/, by module."""
    sites = {}
    for path in (BACKEND / "app").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "configure"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "genai"
            ):
                rel = path.relative_to(BACKEND).as_posix()
                sites.setdefault(rel, []).append(node.lineno)
    return sites


def test_nothing_mutates_the_global_genai_config():
    sites = _configure_sites()
    unexpected = set(sites) - KNOWN_GLOBAL_CONFIGURE_SITES
    assert not unexpected, (
        f"`genai.configure()` is back at {sorted(unexpected)}. That mutates "
        "PROCESS-GLOBAL SDK state which the library reads at CALL time, so "
        "under concurrency a request's HTTP call goes out on another request's "
        "key and a 429 cools the WRONG key for 300s (S5).\n\n"
        "Bind the key to a client instead: "
        "`app.services.gemini_client.get_client_pool().client_for(key)`."
    )


def test_the_legacy_sdk_is_not_reintroduced_for_generation():
    """The legacy package cannot carry a per-request key — that was the whole
    problem. `GenerativeModel.__init__` accepts no `client` and no `api_key`,
    so anything importing it for generation is back to a process global.

    `_safe_extract_text`'s docstring still references the legacy package by
    name because that is where the behaviour was first observed; comments are
    not imports, so only real imports are checked here.
    """
    offenders = []
    for path in (BACKEND / "app").rglob("*.py"):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            if any(n.startswith("google.generativeai") for n in names):
                offenders.append(f"{path.relative_to(BACKEND).as_posix()}:{node.lineno}")

    assert not offenders, (
        f"the deprecated `google.generativeai` SDK is imported at {offenders}. "
        "It has no way to bind a key to a request, so using it reintroduces "
        "the global that S5 removed. Use `google.genai`."
    )


def test_every_key_gets_its_own_client():
    """The pool must not hand the same client to two different keys."""
    from app.services.gemini_client import GeminiClientPool

    pool = GeminiClientPool()

    built = {}

    class _FakeSDK:
        @staticmethod
        def Client(api_key):  # noqa: N802 - mirrors the SDK's name
            obj = object()
            built[api_key] = obj
            return obj

    import app.services.gemini_client as mod

    original = mod.google_genai
    mod.google_genai = _FakeSDK
    try:
        a1 = pool.client_for("key-a")
        b1 = pool.client_for("key-b")
        a2 = pool.client_for("key-a")
    finally:
        mod.google_genai = original

    assert a1 is not b1, (
        "two different keys resolved to the SAME client object. The key would "
        "then be shared mutable state again — exactly S5."
    )
    assert a1 is a2, (
        "the same key built a second client. Construction costs ~2.5s against "
        "google-genai 2.5.0; rebuilding per call would put that on the request "
        "path."
    )
