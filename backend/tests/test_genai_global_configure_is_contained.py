"""Containment ratchet for final_audit S5 (PARKED — owner decision).

S5 is NOT fixed. It is parked pending an architectural decision, and this test
exists so the defect cannot SPREAD while it waits.

The defect: `genai.configure(api_key=...)` mutates PROCESS-GLOBAL SDK state,
and `google.generativeai` resolves its client from that global AT CALL TIME,
not when `GenerativeModel` is constructed. With concurrency >= 2, request A
configures key 3 and dispatches to the executor; request B configures key 7
before A's thread issues its HTTP call; A's call goes out on key 7. If it
429s, `_mark_key_failed` cools KEY 3 — a healthy key — for 300s, while key 7
keeps being handed out. Under load the pool degrades progressively: healthy
keys get cooled, hot keys never do.

Why it cannot be fixed in place, established by inspecting the installed SDK:

    google.generativeai == 0.8.6
    inspect.signature(genai.GenerativeModel.__init__) ->
        (self, model_name, safety_settings, generation_config, tools,
         tool_config, system_instruction)

There is no `client` or `api_key` parameter. The key CANNOT travel with the
request in this SDK, so the register's preferred fix ("a per-call client") is
not expressible without migrating to `google.genai`, which is installed
(2.5.0) and is the supported successor — the legacy package emits an
end-of-support FutureWarning on import.

The two options, and why neither belongs in a repair commit, are recorded
under OWNER DECISIONS in PROGRESS.md.

What this test does: pins the number of `genai.configure` call sites to the
two that are known and coupled. A third would be a third writer to the same
global, and the two existing ones already clobber each other — which is
exactly why the register marks S5 "NOT self-contained".
"""
import ast
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]

# Every site that mutates the process-global SDK config. This set may SHRINK
# when S5 is resolved. It must not grow.
#
# The register names TWO (llm_service, embedding_service). Writing this ratchet
# found FIVE, across two process types — the three automation jobs were never
# listed:
#
#   API process     llm_service (the rotator)  +  embedding_service
#   worker / beat   embedding_service  +  auto_health_check
#                   +  auto_key_rotation  +  auto_model_check
#
# `auto_key_rotation._test_api_key` is the worst of them: it DELIBERATELY walks
# every key, calling configure on each, and leaves the global set to whichever
# key it tested last. Any embedding call in that worker afterwards silently
# uses that key. It is Beat-scheduled, so it fires on a timer with no relation
# to what else the worker is doing.
KNOWN_GLOBAL_CONFIGURE_SITES = {
    "app/services/llm_service.py",
    "app/services/embedding_service.py",
    "app/automation/auto_health_check.py",
    "app/automation/auto_key_rotation.py",
    "app/automation/auto_model_check.py",
}


def _configure_sites() -> dict:
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


def test_no_new_writer_to_the_global_genai_config():
    sites = _configure_sites()
    unexpected = set(sites) - KNOWN_GLOBAL_CONFIGURE_SITES
    assert not unexpected, (
        f"new `genai.configure()` call site(s): {sorted(unexpected)}. That "
        "mutates PROCESS-GLOBAL SDK state which the library reads at call "
        "time, so under concurrency a request's HTTP call can go out on "
        "another request's key — and a 429 then cools the WRONG key for 300s "
        "(S5, parked). The two existing writers already clobber each other; a "
        "third makes the coupling untraceable.\n\n"
        "If you need a specific key for a call, use `google.genai.Client("
        "api_key=...)` (installed, 2.5.0) so the key travels with the request."
    )


def test_the_known_sites_have_not_multiplied():
    """Each known module may configure the global at most once."""
    sites = _configure_sites()
    for module, lines in sites.items():
        assert len(lines) == 1, (
            f"{module} calls genai.configure() {len(lines)} times "
            f"(lines {lines}). Each additional call widens the window in which "
            "a concurrent request can steal the key (S5)."
        )


def test_the_legacy_sdk_cannot_carry_a_per_call_key():
    """Pins the reason S5 is parked rather than fixed.

    If this ever fails, the SDK has gained per-instance keying and S5 becomes
    a normal, self-contained fix — unpark it.
    """
    import inspect

    import google.generativeai as genai

    params = set(inspect.signature(genai.GenerativeModel.__init__).parameters)
    assert not ({"client", "api_key"} & params), (
        "google.generativeai.GenerativeModel now accepts a client/api_key. The "
        "architectural blocker on S5 is gone — the key can travel with the "
        "request. Unpark S5 and fix both configure sites together."
    )
