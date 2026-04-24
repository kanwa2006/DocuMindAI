import React, { useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authAPI } from "../api/client";

const S = `
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
.ap{min-height:100vh;background:#080b12;display:flex;align-items:center;justify-content:center;font-family:'DM Sans',sans-serif;padding:16px;position:relative;overflow:hidden}
.glow1{position:fixed;top:-20%;left:30%;width:600px;height:500px;background:radial-gradient(ellipse,rgba(99,102,241,0.14) 0%,transparent 60%);pointer-events:none;z-index:0}
.glow2{position:fixed;bottom:-20%;right:0%;width:500px;height:400px;background:radial-gradient(ellipse,rgba(139,92,246,0.1) 0%,transparent 60%);pointer-events:none;z-index:0}
.card{background:#0e1320;border:1px solid rgba(255,255,255,0.07);border-radius:20px;padding:28px 28px 24px;width:100%;max-width:400px;position:relative;z-index:1;box-shadow:0 24px 64px rgba(0,0,0,0.6)}
.logo{display:flex;align-items:center;gap:10px;margin-bottom:24px}
.logo-box{width:38px;height:38px;background:linear-gradient(135deg,#6366f1,#8b5cf6);border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:19px;box-shadow:0 4px 12px rgba(99,102,241,0.4);flex-shrink:0}
.logo-txt{font-family:'Plus Jakarta Sans',sans-serif;font-size:17px;font-weight:800;color:#f1f5f9;letter-spacing:-0.4px}
.logo-txt span{color:#818cf8}
.ttl{font-family:'Plus Jakarta Sans',sans-serif;font-size:22px;font-weight:800;color:#f1f5f9;margin-bottom:4px;letter-spacing:-0.4px}
.sub{color:#64748b;font-size:13px;margin-bottom:22px;line-height:1.5}
.field{margin-bottom:12px}
.lbl{display:block;font-size:11px;font-weight:600;color:#475569;margin-bottom:5px;text-transform:uppercase;letter-spacing:.8px}
.inp-wrap{position:relative;display:flex;align-items:center}
.inp{width:100%;background:#131929;border:1.5px solid rgba(255,255,255,0.07);border-radius:10px;padding:11px 40px 11px 13px;color:#e6edf3;font-family:'DM Sans',sans-serif;font-size:14px;outline:none;transition:all .2s}
.inp:focus{border-color:rgba(99,102,241,0.6);background:#141b2e;box-shadow:0 0 0 3px rgba(99,102,241,0.1)}
.inp::placeholder{color:#2d3748;font-size:13px}
.inp-no-icon{padding-right:13px}
.eye{position:absolute;right:11px;background:none;border:none;cursor:pointer;color:#334155;font-size:15px;padding:2px;line-height:1;transition:color .2s;top:50%;transform:translateY(-50%)}
.eye:hover{color:#94a3b8}
.btn{width:100%;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;border:none;border-radius:11px;padding:12px;font-family:'Plus Jakarta Sans',sans-serif;font-weight:700;font-size:14px;cursor:pointer;margin-top:4px;transition:all .2s;box-shadow:0 4px 16px rgba(99,102,241,0.35);letter-spacing:0.1px}
.btn:hover{opacity:.9;transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.btn:disabled{opacity:.4;cursor:not-allowed;transform:none}
.btn-ghost{width:100%;background:rgba(99,102,241,0.06);color:#818cf8;border:1.5px solid rgba(99,102,241,0.2);border-radius:11px;padding:11px;font-family:'DM Sans',sans-serif;font-weight:600;font-size:13px;cursor:pointer;margin-top:6px;transition:all .2s}
.btn-ghost:hover{background:rgba(99,102,241,0.12);border-color:rgba(99,102,241,0.4)}
.btn-ghost:disabled{opacity:.4;cursor:not-allowed}
.err{background:rgba(239,68,68,.07);border:1px solid rgba(239,68,68,.2);color:#fc8181;padding:9px 13px;border-radius:9px;font-size:12.5px;margin-bottom:12px;display:flex;align-items:center;gap:7px}
.ok{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.2);color:#6ee7b7;padding:9px 13px;border-radius:9px;font-size:12.5px;margin-bottom:12px;display:flex;align-items:center;gap:7px}
.foot{text-align:center;margin-top:16px;font-size:13px;color:#475569}
.foot a{color:#818cf8;text-decoration:none;font-weight:600}
.foot a:hover{color:#a5b4fc}
.forg{background:none;border:none;color:#6366f1;font-size:11.5px;cursor:pointer;font-family:'DM Sans',sans-serif;padding:0;float:right;margin-top:4px;transition:color .2s;font-weight:500}
.forg:hover{color:#a5b4fc}
.back{background:none;border:none;color:#475569;font-size:12.5px;cursor:pointer;font-family:'DM Sans',sans-serif;display:flex;align-items:center;gap:5px;padding:0;margin-bottom:16px;transition:color .2s;font-weight:500}
.back:hover{color:#e6edf3}
.steps{display:flex;gap:5px;justify-content:center;margin-bottom:18px}
.step{height:3px;border-radius:99px;background:rgba(255,255,255,0.07);transition:all .35s}
.step.done{background:#6366f1;width:28px}
.step.cur{background:#818cf8;width:18px}
.step.todo{width:10px}
.otp-row{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin:14px 0}
.otp-inp{background:#131929;border:1.5px solid rgba(255,255,255,0.08);border-radius:9px;padding:12px 0;color:#e6edf3;font-family:'Plus Jakarta Sans',sans-serif;font-size:19px;font-weight:700;text-align:center;outline:none;transition:all .2s;width:100%}
.otp-inp:focus{border-color:rgba(99,102,241,0.6);box-shadow:0 0 0 3px rgba(99,102,241,0.1);background:#141b2e}
.otp-inp.filled{border-color:rgba(99,102,241,0.35);color:#a5b4fc}
.hint{font-size:12px;color:#475569;margin-top:3px;line-height:1.5}
.verified-badge{background:rgba(52,211,153,0.1);border:1px solid rgba(52,211,153,0.3);color:#6ee7b7;padding:8px 13px;border-radius:9px;font-size:13px;margin-bottom:14px;display:flex;align-items:center;gap:8px;font-weight:600}
`;

