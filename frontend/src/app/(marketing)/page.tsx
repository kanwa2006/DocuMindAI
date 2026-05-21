import Link from "next/link";

/* ── DATA ─────────────────────────────────────────────────────────────────── */

const WORKSPACES = [
  {
    id: "hr",
    icon: "👥",
    name: "HR Workspace",
    accent: "var(--ws-hr-accent)",
    question: "Rank these 12 candidates by leadership experience",
    answer: "Ranked by leadership score: 1. Priya S. (8.2/10), 2. Rahul M. (7.9/10)...",
    route: "/hr",
  },
  {
    id: "finance",
    icon: "📊",
    name: "Finance Workspace",
    accent: "var(--ws-finance-accent)",
    question: "What is the net profit margin for Q3?",
    answer: "Net profit margin: 18.4%. Revenue ₹2.3Cr, Net Profit ₹4.2L...",
    route: "/finance",
  },
  {
    id: "legal",
    icon: "⚖️",
    name: "Legal Workspace",
    accent: "var(--ws-legal-accent)",
    question: "Does this contract have a penalty clause?",
    answer: "Yes. Clause 7.3 (Page 12): 15% of contract value, capped at ₹50L...",
    route: "/legal",
  },
  {
    id: "exam",
    icon: "📋",
    name: "Teacher Workspace",
    accent: "var(--ws-exam-accent)",
    question: "Generate 10 MCQs from Chapter 4",
    answer: "Q1: What is the primary function of mitochondria? (a) Protein synthesis...",
    route: "/exam",
  },
  {
    id: "research",
    icon: "🔬",
    name: "Research Workspace",
    accent: "var(--ws-research-accent)",
    question: "Summarize the methodology section",
    answer: "The study used a mixed-methods approach with 450 participants...",
    route: "/research",
  },
  {
    id: "study",
    icon: "📚",
    name: "Study Workspace",
    accent: "var(--ws-study-accent)",
    question: "Explain this concept in simple language",
    answer: "Think of it like this: the nucleus is the 'control center' of the cell...",
    route: "/study",
  },
];

const TRUST_STATS = [
  { icon: "📄", stat: "Answers only from your document", sub: "Zero hallucinations from outside your files" },
  { icon: "📍", stat: "Every answer shows exact page", sub: "See precisely where the answer came from" },
  { icon: "🗂️", stat: "7 professional workspaces", sub: "HR · Finance · Legal · Research · Teaching · Study" },
  { icon: "💳", stat: "UPI & Razorpay billing", sub: "Pay securely in ₹, no card required" },
];

const HOW_IT_WORKS = [
  {
    step: "01",
    icon: "⬆️",
    title: "Upload Your Document",
    desc: "PDF, DOCX, TXT — any file up to 50 MB",
  },
  {
    step: "02",
    icon: "⊞",
    title: "Choose Your Workspace",
    desc: "7 professional modes, each optimised for your role",
  },
  {
    step: "03",
    icon: "🛡️",
    title: "Get Verified Answers",
    desc: "Every answer shows the exact page and trust score",
  },
];

const PRICING = [
  {
    name: "Free Trial",
    price: "₹0",
    period: "",
    badge: null,
    description: "Perfect to explore the platform",
    features: [
      "10 queries free",
      "All 7 workspaces unlocked",
      "Exact page citations",
      "Trust scores on every answer",
      "No credit card required",
    ],
    cta: "Start Free Trial",
    href: "/register",
    highlighted: false,
  },
  {
    name: "Professional",
    price: "₹799",
    period: "/month",
    badge: "Most Popular",
    description: "For working professionals",
    features: [
      "200 queries per session",
      "All 7 workspaces",
      "Priority processing",
      "PDF audit reports",
      "Session export (PDF, DOCX)",
      "UPI & Razorpay billing",
    ],
    cta: "Get Professional",
    href: "/register?plan=professional",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "₹2,999",
    period: "/month",
    badge: null,
    description: "For teams & organisations",
    features: [
      "Unlimited queries",
      "All 7 workspaces",
      "PDF + DOCX audit reports",
      "Email report delivery",
      "Multi-user access",
      "Priority support",
    ],
    cta: "Contact Sales",
    href: "/register?plan=enterprise",
    highlighted: false,
  },
];

