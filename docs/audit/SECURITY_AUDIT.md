# DocuMindAI — Security Audit

Companion to [FINAL_AUDIT.md](FINAL_AUDIT.md). Read-only security review of authentication, authorization, tenant isolation, secrets, payments, and injection surfaces. Findings are described, not fixed.

---

## 1. Security Controls That Are Correctly Implemented

| Control | Where | Notes |
|---|---|---|
| **Password hashing** | `core/security.py` | bcrypt via passlib (`CryptContext(schemes=["bcrypt"])`); replaced a prior SHA256 (FIX 0.9). Constant-time verify. |
| **JWT algorithm pinning** | `core/auth.py` | `algorithms=[settings.JWT_ALGORITHM]` (HS256 only), `verify_signature=True`. BUG-013 removed RS256 acceptance (algorithm-confusion) and BUG-003 removed a hardcoded fallback secret. |
| **Access/refresh split** | `core/security.py` | Refresh tokens carry `token_type="refresh"` and a 7-day expiry (BUG-008 fixed identical lifetimes). |
| **CSRF** | `core/middleware.CSRFMiddleware` | Double-submit cookie; header must equal cookie on mutations; bootstrap/auth paths exempt. |
| **Security headers** | `main.py` | HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, CSP `default-src 'self'`. |
| **Rate limiting** | SlowAPI | `/query/stream` 30/min; upload endpoints 20/min (BUG-010 — cost/DoS). |
| **Tenant isolation** | endpoints + `resolve_workspace_id` | Queries filter by `owner_id` + workspace UUID; vector namespace per user/org; RLS migrations exist. |
| **PII handling** | `utils/pii_redactor`, HR logs | `[REDACTED-PII]` in logs; Sentry `send_default_pii=False` + body scrubbing. |
| **Signed document URLs** | `documents.py` | HMAC-SHA256, 15-minute expiry. |
| **Payment webhook** | `billing.py` | HMAC-SHA256 signature `compare_digest` before plan activation. |
| **Path-traversal defense** | `documents.py upload_local` | Filenames sanitized (`re.sub(r'[^\w.\-]', '_', …)`). |
| **Trial abuse control** | `DeviceFingerprintMiddleware` | Blocks repeat trial registration per device (Redis). |
| **Enumeration resistance** | `/auth/forgot-password` | Returns 202 regardless of account existence. |

---

## 2. Findings

### HIGH

**H-S1 — Free plan self-upgrade in the default configuration.** — **RESOLVED (2026-07-18, H-6):** sandbox upgrade now 403s in production when payments are disabled.
`RAZORPAY_ENABLED` defaults to `false`. In that mode `POST /billing/upgrade` calls `_activate_plan` directly, letting any authenticated user set their own plan to any tier (including `enterprise`) with **no payment**. If the app is deployed without explicitly setting `RAZORPAY_ENABLED=true`, paid features are free.
- **Evidence:** `endpoints/billing.py:190-218`.
- **Impact:** revenue bypass / privilege (tier) escalation.
- **Root cause:** insecure-by-default feature flag; the safe mode requires opt-in.

**H-S2 — Algorithm-confusion smell in tenant middleware.** — **RESOLVED (2026-07-18, M-3):** decode pins `settings.JWT_ALGORITHM` (HS256 only).
`TenantContextMiddleware` decodes the session JWT with `algorithms=["HS256","RS256"]`, re-introducing the exact acceptance pattern that `auth.py` deliberately removed (BUG-013). It uses the symmetric `AUTH_SECRET_KEY` as the key. While this middleware only derives `collection_name` (not auth), allowing RS256 alongside a shared secret is a known dangerous pattern and is inconsistent with the hardened verifier.
- **Evidence:** `core/middleware.py:96-99` vs `core/auth.py:26`.
- **Impact:** latent; low direct exploitability here, but a foot-gun if this decode is ever trusted for authz.

### MEDIUM

**M-S1 — Secrets only via environment; weak-secret risk.**
`AUTH_SECRET_KEY`/`CSRF_SECRET_KEY` are plain env vars with placeholder defaults in `.env.example` (`change_me_...`). No secret-strength validation, no rotation, no vault integration. A deployment that forgets to change them is trivially forgeable.
- **Evidence:** `config.py`, `.env.example:19-20`.

**M-S2 — JWT in a readable cookie; no `SameSite`/`Secure` enforcement visible in config.**
Auth relies on a `token` cookie. Cookie flags (`HttpOnly`, `Secure`, `SameSite`) are set at issuance in the auth endpoint (not reviewed in full here); confirm they are `HttpOnly`, `Secure`, `SameSite=Lax/Strict`. HSTS is set, which helps.