const Logo = () => (
  <div className="logo">
    <div className="logo-box">🧠</div>
    <div className="logo-txt">DocuMind <span>AI</span></div>
  </div>
);

// ── LOGIN ─────────────────────────────────────────────────────────────────────
export function Login({ onLogin }) {
  const [u, setU]           = useState("");
  const [p, setP]           = useState("");
  const [show, setShow]     = useState(false);
  const [err, setErr]       = useState("");
  const [busy, setBusy]     = useState(false);
  const [forgot, setForgot] = useState(false);
  const nav = useNavigate();

  const go = async () => {
    if (!u || !p) return setErr("Please fill in all fields");
    setErr(""); setBusy(true);
    try {
      const r = await authAPI.login(u, p);
      onLogin(r.data.access_token, r.data.username);
      nav("/chat");
    } catch(e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "Invalid username/email or password");
    }
    setBusy(false);
  };

  if (forgot) return <ForgotPw onBack={() => { setForgot(false); setErr(""); }} />;

  return (
    <>
      <style>{S}</style>
      <div className="ap">
        <div className="glow1" /><div className="glow2" />
        <div className="card">
          <Logo />
          <h1 className="ttl">Welcome back</h1>
          <p className="sub">Sign in with your username or email</p>
          {err && <div className="err">⚠️ {err}</div>}

          <div className="field">
            <label className="lbl">Username or Email</label>
            <div className="inp-wrap">
              <input className="inp inp-no-icon" value={u} onChange={e => setU(e.target.value)}
                placeholder="username or email@example.com"
                onKeyDown={e => e.key === "Enter" && go()} />
            </div>
          </div>

          <div className="field">
            <label className="lbl">Password</label>
            <div className="inp-wrap">
              <input className="inp" type={show ? "text" : "password"} value={p}
                onChange={e => setP(e.target.value)} placeholder="••••••••"
                onKeyDown={e => e.key === "Enter" && go()} />
              <button className="eye" onClick={() => setShow(s => !s)}>{show ? "🙈" : "👁"}</button>
            </div>
            <button className="forg" onClick={() => setForgot(true)}>Forgot password?</button>
          </div>

          <div style={{ clear: "both", marginBottom: 2 }} />
          <button className="btn" onClick={go} disabled={busy}>
            {busy ? "Signing in..." : "Sign In →"}
          </button>
          <div className="foot">Don't have an account? <Link to="/register">Create one free</Link></div>
        </div>
      </div>
    </>
  );
}