/* ── PAGE ─────────────────────────────────────────────────────────────────── */

export default function LandingPage() {
  const sectionPad = "80px max(24px, calc((100% - 1200px) / 2))";

  return (
    <div style={{ fontFamily: "var(--font-body)", color: "var(--text-primary)", background: "var(--surface-base)" }}>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 1 — HERO
      ═══════════════════════════════════════════════════════════════════ */}
      <section
        id="hero"
        style={{
          padding: "96px max(24px, calc((100% - 960px) / 2)) 80px",
          textAlign: "center",
          background: "linear-gradient(160deg, var(--brand-ghost) 0%, var(--surface-base) 60%)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        {/* Eyebrow */}
        <div style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          background: "var(--brand-ghost)",
          border: "1px solid var(--brand-glow)",
          borderRadius: "var(--radius-full)",
          padding: "4px 14px",
          marginBottom: "28px",
          fontFamily: "var(--font-body)",
          fontSize: "var(--text-xs)",
          fontWeight: "var(--weight-semibold)",
          color: "var(--text-brand)",
          letterSpacing: "var(--tracking-wide)",
          textTransform: "uppercase",
        }}>
          🇮🇳 Built for Indian Professionals
        </div>

        {/* Headline */}
        <h1 style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(2.25rem, 5vw, 3.75rem)",
          fontWeight: "var(--weight-bold)",
          lineHeight: "var(--leading-tight)",
          color: "var(--text-primary)",
          margin: "0 0 24px",
          letterSpacing: "var(--tracking-tight)",
        }}>
          Your Documents.<br />
          <span style={{ color: "var(--brand)" }}>Fully Understood.</span>
        </h1>

        {/* Subheadline */}
        <p style={{
          fontSize: "clamp(var(--text-lg), 2vw, var(--text-xl))",
          color: "var(--text-secondary)",
          lineHeight: "var(--leading-relaxed)",
          maxWidth: "600px",
          margin: "0 auto 40px",
        }}>
          Ask anything about your PDFs, contracts, or notes.<br />
          Get answers with <strong style={{ color: "var(--text-primary)" }}>exact page citations</strong>.<br />
          Built for Indian CAs, Lawyers, Teachers, and HR professionals.
        </p>

        {/* CTAs */}
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          justifyContent: "center",
          marginBottom: "20px",
        }}>
          <Link
            href="/register"
            style={{
              display: "inline-block",
              background: "var(--brand)",
              color: "#fff",
              textDecoration: "none",
              padding: "14px 28px",
              borderRadius: "var(--radius-lg)",
              fontWeight: "var(--weight-semibold)",
              fontSize: "var(--text-base)",
              boxShadow: "var(--shadow-brand)",
            }}
          >
            Start Free — 10 Queries
          </Link>
          <a
            href="#how-it-works"
            style={{
              display: "inline-block",
              background: "transparent",
              color: "var(--text-primary)",
              textDecoration: "none",
              padding: "14px 28px",
              borderRadius: "var(--radius-lg)",
              fontWeight: "var(--weight-medium)",
              fontSize: "var(--text-base)",
              border: "1.5px solid var(--border-default)",
            }}
          >
            See How It Works
          </a>
        </div>

        {/* Trust line */}
        <p style={{ fontSize: "var(--text-sm)", color: "var(--text-tertiary)" }}>
          No credit card required · 10 queries free · Cancel anytime
        </p>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 2 — TRUST BAR
      ═══════════════════════════════════════════════════════════════════ */}
      <section
        id="trust-bar"
        style={{
          padding: sectionPad,
          background: "var(--surface-raised)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "32px",
        }}>
          {TRUST_STATS.map(({ icon, stat, sub }) => (
            <div key={stat} style={{ display: "flex", alignItems: "flex-start", gap: "14px" }}>
              <span style={{ fontSize: "1.75rem", flexShrink: 0, lineHeight: 1 }}>{icon}</span>
              <div>
                <div style={{ fontWeight: "var(--weight-semibold)", fontSize: "var(--text-base)", color: "var(--text-primary)", lineHeight: "var(--leading-snug)", marginBottom: "4px" }}>
                  {stat}
                </div>
                <div style={{ fontSize: "var(--text-sm)", color: "var(--text-tertiary)", lineHeight: "var(--leading-normal)" }}>
                  {sub}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 3 — WORKSPACE SHOWCASE
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="workspaces" style={{ padding: sectionPad }}>
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(var(--text-3xl), 3vw, var(--text-4xl))",
            fontWeight: "var(--weight-bold)",
            marginBottom: "12px",
            lineHeight: "var(--leading-tight)",
          }}>
            7 Workspaces. One Platform.
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-lg)", maxWidth: "540px", margin: "0 auto" }}>
            Each workspace is tuned for your profession — so you get better answers, faster.
          </p>
        </div>

        {/* 2×3 grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "20px",
        }}>
          {WORKSPACES.map((ws) => (
            <div
              key={ws.id}
              style={{
                background: "var(--surface-raised)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-xl)",
                padding: "24px",
                display: "flex",
                flexDirection: "column",
                gap: "16px",
                transition: "box-shadow var(--dur-normal) var(--ease-standard)",
              }}
            >
              {/* Workspace header */}
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "40px",
                  height: "40px",
                  borderRadius: "var(--radius-lg)",
                  background: `color-mix(in srgb, ${ws.accent} 12%, transparent)`,
                  fontSize: "1.3rem",
                  flexShrink: 0,
                }}>
                  {ws.icon}
                </span>
                <span style={{
                  fontWeight: "var(--weight-semibold)",
                  fontSize: "var(--text-base)",
                  color: ws.accent,
                }}>
                  {ws.name}
                </span>
              </div>

              {/* Example Q&A */}
              <div style={{
                background: "var(--surface-sunken)",
                borderRadius: "var(--radius-md)",
                padding: "14px",
                flexGrow: 1,
              }}>
                <p style={{
                  fontStyle: "italic",
                  color: "var(--text-secondary)",
                  fontSize: "var(--text-sm)",
                  margin: "0 0 10px",
                  lineHeight: "var(--leading-relaxed)",
                }}>
                  "{ws.question}"
                </p>
                <p style={{
                  color: "var(--text-primary)",
                  fontSize: "var(--text-sm)",
                  margin: 0,
                  lineHeight: "var(--leading-normal)",
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical" as const,
                  overflow: "hidden",
                }}>
                  {ws.answer}
                </p>
              </div>

              {/* CTA */}
              <Link
                href={ws.route}
                style={{
                  fontSize: "var(--text-sm)",
                  color: ws.accent,
                  fontWeight: "var(--weight-medium)",
                  textDecoration: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                Try this workspace →
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 4 — HOW IT WORKS
      ═══════════════════════════════════════════════════════════════════ */}
      <section
        id="how-it-works"
        style={{
          padding: sectionPad,
          background: "var(--surface-sunken)",
          borderTop: "1px solid var(--border-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(var(--text-3xl), 3vw, var(--text-4xl))",
            fontWeight: "var(--weight-bold)",
            marginBottom: "12px",
            lineHeight: "var(--leading-tight)",
          }}>
            Up and running in 3 steps
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-lg)" }}>
            From upload to verified answer in under a minute.
          </p>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "32px",
          maxWidth: "900px",
          margin: "0 auto",
          position: "relative",
        }}>
          {HOW_IT_WORKS.map(({ step, icon, title, desc }, i) => (
            <div key={step} style={{ textAlign: "center", position: "relative" }}>
              {/* Connector line (hidden on mobile via overflow) */}
              {i < HOW_IT_WORKS.length - 1 && (
                <div style={{
                  position: "absolute",
                  top: "28px",
                  left: "calc(50% + 36px)",
                  right: "calc(-50% + 36px)",
                  height: "2px",
                  background: "var(--border-default)",
                }} />
              )}

              {/* Step circle */}
              <div style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "var(--brand)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 20px",
                fontSize: "1.5rem",
                position: "relative",
                zIndex: 1,
              }}>
                {icon}
              </div>

              <div style={{
                fontSize: "var(--text-2xs)",
                fontWeight: "var(--weight-bold)",
                color: "var(--brand)",
                letterSpacing: "var(--tracking-widest)",
                textTransform: "uppercase",
                marginBottom: "8px",
              }}>
                STEP {step}
              </div>

              <h3 style={{
                fontSize: "var(--text-xl)",
                fontWeight: "var(--weight-semibold)",
                marginBottom: "10px",
                color: "var(--text-primary)",
              }}>
                {title}
              </h3>

              <p style={{
                fontSize: "var(--text-base)",
                color: "var(--text-secondary)",
                lineHeight: "var(--leading-relaxed)",
                margin: 0,
              }}>
                {desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 5 — THE TRUST DIFFERENCE
      ═══════════════════════════════════════════════════════════════════ */}
      <section id="trust" style={{ padding: sectionPad }}>
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(var(--text-3xl), 3vw, var(--text-4xl))",
            fontWeight: "var(--weight-bold)",
            marginBottom: "12px",
            lineHeight: "var(--leading-tight)",
          }}>
            The Trust Difference
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-lg)", maxWidth: "540px", margin: "0 auto" }}>
            For professionals where a wrong answer isn't just inconvenient — it's dangerous.
          </p>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "24px",
          maxWidth: "1000px",
          margin: "0 auto",
        }}>
          {/* Left: Problem */}
          <div style={{
            background: "var(--error-bg)",
            border: "1px solid var(--error-border)",
            borderRadius: "var(--radius-xl)",
            padding: "32px",
          }}>
            <div style={{
              fontSize: "var(--text-2xs)",
              fontWeight: "var(--weight-bold)",
              letterSpacing: "var(--tracking-widest)",
              textTransform: "uppercase",
              color: "var(--error-text)",
              marginBottom: "16px",
            }}>
              ❌ Other AI Tools
            </div>
            <p style={{
              fontSize: "var(--text-lg)",
              fontWeight: "var(--weight-medium)",
              lineHeight: "var(--leading-relaxed)",
              color: "var(--text-primary)",
              margin: "0 0 16px",
            }}>
              "Other AI tools give you an answer."
            </p>
            <p style={{
              fontSize: "var(--text-base)",
              color: "var(--text-secondary)",
              lineHeight: "var(--leading-relaxed)",
              margin: 0,
            }}>
              You have no idea if it's right or hallucinated.
              For CAs, lawyers, and doctors — a wrong answer isn't
              just inconvenient. <strong style={{ color: "var(--error-text)" }}>It's dangerous.</strong>
            </p>
          </div>

          {/* Right: Solution */}
          <div style={{
            background: "var(--success-bg)",
            border: "1px solid var(--success-border)",
            borderRadius: "var(--radius-xl)",
            padding: "32px",
          }}>
            <div style={{
              fontSize: "var(--text-2xs)",
              fontWeight: "var(--weight-bold)",
              letterSpacing: "var(--tracking-widest)",
              textTransform: "uppercase",
              color: "var(--success-text)",
              marginBottom: "16px",
            }}>
              ✅ DocuMindAI
            </div>
            <p style={{
              fontSize: "var(--text-lg)",
              fontWeight: "var(--weight-medium)",
              lineHeight: "var(--leading-relaxed)",
              color: "var(--text-primary)",
              margin: "0 0 16px",
            }}>
              "DocuMindAI shows a Trust Score with every answer."
            </p>
            <p style={{
              fontSize: "var(--text-base)",
              color: "var(--text-secondary)",
              lineHeight: "var(--leading-relaxed)",
              margin: "0 0 24px",
            }}>
              You know exactly how confident the AI is,
              what page it came from, and whether any contradiction
              was found in the document.
            </p>

            {/* Mock Trust Score Badge */}
            <div style={{
              background: "var(--surface-raised)",
              border: "1px solid var(--success-border)",
              borderRadius: "var(--radius-lg)",
              padding: "16px 20px",
            }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "8px",
              }}>
                <span style={{ fontSize: "var(--text-sm)", fontWeight: "var(--weight-semibold)", color: "var(--text-primary)" }}>
                  Trust Score
                </span>
                <span style={{
                  fontSize: "var(--text-sm)",
                  fontWeight: "var(--weight-bold)",
                  color: "var(--success-text)",
                }}>
                  ✅ HIGH CONFIDENCE
                </span>
              </div>
              {/* Progress bar */}
              <div style={{
                height: "10px",
                background: "var(--surface-sunken)",
                borderRadius: "var(--radius-full)",
                overflow: "hidden",
                marginBottom: "8px",
              }}>
                <div style={{
                  height: "100%",
                  width: "87%",
                  background: "linear-gradient(90deg, var(--success-text), hsl(160, 70%, 50%))",
                  borderRadius: "var(--radius-full)",
                }} />
              </div>
              <div style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: "var(--text-xs)",
                color: "var(--text-tertiary)",
                fontFamily: "var(--font-mono)",
              }}>
                <span>0</span>
                <span style={{ fontWeight: "var(--weight-bold)", color: "var(--success-text)", fontSize: "var(--text-sm)" }}>87 / 100</span>
                <span>100</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 6 — PRICING
      ═══════════════════════════════════════════════════════════════════ */}
      <section
        id="pricing"
        style={{
          padding: sectionPad,
          background: "var(--surface-sunken)",
          borderTop: "1px solid var(--border-subtle)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{
            fontFamily: "var(--font-display)",
            fontSize: "clamp(var(--text-3xl), 3vw, var(--text-4xl))",
            fontWeight: "var(--weight-bold)",
            marginBottom: "12px",
            lineHeight: "var(--leading-tight)",
          }}>
            Simple, Transparent Pricing
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "var(--text-lg)" }}>
            Start free. Upgrade when you're ready. Pay in ₹.
          </p>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "20px",
          maxWidth: "1000px",
          margin: "0 auto 40px",
          alignItems: "start",
        }}>
          {PRICING.map((plan) => (
            <div
              key={plan.name}
              style={{
                background: plan.highlighted ? "var(--brand)" : "var(--surface-raised)",
                border: plan.highlighted ? "none" : "1px solid var(--border-default)",
                borderRadius: "var(--radius-2xl)",
                padding: "32px",
                position: "relative",
                boxShadow: plan.highlighted ? "var(--shadow-xl)" : "none",
              }}
            >
              {/* Popular badge */}
              {plan.badge && (
                <div style={{
                  position: "absolute",
                  top: "-12px",
                  left: "50%",
                  transform: "translateX(-50%)",
                  background: "var(--surface-base)",
                  color: "var(--brand)",
                  border: "1.5px solid var(--brand)",
                  borderRadius: "var(--radius-full)",
                  padding: "3px 14px",
                  fontSize: "var(--text-xs)",
                  fontWeight: "var(--weight-bold)",
                  whiteSpace: "nowrap",
                  letterSpacing: "var(--tracking-wide)",
                }}>
                  {plan.badge}
                </div>
              )}

              <div style={{
                fontSize: "var(--text-sm)",
                fontWeight: "var(--weight-semibold)",
                color: plan.highlighted ? "rgba(255,255,255,0.8)" : "var(--text-tertiary)",
                marginBottom: "8px",
                letterSpacing: "var(--tracking-wide)",
                textTransform: "uppercase",
              }}>
                {plan.name}
              </div>

              <div style={{ display: "flex", alignItems: "baseline", gap: "4px", marginBottom: "4px" }}>
                <span style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "2.5rem",
                  fontWeight: "var(--weight-bold)",
                  color: plan.highlighted ? "#fff" : "var(--text-primary)",
                  lineHeight: 1,
                }}>
                  {plan.price}
                </span>
                {plan.period && (
                  <span style={{
                    fontSize: "var(--text-base)",
                    color: plan.highlighted ? "rgba(255,255,255,0.7)" : "var(--text-tertiary)",
                  }}>
                    {plan.period}
                  </span>
                )}
              </div>

              <p style={{
                fontSize: "var(--text-sm)",
                color: plan.highlighted ? "rgba(255,255,255,0.75)" : "var(--text-secondary)",
                marginBottom: "24px",
              }}>
                {plan.description}
              </p>

              <ul style={{ listStyle: "none", padding: 0, margin: "0 0 28px", display: "flex", flexDirection: "column", gap: "10px" }}>
                {plan.features.map((f) => (
                  <li key={f} style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    fontSize: "var(--text-sm)",
                    color: plan.highlighted ? "rgba(255,255,255,0.9)" : "var(--text-secondary)",
                    lineHeight: "var(--leading-snug)",
                  }}>
                    <span style={{ flexShrink: 0, color: plan.highlighted ? "#fff" : "var(--success-text)", fontSize: "var(--text-base)" }}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <Link
                href={plan.href}
                style={{
                  display: "block",
                  textAlign: "center",
                  textDecoration: "none",
                  padding: "12px 24px",
                  borderRadius: "var(--radius-lg)",
                  fontWeight: "var(--weight-semibold)",
                  fontSize: "var(--text-base)",
                  background: plan.highlighted ? "#fff" : "var(--brand)",
                  color: plan.highlighted ? "var(--brand)" : "#fff",
                }}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>

        {/* Large CTA below pricing */}
        <div style={{ textAlign: "center" }}>
          <Link
            href="/register"
            style={{
              display: "inline-block",
              background: "var(--brand)",
              color: "#fff",
              textDecoration: "none",
              padding: "16px 40px",
              borderRadius: "var(--radius-lg)",
              fontWeight: "var(--weight-bold)",
              fontSize: "var(--text-lg)",
              boxShadow: "var(--shadow-brand-lg)",
            }}
          >
            Start Free Trial →
          </Link>
          <p style={{ marginTop: "12px", fontSize: "var(--text-sm)", color: "var(--text-tertiary)" }}>
            No credit card required · Cancel anytime
          </p>
        </div>
      </section>

      {/* ═══════════════════════════════════════════════════════════════════
          SECTION 7 — FOOTER
      ═══════════════════════════════════════════════════════════════════ */}
      <footer
        style={{
          padding: "48px max(24px, calc((100% - 1200px) / 2))",
          background: "var(--surface-raised)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "20px",
          textAlign: "center",
        }}>
          {/* Brand */}
          <div style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--text-xl)",
            color: "var(--text-primary)",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}>
            <span>🧠</span>
            <span style={{ color: "var(--brand)", fontWeight: "var(--weight-bold)" }}>DocuMind</span>
            <span>AI</span>
          </div>

          {/* Links */}
          <nav aria-label="Footer navigation" style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "8px 24px" }}>
            {[
              { label: "Privacy Policy", href: "/privacy" },
              { label: "Terms of Service", href: "/terms" },
              { label: "Contact", href: "mailto:support@documindai.com" },
              { label: "Pricing", href: "#pricing" },
            ].map(({ label, href }) => (
              <Link
                key={label}
                href={href}
                style={{
                  fontSize: "var(--text-sm)",
                  color: "var(--text-tertiary)",
                  textDecoration: "none",
                }}
              >
                {label}
              </Link>
            ))}
          </nav>

          {/* Made in India */}
          <p style={{
            fontSize: "var(--text-sm)",
            color: "var(--text-secondary)",
            fontWeight: "var(--weight-medium)",
          }}>
            Made with ❤️ in India 🇮🇳
          </p>

          {/* Copyright */}
          <p style={{ fontSize: "var(--text-xs)", color: "var(--text-disabled)", margin: 0 }}>
            © 2026 DocuMindAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
