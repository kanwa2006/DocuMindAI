"""
OTP password reset via Gmail SMTP.
Add to .env: EMAIL_USER=your@gmail.com  EMAIL_PASS=your_app_password
"""
import os, random, string, smtplib, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from backend.db.database import get_db
from backend.db.models import User
from backend.auth.utils import hash_password

router = APIRouter(prefix="/auth", tags=["password-reset"])

# In-memory OTP store: {email: {otp, expires_at, username, verified}}
_otp_store = {}


def _send_otp_email(to_email: str, otp: str, username: str) -> bool:
    EMAIL_USER = os.getenv("EMAIL_USER", "")
    EMAIL_PASS = os.getenv("EMAIL_PASS", "").replace(" ", "")
    if not EMAIL_USER or not EMAIL_PASS:
        print(f"[OTP DEV] OTP for {to_email}: {otp}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "DocuMind AI - Password Reset OTP"
        # ✅ Fixed sender name to show project name
        msg["From"] = "DocuMind AI <{}>".format(EMAIL_USER)
        msg["To"] = to_email

        html = """<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0d1117;font-family:'Segoe UI',sans-serif;">
<div style="max-width:460px;margin:40px auto;background:#161b22;border:1px solid #30363d;border-radius:16px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#6366f1,#7c3aed);padding:24px 32px;text-align:center;">
    <div style="font-size:32px;">&#x1F9E0;</div>
    <h1 style="margin:6px 0 0;color:#fff;font-size:20px;font-weight:800;">DocuMind AI</h1>
    <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:12px;">Password Reset</p>
  </div>
  <div style="padding:28px 32px;">
    <p style="margin:0 0 6px;color:#e6edf3;font-size:15px;">Hi <strong>{username}</strong>,</p>
    <p style="margin:0 0 20px;color:#8b949e;font-size:13px;">
      Use this OTP to reset your DocuMind AI password.<br>
      This code expires in <strong style="color:#f0f6fc;">10 minutes</strong>.
    </p>
    <div style="background:#0d1117;border:2px dashed #6366f1;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px;">
      <p style="margin:0 0 4px;color:#8b949e;font-size:11px;letter-spacing:2px;text-transform:uppercase;">Your OTP Code</p>
      <p style="margin:0;color:#818cf8;font-size:38px;font-weight:800;letter-spacing:10px;">{otp}</p>
    </div>
    <p style="margin:0;color:#484f58;font-size:11px;">
      If you did not request this, please ignore this email. Your password remains unchanged.
    </p>
  </div>
  <div style="padding:12px 32px;border-top:1px solid #21262d;text-align:center;">
    <p style="margin:0;color:#484f58;font-size:11px;">DocuMind AI - IcfaiTech Hyderabad</p>
  </div>
</div></body></html>""".format(username=username, otp=otp)

        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_USER, EMAIL_PASS)
            s.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"[OTP] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[OTP] Email failed: {e}")
        return False


# ── Request models ────────────────────────────────────────────────────────────
class SendOTPRequest(BaseModel):
    email: EmailStr

class CheckOTPRequest(BaseModel):
    """Only verifies the OTP — does NOT reset password."""
    email: EmailStr
    otp: str

class ResetPasswordRequest(BaseModel):
    """Resets password after OTP has been verified."""
    email: EmailStr
    otp: str
    new_password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post("/send-otp")
def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    """Send OTP to registered email."""
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(404, "No account found with this email address")

    otp = "".join(random.choices(string.digits, k=6))
    _otp_store[req.email] = {
        "otp": otp,
        "expires_at": time.time() + 600,  # 10 minutes
        "username": user.username,
        "verified": False
    }
    print(f"[OTP] Generated OTP {otp} for {req.email}")

    sent = _send_otp_email(req.email, otp, user.username)
    if sent:
        return {"message": f"OTP sent to {req.email}", "sent": True}
    # Dev mode — show OTP in response if email not configured
    return {"message": "Email not configured. Check server logs.", "sent": False, "dev_otp": otp}


@router.post("/check-otp")
def check_otp(req: CheckOTPRequest, db: Session = Depends(get_db)):
    """
    Step 2: Verify the OTP without resetting password.
    Sets verified=True in store so verify-otp can proceed.
    """
    email = req.email
    entered_otp = req.otp.strip()

    if email not in _otp_store:
        raise HTTPException(400, "No OTP found. Please request a new OTP.")

    stored = _otp_store[email]

    if time.time() > stored["expires_at"]:
        del _otp_store[email]
        raise HTTPException(400, "OTP has expired. Please request a new one.")

    if stored["otp"] != entered_otp:
        raise HTTPException(400, "Incorrect OTP. Please check and try again.")

    # ✅ Mark as verified
    _otp_store[email]["verified"] = True
    print(f"[OTP] OTP verified for {email}")
    return {"message": "OTP verified successfully", "verified": True}


@router.post("/verify-otp")
def verify_otp(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Step 3: Reset password. Only works if check-otp was called successfully.
    """
    email = req.email
    entered_otp = req.otp.strip()

    if email not in _otp_store:
        raise HTTPException(400, "Session expired. Please request a new OTP.")

    stored = _otp_store[email]

    if time.time() > stored["expires_at"]:
        del _otp_store[email]
        raise HTTPException(400, "OTP expired. Please request a new one.")

    if stored["otp"] != entered_otp:
        raise HTTPException(400, "Invalid OTP.")

    # Must have been pre-verified via check-otp
    if not stored.get("verified", False):
        raise HTTPException(400, "OTP not verified. Please complete step 2 first.")

    if len(req.new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")

    user.hashed_password = hash_password(req.new_password)
    db.commit()
    del _otp_store[email]
    print(f"[OTP] Password reset for {user.username}")
    return {"message": f"Password reset successfully! Welcome back, {user.username}"}
