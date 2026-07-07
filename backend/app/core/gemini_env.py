"""
Gemini API key environment bridge.

WHY THIS EXISTS
---------------
`GeminiKeyRotator` (services/llm_key_rotation.py) reads keys *directly* from the
process environment: os.environ["GEMINI_API_KEY_1"], _2, _3, ...  pydantic-settings
loads the .env file into the `settings` object but does NOT export those values
into os.environ, so the rotator finds nothing and LLMService silently falls back
to DummyLLMProvider (fake "fully grounded and operational" answers).

Previously a bridge lived inline in main.py, but that had two runtime failures:
  1. It read `dotenv_values(".env")` with a RELATIVE path, so it only worked when
     the process was launched from the backend/ directory. Launched from the repo
     root (or via a bare `python -c` repro) it loaded 0 keys.
  2. It ran only inside main.py (the web app). The Celery worker imports
     celery_app.py, never main.py, so worker-side LLM calls (summaries, deep
     research, HR/legal/finance/research/study tasks) never got keys at all.

This module fixes both by:
  * resolving the env file relative to the backend ROOT (anchored to __file__),
    never the current working directory, and
  * being called from get_key_rotator() — the single point every LLM call funnels
    through — so web, worker, and standalone scripts all load keys identically.

It is additive and idempotent. It NEVER overrides a value already present in
os.environ (so real container env vars / docker-compose `env_file` always win).
It does not touch any CLAUDE.md-protected file.
"""
import os
import logging

logger = logging.getLogger(__name__)

# backend/app/core/gemini_env.py -> backend/
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_bridged = False


def _candidate_env_files():
    """
    Ordered list of env files to inspect. First match wins per key (setdefault),
    and anything already in os.environ always wins over all of them.

    Order:
      1. $ENV_FILE if set (absolute, or resolved against CWD, or backend root)
      2. <backend_root>/.env          (where the project's real keys live)
      3. <backend_root>/.env.development
    """
    candidates = []
    env_file = os.getenv("ENV_FILE")
    if env_file:
        if os.path.isabs(env_file):
            candidates.append(env_file)
        else:
            candidates.append(os.path.abspath(env_file))            # relative to CWD
            candidates.append(os.path.join(_BACKEND_ROOT, env_file))  # relative to backend root
    candidates.append(os.path.join(_BACKEND_ROOT, ".env"))
    candidates.append(os.path.join(_BACKEND_ROOT, ".env.development"))

    seen, ordered = set(), []
    for path in candidates:
        norm = os.path.normpath(path)
        if norm not in seen:
            seen.add(norm)
            ordered.append(norm)
    return ordered


def bridge_gemini_keys() -> int:
    """
    Promote GEMINI_API_KEY_N (and the legacy comma-separated GEMINI_API_KEYS)
    from the project's env file into os.environ, CWD-independent and idempotent.

    Returns the number of GEMINI_API_KEY_* values present in os.environ afterward.
    """
    global _bridged

    def _count():
        return len([
            v for n, v in os.environ.items()
            if n.startswith("GEMINI_API_KEY_") and v
        ])

    # Already populated (e.g. real container env / docker-compose env_file): done.
    if _bridged or _count() > 0:
        _bridged = True
        return _count()

    try:
        from dotenv import dotenv_values
    except ImportError:
        logger.warning("[gemini_env] python-dotenv not installed; cannot bridge keys from .env file.")
        return _count()

    for path in _candidate_env_files():
        if not os.path.isfile(path):
            continue
        values = dotenv_values(path) or {}

        # 1) Direct numbered keys: GEMINI_API_KEY_1, _2, ...
        for name, val in values.items():
            if name and name.startswith("GEMINI_API_KEY_") and val and val.strip():
                os.environ.setdefault(name, val.strip())

        # 2) Legacy single key (no suffix).
        single = values.get("GEMINI_API_KEY")
        if single and single.strip():
            os.environ.setdefault("GEMINI_API_KEY", single.strip())

        # 3) Legacy comma-separated plural form -> explode into numbered slots,
        #    but only if no numbered keys were found anywhere yet.
        if _count() == 0:
            plural = values.get("GEMINI_API_KEYS") or ""
            plural_keys = [k.strip() for k in plural.split(",") if k.strip()]
            # Ignore obvious placeholders like "your_gemini_api_key_here".
            plural_keys = [k for k in plural_keys if k.lower().startswith("aizasy") or len(k) > 20]
            for i, k in enumerate(plural_keys, start=1):
                os.environ.setdefault(f"GEMINI_API_KEY_{i}", k)

        if _count() > 0:
            logger.info("[gemini_env] Bridged %d Gemini key(s) from %s", _count(), path)
            break

    _bridged = True
    return _count()