**M-S3 — CORS allows credentials with an env-driven origin list.**
`allow_credentials=True` with `allow_origins=CORS_ORIGINS`. Safe if `CORS_ORIGINS` is a tight allowlist; dangerous if ever set to `*` (which is incompatible with credentials but sometimes forced). `allow_headers=["*"]`.

**M-S4 — Public shared-session endpoint.**
`GET /shared/{token}` is intentionally unauthenticated and returns session messages. Security rests entirely on token unguessability and the absence of enumeration. Confirm tokens are high-entropy and that revocation (`unshareSession`) fully invalidates.

**M-S5 — Prompt-injection exposure in document-grounded generation.** — **RESOLVED (2026-07-18, M-8):** evidence framed as untrusted data via a shared guard at the LLM service boundary.
User-uploaded document text is injected verbatim into LLM system prompts across workspaces (`_build_system_prompt`, legal/finance/exam prompts). A malicious document can attempt to override instructions ("ignore previous instructions…"). There is no input sanitization or instruction-isolation of evidence beyond `<evidence>` tags. For a "zero-hallucination/grounded" product this is the most relevant AI-security risk.

**M-S6 — Cache-purge pattern mismatch on delete.** — **RESOLVED (2026-07-19, M-2):** write key unified to the purged `retrieval:uid_{user}:*` namespace, tenant-scoped.
`delete_document` purges Redis keys `retrieval:uid_{uid}:*`, but the retrieval cache is written as `retrieval:{workspace}:{hash}`. Deleted-document content can persist in the retrieval cache (TTL 300s) and be served in answers after deletion — a data-retention/consistency concern.
- **Evidence:** `documents.py:601` vs `query.py:360-372`.

### LOW

**L-S1 — Verbose error surfaces.** Health checks and several endpoints return raw exception strings (`f"error: {str(e)}"`), which can leak DSNs/host info in error bodies.

**L-S2 — `pip-audit` non-blocking.** CI runs `pip-audit || echo "…"`, so dependency vulnerabilities never fail the build.

**L-S3 — No server-side timeouts on LLM calls.** Long Gemini calls have no hard cap server-side; a slow upstream ties up a worker thread (mitigated by client `AbortSignal`).

**L-S4 — Email verification optional.** The `/query/stream` gate on `email_verified` was intentionally removed; unverified accounts can use the product (acceptable, but weakens the "verified user" guarantee).

**L-S5 — Signed-URL/token reuse window.** 15-minute HMAC URLs are bearer tokens with no per-use nonce; anyone with the URL within the window has access.

---

## 3. Tenant Isolation Assessment

- **Application layer:** consistent `owner_id` + `workspace_id` filters across endpoints; per-chat `document_ids` scoping in retrieval; `resolve_workspace_id` deterministic mapping.
- **Vector layer:** namespace per user (`docuMind_{user_id}`) or org (`docuMind_org_{org_id}`), but **organization isolation is off by default** (`ENABLE_ORG_ISOLATION=false`, `VECTOR_ISOLATION_MODE="user"`).
- **Database layer:** RLS migrations (`enable_rls_documents`, `add_rls_user_isolation`) exist; confirm the app connects as a non-superuser role for RLS to be enforced (superuser bypasses RLS).
- **Risk:** the retrieval cache key does not include `owner_id` on the deletion-purge side (see M-S6); the main cache key does include workspace + attached doc ids, reducing cross-tenant bleed, but relies on workspace UUID correctness.

---

## 4. AI/LLM-Specific Security

- **Grounding as guardrail:** evidence is injected within a token budget and the prompt forbids external knowledge — good hallucination control, but **not** injection-proof (M-S5).
- **Refusal contract:** the system prompt mandates an exact refusal string when evidence is missing; however, **no-document mode** answers from general knowledge (labeled `mode: "general"`), which contradicts an absolute "refuses without evidence" claim.
- **Safe output handling:** `_safe_extract_text` prevents crashes on safety/recitation blocks — a robustness win.
- **Key exposure:** Gemini keys are logged only as masked suffixes; the key bridge never logs values.

---

## 5. Prioritized Security Recommendations (documentation only)

1. **Make payments secure-by-default:** require explicit `RAZORPAY_ENABLED` handling so `/billing/upgrade` cannot free-upgrade in production (H-S1).
2. **Unify JWT decoding** to HS256 everywhere; remove RS256 from the middleware (H-S2).
3. **Validate secret strength at startup**; document rotation (M-S1).
4. **Add evidence/instruction isolation** and basic prompt-injection defenses for grounded generation (M-S5).
5. **Fix the delete cache-purge key** to match the write pattern and include tenant scope (M-S6).
6. **Make `pip-audit` blocking**; scrub raw exception strings from responses (L-S1/L-S2).
7. **Confirm cookie flags** (`HttpOnly`, `Secure`, `SameSite`) and RLS role (M-S2, isolation §3).
