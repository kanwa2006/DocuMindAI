"""
DocuMindAI — DB connectivity probe.

Run from the backend/ directory:
    python -m scripts.check_db
or:
    python scripts/check_db.py

Reports, in plain English, which connection attempts succeed and which fail.
Useful when /api/v1/health/detailed reports db != ok.

This script never logs the password. It only reports auth/network/SSL errors.
"""
from __future__ import annotations

import asyncio
import os
import sys
import ssl
import traceback
from pathlib import Path
from urllib.parse import urlparse, unquote

# Make sure we can import app.* whether invoked as -m or as a script
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

try:
    import asyncpg  # type: ignore
except ImportError:
    asyncpg = None

try:
    import psycopg2  # type: ignore
except ImportError:
    psycopg2 = None


def _parse(url: str):
    u = urlparse(url)
    return {
        "scheme": u.scheme,
        "user": u.username,
        "password_present": bool(u.password),
        "password_url_encoded": "%" in (u.password or ""),
        "host": u.hostname,
        "port": u.port,
        "db": (u.path or "/").lstrip("/") or None,
    }


def _redact_url(url: str) -> str:
    u = urlparse(url)
    if u.password:
        return url.replace(u.password, "***")
    return url


async def _probe_asyncpg(label: str, url: str) -> bool:
    if asyncpg is None:
        print(f"  [{label}] asyncpg not installed — skipping")
        return False
    # asyncpg.connect can take a DSN directly; strip the SQLAlchemy driver tag.
    dsn = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(dsn=dsn, ssl="require",
                            statement_cache_size=0),
            timeout=12,
        )
        v = await conn.fetchval("select version()")
        await conn.close()
        print(f"  OK   [{label}] -> {v[:80]}")
        return True
    except asyncpg.InvalidPasswordError as e:
        print(f"  AUTH [{label}] -> password rejected by server: {e}")
    except asyncpg.PostgresError as e:
        print(f"  PG   [{label}] -> {type(e).__name__}: {e}")
    except (OSError, asyncio.TimeoutError) as e:
        print(f"  NET  [{label}] -> {type(e).__name__}: {e}")
    except Exception as e:
        print(f"  ERR  [{label}] -> {type(e).__name__}: {e}")
    return False


def _probe_psycopg2(label: str, url: str) -> bool:
    if psycopg2 is None:
        print(f"  [{label}] psycopg2 not installed — skipping")
        return False
    dsn = url.replace("postgresql+psycopg2://", "postgresql://", 1)
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    if "sslmode=" not in dsn:
        dsn += ("&" if "?" in dsn else "?") + "sslmode=require"
    try:
        conn = psycopg2.connect(dsn, connect_timeout=12)
        cur = conn.cursor()
        cur.execute("select version()")
        v = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"  OK   [{label}] -> {v[:80]}")
        return True
    except psycopg2.OperationalError as e:
        print(f"  AUTH [{label}] -> {e}".strip())
    except Exception as e:
        print(f"  ERR  [{label}] -> {type(e).__name__}: {e}")
    return False


def _derive_pooler_variants(url: str):
    """If the URL targets Supavisor on :5432 (session pooler), also try :6543."""
    out = []
    u = urlparse(url)
    if u.hostname and "pooler.supabase.com" in u.hostname and u.port in (5432, 6543):
        other = 6543 if u.port == 5432 else 5432
        twin = url.replace(f":{u.port}/", f":{other}/")
        out.append((f"{('tx' if other==6543 else 'session')} pooler :{other}", twin))
    return out


async def main():
    print("DocuMindAI DB connectivity probe")
    print("=" * 60)

    raw = os.getenv("DATABASE_URL")
    if not raw:
        print("ERROR: DATABASE_URL is not set in environment / .env")
        sys.exit(2)

    print("DATABASE_URL :", _redact_url(raw))
    info = _parse(raw)
    print("parsed       :", {k: v for k, v in info.items() if k != "password_present"})
    print()

    print("--- async (asyncpg) ---")
    primary_ok = await _probe_asyncpg("primary", raw)

    for label, twin in _derive_pooler_variants(raw):
        await _probe_asyncpg(label, twin)

    print()
    print("--- sync (psycopg2) ---")
    # Derive sync-friendly URL by stripping +asyncpg and adding sslmode
    sync_url = raw.replace("+asyncpg", "")
    _probe_psycopg2("primary-sync", sync_url)

    print()
    if primary_ok:
        print("RESULT: primary async connection works — backend health should report db=ok.")
        sys.exit(0)
    else:
        print("RESULT: primary async connection FAILED. Common causes:")
        print("  1. Supabase password was rotated — update DATABASE_URL in .env.")
        print("  2. Supabase project is paused (free tier) — open the dashboard to resume.")
        print("  3. Outbound 5432/6543 blocked by local firewall.")
        print("  4. Wrong pooler region in host (current host should match your Supabase project).")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