// ── FORGOT PASSWORD — 3 steps with BACKEND OTP VERIFICATION on step 2 ────────
function ForgotPw({ onBack }) {
  const [step, setStep]       = useState(1);
  const [email, setEmail]     = useState("");
  const [otp, setOtp]         = useState(["", "", "", "", "", ""]);
  const [np, setNp]           = useState("");
  const [cp, setCp]           = useState("");
  const [snp, setSnp]         = useState(false);
  const [scp, setScp]         = useState(false);
  const [busy, setBusy]       = useState(false);
  const [err, setErr]         = useState("");
  const [ok, setOk]           = useState("");
  const [timer, setTimer]     = useState(0);
  // Track that OTP was verified by backend before allowing step 3
  const [otpVerified, setOtpVerified] = useState(false);
  const refs = [useRef(), useRef(), useRef(), useRef(), useRef(), useRef()];
  const timerRef = useRef(null);

  const startTimer = () => {
    setTimer(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => setTimer(t => {
      if (t <= 1) { clearInterval(timerRef.current); return 0; }
      return t - 1;
    }), 1000);
  };

  const sendOtp = async () => {
    const trimmed = email.trim();
    if (!trimmed || !trimmed.includes("@")) return setErr("Please enter a valid email address");
    setErr(""); setBusy(true);
    try {
      await authAPI.sendOTP({ email: trimmed });
      setStep(2);
      setOtpVerified(false);
      startTimer();
    } catch(e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "No account found with this email");
    }
    setBusy(false);
  };

  const handleOtp = (i, val) => {
    if (!/^\d*$/.test(val)) return;
    const n = [...otp]; n[i] = val.slice(-1); setOtp(n);
    if (val && i < 5) refs[i + 1].current?.focus();
    if (!val && i > 0) refs[i - 1].current?.focus();
  };

  const handlePaste = e => {
    const t = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (t.length === 6) { setOtp(t.split("")); refs[5].current?.focus(); e.preventDefault(); }
  };

  // ✅ FIXED: Verify OTP against backend BEFORE proceeding to step 3
  const verifyOtpWithBackend = async () => {
    const code = otp.join("");
    if (code.length < 6) return setErr("Please enter all 6 digits");
    setErr(""); setBusy(true);
    try {
      // Call backend to verify OTP — if wrong, backend throws 400 error
      // We use a dummy password here just to trigger verification
      // Actually we need a separate verify endpoint — use the existing one with a flag
      // Instead: call send-otp again won't work. Use verify-otp with a temp check.
      // The clean solution: verify OTP first, then set password in same call
      // So we verify here by calling verify-otp — if correct, move to step 3
      // We'll store the verified OTP and use it in step 3
      await authAPI.checkOTP({ email: email.trim(), otp: code });
      setOtpVerified(true);
      setStep(3);
    } catch(e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "Incorrect OTP. Please try again.");
      // Clear OTP boxes on wrong entry
      setOtp(["", "", "", "", "", ""]);
      refs[0].current?.focus();
    }
    setBusy(false);
  };

  const resetPass = async () => {
    if (!otpVerified) return setErr("Please verify OTP first");
    if (!np || !cp) return setErr("Please fill in both fields");
    if (np !== cp) return setErr("Passwords do not match");
    if (np.length < 6) return setErr("Password must be at least 6 characters");
    setErr(""); setBusy(true);
    try {
      await authAPI.verifyOTP({ email: email.trim(), otp: otp.join(""), new_password: np });
      setOk("✅ Password reset successfully! Redirecting to login...");
      setTimeout(onBack, 2000);
    } catch(e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "Session expired. Please start again.");
      // If token expired, go back to step 1
      setTimeout(() => { setStep(1); setOtpVerified(false); setErr(""); }, 2000);
    }
    setBusy(false);
  };

  return (
    <>
      <style>{S}</style>
      <div className="ap">
        <div className="glow1" /><div className="glow2" />
        <div className="card">
          <Logo />
          <button className="back" onClick={onBack}>← Back to login</button>

          <div className="steps">
            {[1, 2, 3].map(n => (
              <div key={n} className={`step ${n < step ? "done" : n === step ? "cur" : "todo"}`} />
            ))}
          </div>
          <p style={{ textAlign:"center", fontSize:11, color:"#475569", marginBottom:16, fontWeight:600, letterSpacing:".5px", textTransform:"uppercase" }}>
            Step {step} of 3 — {["Email", "Verify OTP", "New Password"][step - 1]}
          </p>

          {err && <div className="err">⚠️ {err}</div>}
          {ok  && <div className="ok">{ok}</div>}

          {/* Step 1 — Email */}
          {step === 1 && (
            <>
              <h1 className="ttl">Reset Password</h1>
              <p className="sub">Enter your registered email to receive a 6-digit OTP</p>
              <div className="field">
                <label className="lbl">Registered Email</label>
                <div className="inp-wrap">
                  <input className="inp inp-no-icon" type="email" value={email}
                    onChange={e => setEmail(e.target.value)} placeholder="your@gmail.com"
                    onKeyDown={e => e.key === "Enter" && sendOtp()} />
                </div>
              </div>
              <button className="btn" onClick={sendOtp} disabled={busy}>
                {busy ? "Sending OTP..." : "Send OTP →"}
              </button>
            </>
          )}

          {/* Step 2 — OTP (verified against backend) */}
          {step === 2 && (
            <>
              <h1 className="ttl">Enter OTP</h1>
              <p className="sub">6-digit code sent to <strong style={{ color:"#818cf8" }}>{email}</strong></p>
              <div className="otp-row" onPaste={handlePaste}>
                {otp.map((v, i) => (
                  <input key={i} ref={refs[i]} className={`otp-inp${v ? " filled" : ""}`}
                    value={v} maxLength={1}
                    onChange={e => handleOtp(i, e.target.value)}
                    onKeyDown={e => {
                      if (e.key === "Backspace" && !v && i > 0) refs[i - 1].current?.focus();
                      if (e.key === "Enter" && otp.join("").length === 6) verifyOtpWithBackend();
                    }} />
                ))}
              </div>
              <p className="hint">💡 Paste your OTP — it auto-fills all 6 boxes</p>
              <button className="btn" style={{ marginTop: 12 }} onClick={verifyOtpWithBackend}
                disabled={otp.join("").length < 6 || busy}>
                {busy ? "Verifying..." : "Verify OTP →"}
              </button>
              <button className="btn-ghost" onClick={() => { sendOtp(); setOtp(["","","","","",""]); }}
                disabled={timer > 0 || busy}>
                {timer > 0 ? `Resend in ${timer}s` : "Resend OTP"}
              </button>
            </>
          )}

          {/* Step 3 — New Password (only reachable after backend OTP verification) */}
          {step === 3 && (
            <>
              <h1 className="ttl">New Password</h1>
              <div className="verified-badge">✅ OTP Verified — Set your new password</div>
              <div className="field">
                <label className="lbl">New Password</label>
                <div className="inp-wrap">
                  <input className="inp" type={snp ? "text" : "password"} value={np}
                    onChange={e => setNp(e.target.value)} placeholder="at least 6 characters" />
                  <button className="eye" onClick={() => setSnp(s => !s)}>{snp ? "🙈" : "👁"}</button>
                </div>
              </div>
              <div className="field">
                <label className="lbl">Confirm Password</label>
                <div className="inp-wrap">
                  <input className="inp" type={scp ? "text" : "password"} value={cp}
                    onChange={e => setCp(e.target.value)} placeholder="repeat new password"
                    onKeyDown={e => e.key === "Enter" && resetPass()} />
                  <button className="eye" onClick={() => setScp(s => !s)}>{scp ? "🙈" : "👁"}</button>
                </div>
              </div>
              <button className="btn" onClick={resetPass} disabled={busy}>
                {busy ? "Resetting..." : "Reset Password →"}
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ── REGISTER ──────────────────────────────────────────────────────────────────
export function Register() {
  const [f, setF]       = useState({ username: "", email: "", password: "" });
  const [show, setShow] = useState(false);
  const [err, setErr]   = useState("");
  const [ok, setOk]     = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const go = async () => {
    if (!f.username || !f.email || !f.password) return setErr("Please fill in all fields");
    if (f.password.length < 6) return setErr("Password must be at least 6 characters");
    setErr(""); setBusy(true);
    try {
      await authAPI.register(f);
      setOk("✅ Account created! Redirecting to login...");
      setTimeout(() => nav("/login"), 1800);
    } catch(e) {
      const d = e.response?.data?.detail;
      setErr(typeof d === "string" ? d : "Registration failed. Please try again.");
    }
    setBusy(false);
  };

  return (
    <>
      <style>{S}</style>
      <div className="ap">
        <div className="glow1" /><div className="glow2" />
        <div className="card">
          <Logo />
          <h1 className="ttl">Create account</h1>
          <p className="sub">Your private AI document workspace, free forever</p>
          {err && <div className="err">⚠️ {err}</div>}
          {ok  && <div className="ok">{ok}</div>}

          <div className="field">
            <label className="lbl">Username</label>
            <div className="inp-wrap">
              <input className="inp inp-no-icon" value={f.username}
                onChange={e => setF({ ...f, username: e.target.value })} placeholder="choose a username" />
            </div>
          </div>
          <div className="field">
            <label className="lbl">Email</label>
            <div className="inp-wrap">
              <input className="inp inp-no-icon" type="email" value={f.email}
                onChange={e => setF({ ...f, email: e.target.value })} placeholder="you@example.com" />
            </div>
          </div>
          <div className="field">
            <label className="lbl">Password</label>
            <div className="inp-wrap">
              <input className="inp" type={show ? "text" : "password"} value={f.password}
                onChange={e => setF({ ...f, password: e.target.value })}
                placeholder="at least 6 characters"
                onKeyDown={e => e.key === "Enter" && go()} />
              <button className="eye" onClick={() => setShow(s => !s)}>{show ? "🙈" : "👁"}</button>
            </div>
          </div>

          <button className="btn" onClick={go} disabled={busy}>
            {busy ? "Creating..." : "Create Account →"}
          </button>
          <div className="foot">Already have an account? <Link to="/login">Sign in</Link></div>
        </div>
      </div>
    </>
  );
}

export default Login;
