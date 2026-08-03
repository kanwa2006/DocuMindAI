"""Regression guard for the silent-failure table entry `auth.py:263` /
`feedback.py:41`.

S12 fixed the CLIENT (aioredis was never installed; `get_redis` is now real
and logs at ERROR). It did not fix the CALLERS, which is why this entry was
re-verified against current code rather than assumed closed.

Two distinct problems hid behind one `if not redis: return`:

1. **OTP storage — a dead end presented as success.** `_store_email_otp` and
   `_store_phone_otp` returned None whether or not the code was saved. The
   caller then emailed (or SMS'd) the user a code and answered
   `{"success": true, "message": "Verification code resent."}` — for a code
   verification could never accept.

   Checked explicitly, because it would be the serious version of this bug:
   the verify path FAILS CLOSED (`if not stored_otp: raise 400`), so this was
   never an authentication bypass. It was a user who can never verify, plus a
   wasted Twilio message.

2. **Rate limits genuinely not enforced.** Registration-IP and feedback limits
   still fail OPEN — whether a Redis outage should block all registration is a
   business decision, parked under OWNER DECISIONS. What is not a business
   decision is doing it silently: an abuse control that is off must say so.
"""
import ast
import inspect
import textwrap

from app.api.v1.endpoints import auth as auth_module
from app.api.v1.endpoints import feedback as feedback_module


def _fn_src(module, name):
    return inspect.getsource(getattr(module, name))


def test_otp_storage_reports_whether_it_stored_anything():
    for fn in ("_store_email_otp", "_store_phone_otp"):
        src = _fn_src(auth_module, fn)
        assert "-> bool" in src, (
            f"{fn} does not report success. Its caller then sends a code that "
            "verification cannot accept and answers success."
        )
        assert "return False" in src and "return True" in src, (
            f"{fn} must return False when the code was not stored."
        )


def test_no_code_is_sent_when_it_could_not_be_stored():
    resend = _fn_src(auth_module, "resend_verification_email")
    assert "if not await _store_email_otp" in resend, (
        "the email OTP is sent without checking that it was stored. The user "
        "receives a code that can never work and is told it was sent."
    )
    assert "status_code=503" in resend

    phone = _fn_src(auth_module, "send_phone_otp")
    assert "if not await _store_phone_otp" in phone, (
        "an SMS is sent without checking the OTP was stored — a dead end for "
        "the user and a billed Twilio message for the owner."
    )
    assert "status_code=503" in phone


def test_otp_verification_still_fails_closed():
    """The serious version of this bug, explicitly pinned.

    If a missing stored OTP compared equal to a missing submitted one, this
    would be an authentication bypass. It does not — but that must stay true.
    """
    verify = _fn_src(auth_module, "verify_email")
    tree = ast.parse(textwrap.dedent(verify))

    raises_on_missing = any(
        isinstance(node, ast.If)
        and any(isinstance(n, ast.Raise) for n in ast.walk(node))
        and "stored_otp" in ast.dump(node.test)
        for node in ast.walk(tree)
    )
    assert raises_on_missing, (
        "verify_email no longer rejects a missing stored OTP. If storage "
        "silently fails and verification accepts the absence, that is an "
        "authentication bypass, not a degraded feature."
    )


def test_unenforced_rate_limits_say_so():
    """Fail-open is a policy choice; failing open SILENTLY is not."""
    for module, fn, label in (
        (auth_module, "_check_ip_rate_limit", "registration IP"),
        (feedback_module, "_check_feedback_rate_limit", "feedback"),
    ):
        src = _fn_src(module, fn)
        tree = ast.parse(textwrap.dedent(src))

        logs_error = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "error"
            for node in ast.walk(tree)
        )
        assert logs_error, (
            f"the {label} rate limit returns silently when Redis is "
            "unavailable, so an abuse control is disabled with no evidence "
            "anywhere that it is off."
        )
