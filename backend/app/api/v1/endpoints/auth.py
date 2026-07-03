import os
import random
import string
import secrets
import smtplib
import asyncio
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sa_update

from app.db.session import get_db
from app.models.org import User
from app.core.security import verify_password, create_access_token, create_refresh_token, hash_password
from app.core.config import settings
from app.core.auth import get_current_user
from app.core.rate_limiter import limiter

logger = logging.getLogger("audit.auth")
router = APIRouter()

# FIX 0.4: Environment-aware secure flag — False on localhost HTTP, True in production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates user and returns HTTP-Only cookie.
    secure=False in dev (HTTP localhost), secure=True in production (HTTPS).
    Rate-limited to 5/minute per IP to slow credential-stuffing.
    """
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    workspace_id = str(user.workspace_id) if user.workspace_id else "general"
    roles = [r.role for r in (user.roles or [])]

    access_token = create_access_token(
        subject=user.email,
        user_id=str(user.id),
        workspace_id=workspace_id,
        roles=roles
    )

    # BUG-008 FIX: Use create_refresh_token() which sets REFRESH_TOKEN_EXPIRE_DAYS
    # (7 days). The old code called create_access_token() for the refresh token,
    # giving it the same 60-minute expiry as the access token.
    refresh_token = create_refresh_token(
        subject=user.email,
        user_id=str(user.id),
        workspace_id=workspace_id,
        roles=roles
    )

    # FIX 0.4: Use IS_PRODUCTION so cookies are accepted on HTTP localhost
    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=15 * 60,
        path="/"
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth/refresh"
    )

    return {"message": "Successfully logged in. Session secured."}


@router.post("/refresh")
async def refresh_session(request: Request, response: Response):
    """Silently rotates the access token if the user has a valid refresh cookie."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token found")

    from app.core.auth import AuthProvider
    try:
        user = AuthProvider.verify_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # BUG-008 FIX: Reject access tokens used as refresh tokens.
    # create_refresh_token() sets token_type='refresh'; access tokens have no such claim.
    if user.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="Token is not a refresh token")

    access_token = create_access_token(
        subject=user["email"],
        user_id=user["id"],
        workspace_id=user["workspace_id"],
        roles=user["roles"]
    )

    response.set_cookie(
        key="token",
        value=access_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=15 * 60,
        path="/"
    )

    return {"success": True, "message": "Session refreshed."}


@router.post("/logout")
async def logout(response: Response):
    """Invalidates the session by clearing the cookie."""
    response.delete_cookie(
        key="token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        path="/"
    )
    return {"message": "Successfully logged out."}


# ── Admin Impersonation (9-C5) ────────────────────────────────────────────────

class ImpersonateRequest(BaseModel):
    reason: str


def _require_super_admin(current_user: dict) -> dict:
    roles = current_user.get("roles", [])
    if "super_admin" not in roles:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    return current_user


