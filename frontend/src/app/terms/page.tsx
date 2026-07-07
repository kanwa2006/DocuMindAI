import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service — DocuMindAI",
  description: "Terms and conditions for using DocuMindAI.",
};

export default function TermsPage() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-base)", color: "var(--text-primary)", fontFamily: "var(--font-body)" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "64px 24px" }}>
        <Link href="/" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)", display: "inline-flex", alignItems: "center", gap: "4px", marginBottom: "32px" }}>
          ← Back to Home
        </Link>

        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-4xl)", fontWeight: "var(--weight-bold)", marginBottom: "8px", lineHeight: "var(--leading-tight)" }}>
          Terms of Service
        </h1>
        <p style={{ color: "var(--text-tertiary)", fontSize: "var(--text-sm)", marginBottom: "48px" }}>
          Last updated: May 2026
        </p>

        {[
          {
            title: "1. Acceptance of Terms",
            body: "By accessing or using DocuMindAI, you agree to be bound by these Terms. If you do not agree, do not use the service. These Terms apply to all users, including free trial and paid subscribers.",
          },
          {
            title: "2. Use of the Service",
            body: "DocuMindAI provides AI-assisted document analysis. You may upload documents you own or have the legal right to process. You must not upload documents containing illegal content, violating third-party rights, or that you are prohibited from sharing.",
          },
          {
            title: "3. AI-Generated Answers",
            body: "Answers provided by DocuMindAI are AI-generated and grounded in your uploaded documents. They do not constitute legal, financial, medical, or professional advice. Always verify critical information with a qualified professional. DocuMindAI is not liable for decisions made based on AI outputs.",
          },
          {
            title: "4. Subscription and Billing",
            body: "Free trial accounts receive 10 queries. Paid plans are billed monthly. You may cancel anytime; access continues until the end of the billing period. Refunds are issued only for documented technical failures on our part, reviewed within 5 business days.",
          },
          {
            title: "5. Intellectual Property",
            body: "You retain all rights to your uploaded documents. DocuMindAI retains rights to the platform, UI, models, and brand. You grant DocuMindAI a limited license to process your documents solely to provide the service.",
          },
          {
            title: "6. Prohibited Conduct",
            body: "You may not: attempt to reverse-engineer or extract the underlying AI models; scrape or automate queries at scale; share account credentials; or use the service to process classified government documents without authorization.",
          },
          {
            title: "7. Limitation of Liability",
            body: "DocuMindAI's liability is limited to the amount paid in the 3 months prior to any claim. We are not liable for indirect, incidental, or consequential damages including data loss or business interruption.",
          },
          {
            title: "8. Governing Law",
            body: "These Terms are governed by the laws of India. Disputes shall be resolved in the courts of Mumbai, Maharashtra.",
          },
          {
            title: "9. Contact",
            body: "Questions about these Terms? Email legal@documindai.com.",
          },
        ].map(({ title, body }) => (
          <section key={title} style={{ marginBottom: "36px" }}>
            <h2 style={{ fontSize: "var(--text-xl)", fontWeight: "var(--weight-semibold)", marginBottom: "12px" }}>{title}</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: "var(--leading-relaxed)", fontSize: "var(--text-base)" }}>{body}</p>
          </section>
        ))}

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "32px", display: "flex", gap: "24px" }}>
          <Link href="/privacy" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)" }}>Privacy Policy</Link>
          <Link href="/" style={{ color: "var(--text-tertiary)", textDecoration: "none", fontSize: "var(--text-sm)" }}>Home</Link>
        </div>
      </div>
    </div>
  );
}