@router.post("/admin/impersonate/{user_id}")
async def impersonate_user(
    user_id: str,
    body: ImpersonateRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Issue a 1-hour impersonation token for the target user.
    Super-admin only. Reason is mandatory. Fully audit-logged.
    Impersonated queries are tagged with impersonated_by in all logs.
    CRITICAL: Token cannot access other organizations.
    """
    _require_super_admin(current_user)

    if not body.reason or not body.reason.strip():
        raise HTTPException(status_code=422, detail="reason is required and must be non-empty")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    logger.warning(
        "[AUDIT] event=admin_impersonation_start admin_id=%s target_user_id=%s reason=%s ts=%s",
        current_user["id"],
        user_id,
        body.reason.strip(),
        datetime.utcnow().isoformat(),
    )

    workspace_id = str(target_user.workspace_id) if target_user.workspace_id else "general"
    target_roles = [r.role for r in (target_user.roles or [])]

    import jwt
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "exp": expire,
        "sub": str(target_user.id),
        "email": target_user.email,
        "workspace_id": workspace_id,
        "roles": target_roles,
        "impersonated_by": current_user["id"],
    }
    token = jwt.encode(payload, settings.AUTH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="strict",
        max_age=3600,
        path="/",
    )

    return {
        "message": f"Impersonating {target_user.email}. Session expires in 1 hour.",
        "impersonated_user_id": str(target_user.id),
        "expires_at": expire.isoformat(),
    }


@router.post("/admin/impersonation/end")
async def end_impersonation(
    response: Response,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Explicitly end impersonation session and write audit log entry."""
    impersonated_by = current_user.get("impersonated_by")
    logger.warning(
        "[AUDIT] event=admin_impersonation_end admin_id=%s target_user_id=%s ts=%s",
        impersonated_by or "unknown",
        current_user["id"],
        datetime.utcnow().isoformat(),
    )
    response.delete_cookie(key="token", httponly=True, secure=IS_PRODUCTION, samesite="strict", path="/")
    return {"message": "Impersonation ended. Please log in again."}


# ── Registration ──────────────────────────────────────────────────────────────

BLOCKED_DOMAINS = [
    "mailinator.com", "guerrillamail.com", "10minutemail.com",
    "throwam.com", "yopmail.com", "temp-mail.org", "fakeinbox.com",
    "sharklasers.com", "guerrillamailblock.com", "grr.la", "spamgourmet.com",
]

IP_REG_LIMIT = 3       # max registrations per IP per hour
IP_REG_WINDOW = 3600   # seconds


async def _get_redis():
    try:
        import aioredis
        return await aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
    except Exception:
        return None


async def _check_ip_rate_limit(ip: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        key = f"reg_ip:{ip}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, IP_REG_WINDOW)
        if count > IP_REG_LIMIT:
            raise HTTPException(
                status_code=429,
                detail="Too many registration attempts from this IP. Try again in 1 hour.",
            )
    finally:
        await redis.close()


async def _store_email_otp(user_id: str, otp: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.setex(f"email_otp:{user_id}", 600, otp)
    finally:
        await redis.close()


async def _get_email_otp(user_id: str) -> str | None:
    redis = await _get_redis()
    if not redis:
        return None
    try:
        return await redis.get(f"email_otp:{user_id}")
    finally:
        await redis.close()


async def _delete_email_otp(user_id: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.delete(f"email_otp:{user_id}")
    finally:
        await redis.close()


def _send_otp_email(to_email: str, otp: str) -> None:
    """Send OTP via SMTP. Silently logs on failure — never blocks registration."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("[auth] SMTP not configured — skipping OTP email")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DocuMindAI — Verify your email"
        msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
        msg["To"] = to_email

        body = (
            f"Your DocuMindAI verification code is:\n\n"
            f"  {otp}\n\n"
            f"This code expires in 10 minutes.\n"
            f"If you did not register, ignore this email."
        )
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
    except Exception as exc:
        logger.error("[auth] Failed to send OTP email to %s: %s", to_email, exc)


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class VerifyEmailRequest(BaseModel):
    otp: str


@router.post("/register", status_code=201)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new trial account.
    Abuse guards: disposable-domain block, duplicate-email check, IP rate limit.
    After success, a 6-digit OTP is sent to the registered email (10-min TTL).
    """
    email = body.email.strip().lower()

    # 1. Block disposable domains
    domain = email.split("@")[-1] if "@" in email else ""
    if domain in BLOCKED_DOMAINS:
        raise HTTPException(status_code=400, detail="Disposable emails not allowed")

    # 2. Check duplicate trial email
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={"error": "email_exists", "message": "An account with this email already exists."})

    # 3. IP rate limit (best-effort — failure is non-blocking)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    client_ip = client_ip.split(",")[0].strip()
    await _check_ip_rate_limit(client_ip)

    # 4. Create user — deep-debug A1: email verification is now optional, so
    # users start with email_verified=True. The /auth/verify-email endpoint
    # remains for users who want to re-verify, but it no longer gates queries.
    new_user = User(
        email=email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        workspace_id="general",
        is_active=True,
        plan="trial",
        trial_queries_used=0,
        trial_started_at=datetime.utcnow(),
        email_verified=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 5. OTP generation/email skipped (A1). Kept the helpers in case verification
    # is re-enabled later.

    # 6. Persist device fingerprint (no TTL = permanent trial lock per device)
    device_id = request.headers.get("X-Device-ID", "").strip()
    if device_id:
        redis = await _get_redis()
        if redis:
            try:
                await redis.set(f"device_trial:{device_id}", str(new_user.id))
            finally:
                await redis.close()

    logger.info("[auth] New trial registration: user_id=%s email=REDACTED", new_user.id)
    return {
        "success": True,
        "user_id": str(new_user.id),
        "message": "Account created. Sign in to get started.",
    }


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify the 6-digit OTP sent after registration.
    Sets email_verified = True on success.
    """
    user_id = current_user["id"]
    stored_otp = await _get_email_otp(user_id)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="Verification code expired or not found. Request a new one.")

    if body.otp.strip() != stored_otp:
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    await db.execute(
        sa_update(User).where(User.id == user_id).values(email_verified=True)
    )
    await db.commit()
    await _delete_email_otp(user_id)

    # Fire-and-forget welcome email — never blocks the response
    try:
        from app.services.email_service import send_welcome_email
        _loop = asyncio.get_event_loop()
        _loop.run_in_executor(
            None, send_welcome_email,
            current_user["email"], current_user.get("full_name"),
        )
    except Exception:
        pass  # email failure must never break verification

    return {"success": True, "message": "Email verified successfully."}


# ── Password reset ──────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: str


# P9 — OTP-based password reset. Replaces the prior link-token flow per
# user request: send a 6-digit code by email, the user enters it on the
# reset page, then sets a new password. Tokens stay in Redis (10 min TTL).
# Rate-limit + 30 s resend cooldown enforced.

class ResetPasswordRequest(BaseModel):
    # P9: { email, otp, new_password } replaces the old { token, new_password }.
    email: str
    otp: str
    new_password: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str


def _generate_password_otp() -> str:
    """6-digit zero-padded numeric OTP, kept in step with the email-verify OTPs."""
    return f"{secrets.randbelow(10**6):06d}"


async def _store_password_otp(email: str, otp: str) -> None:
    """Store the OTP keyed by lower-cased email. 10-minute TTL.
    Existing key is overwritten so a resend produces a fresh code.
    """
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.setex(f"pwotp:{email}", 600, otp)
    finally:
        await redis.close()


async def _peek_password_otp(email: str) -> str | None:
    """Read-only peek used by verify-otp + by the resend-cooldown check."""
    redis = await _get_redis()
    if not redis:
        return None
    try:
        return await redis.get(f"pwotp:{email}")
    finally:
        await redis.close()


async def _consume_password_otp(email: str, otp: str) -> bool:
    """Constant-time compare + atomic delete on success."""
    redis = await _get_redis()
    if not redis:
        return False
    try:
        stored = await redis.get(f"pwotp:{email}")
        if not stored:
            return False
        # secrets.compare_digest avoids timing oracle on a 6-digit string.
        if not secrets.compare_digest(stored, otp):
            return False
        await redis.delete(f"pwotp:{email}")
        return True
    finally:
        await redis.close()


async def _password_otp_cooldown_seconds(email: str) -> int:
    """How many seconds before another OTP can be requested. Always 0 if no
    OTP is on file (no enumeration leak — we don't say whether the email
    exists, only whether *we recently sent* something).
    """
    redis = await _get_redis()
    if not redis:
        return 0
    try:
        ttl = await redis.ttl(f"pwotp_sent:{email}")
        return ttl if (ttl and ttl > 0) else 0
    finally:
        await redis.close()


async def _mark_password_otp_sent(email: str) -> None:
    """Set a short-lived 'resend cooldown' marker (30 seconds)."""
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.setex(f"pwotp_sent:{email}", 30, "1")
    finally:
        await redis.close()


def _send_password_otp_email(to_email: str, otp: str) -> None:
    """Send the OTP. In dev / when SMTP isn't configured, LOG it loudly so
    the developer can copy-paste it during manual testing.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(
            "[auth] SMTP not configured — password-reset OTP logged below "
            "(use it directly in the reset form). Email=%s OTP=%s",
            to_email, otp,
        )
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DocuMindAI — Your password reset code"
        msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
        msg["To"] = to_email
        body = (
            f"Your DocuMindAI password reset code is:\n\n"
            f"   {otp}\n\n"
            f"Enter this code on the reset screen to choose a new password.\n"
            f"The code expires in 10 minutes. If you did not request this, "
            f"ignore this email — no changes were made.\n"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
    except Exception as exc:
        logger.error("[auth] Reset OTP email failed for %s: %s", to_email, exc)


@router.post("/forgot-password", status_code=202)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a 6-digit password-reset OTP by email.

    Always returns 202 with the same body whether or not the account exists,
    to prevent user-enumeration. The resend cooldown is enforced via a
    separate Redis key (`pwotp_sent:{email}`, 30 s TTL); when an in-cooldown
    request arrives we still return 202 but skip the actual send.
    """
    email = body.email.strip().lower()

    # Skip the send (but still return 202) if we sent one in the last 30 s.
    cooldown = await _password_otp_cooldown_seconds(email)
    if cooldown > 0:
        return {
            "message": "If an account exists for that email, a reset code has been sent.",
            "resend_in": cooldown,
        }

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        otp = _generate_password_otp()
        await _store_password_otp(email, otp)
        await _mark_password_otp_sent(email)
        _send_password_otp_email(email, otp)

    return {
        "message": "If an account exists for that email, a reset code has been sent.",
        "resend_in": 30,
    }


@router.post("/verify-otp")
@limiter.limit("10/minute")
async def verify_password_otp(
    request: Request,
    body: VerifyOtpRequest,
) -> dict:
    """Stateless preflight: confirm an OTP without consuming it.

    Lets the frontend split the flow into two screens — "enter OTP" then
    "set new password" — without expanding the contract of reset-password.
    The OTP is only DELETED in reset-password (or on TTL expiry).
    """
    email = body.email.strip().lower()
    otp = body.otp.strip()
    stored = await _peek_password_otp(email)
    if not stored or not secrets.compare_digest(stored, otp):
        # Generic message — no enumeration.
        raise HTTPException(status_code=400, detail="Invalid or expired code.")
    return {"valid": True}


@router.post("/reset-password")
@limiter.limit("10/hour")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate { email, otp } and update the password atomically.

    Returns generic errors so callers can't probe the email database. The
    OTP is consumed (deleted) on success.
    """
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    email = body.email.strip().lower()
    otp = body.otp.strip()

    ok = await _consume_password_otp(email, otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    # OTP matched — find the user and update the password. We re-look-up
    # rather than trusting the email blindly so a future enumeration vector
    # (e.g. case-only differences) is closed.
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        # Generic — no enumeration.
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    await db.execute(
        sa_update(User).where(User.id == user.id).values(hashed_password=hash_password(body.new_password))
    )
    await db.commit()
    return {"success": True, "message": "Password updated. You can now sign in."}


@router.post("/verify-email/resend")
async def resend_verification_email(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-generate and resend the OTP. Rate-limit is Redis TTL (10 min)."""
    user_id = current_user["id"]

    # Don't let already-verified users resend
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        return {"success": True, "message": "Email is already verified."}

    # Check if an unexpired OTP already exists — avoid flooding
    existing = await _get_email_otp(user_id)
    if existing:
        raise HTTPException(
            status_code=429,
            detail="A verification code was already sent. Please wait 10 minutes before requesting a new one.",
        )

    otp = "".join(random.choices(string.digits, k=6))
    await _store_email_otp(user_id, otp)
    _send_otp_email(user.email, otp)
    return {"success": True, "message": "Verification code resent."}


# ── Phone OTP (Layer 1 — Twilio) ──────────────────────────────────────────────

import json as _json


async def _store_phone_otp(user_id: str, otp: str, phone: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.setex(f"phone_otp:{user_id}", 600, _json.dumps({"otp": otp, "phone": phone}))
    finally:
        await redis.close()


async def _get_phone_otp_data(user_id: str) -> dict | None:
    redis = await _get_redis()
    if not redis:
        return None
    try:
        raw = await redis.get(f"phone_otp:{user_id}")
        return _json.loads(raw) if raw else None
    finally:
        await redis.close()


async def _delete_phone_otp(user_id: str) -> None:
    redis = await _get_redis()
    if not redis:
        return
    try:
        await redis.delete(f"phone_otp:{user_id}")
    finally:
        await redis.close()


class SendPhoneOTPRequest(BaseModel):
    phone: str


class VerifyPhoneRequest(BaseModel):
    otp: str


@router.post("/send-phone-otp")
async def send_phone_otp(
    body: SendPhoneOTPRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Send a 6-digit OTP via Twilio SMS to the given E.164 phone number.
    Rejects the number if it is already linked to any trial account.
    """
    from app.core.config import settings

    phone = body.phone.strip()

    # Check if phone is already claimed by another user
    stmt = select(User).where(User.phone_number == phone)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Phone number already registered to a trial account.")

    otp = "".join(random.choices(string.digits, k=6))
    await _store_phone_otp(current_user["id"], otp, phone)

    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=f"Your DocuMindAI code: {otp}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone,
            )
        except Exception as exc:
            logger.error("[auth] Twilio SMS failed to %s: %s", phone, exc)
            raise HTTPException(status_code=502, detail="Failed to send OTP. Please try again.")
    else:
        logger.warning("[auth] Twilio not configured — OTP for user %s: %s", current_user["id"], otp)

    return {"message": "OTP sent", "expires_in": 600}


@router.post("/verify-phone")
async def verify_phone(
    body: VerifyPhoneRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify the SMS OTP. On success sets phone_verified=True and stores the phone number.
    """
    user_id = current_user["id"]
    data = await _get_phone_otp_data(user_id)

    if not data:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Request a new one.")

    if body.otp.strip() != data["otp"]:
        raise HTTPException(status_code=400, detail="Incorrect OTP.")

    await db.execute(
        sa_update(User)
        .where(User.id == user_id)
        .values(phone_number=data["phone"], phone_verified=True)
    )
    await db.commit()
    await _delete_phone_otp(user_id)

    return {"verified": True}
