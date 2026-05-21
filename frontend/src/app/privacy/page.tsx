import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — DocuMindAI",
  description: "How DocuMindAI collects, uses, and protects your data.",
};

export default function PrivacyPage() {
  return (
    <div style={{ minHeight: "100vh", background: "var(--surface-base)", color: "var(--text-primary)", fontFamily: "var(--font-body)" }}>
      <div style={{ maxWidth: "720px", margin: "0 auto", padding: "64px 24px" }}>
        <Link href="/" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)", display: "inline-flex", alignItems: "center", gap: "4px", marginBottom: "32px" }}>
          ← Back to Home
        </Link>

        <h1 style={{ fontFamily: "var(--font-display)", fontSize: "var(--text-4xl)", fontWeight: "var(--weight-bold)", marginBottom: "8px", lineHeight: "var(--leading-tight)" }}>
          Privacy Policy
        </h1>
        <p style={{ color: "var(--text-tertiary)", fontSize: "var(--text-sm)", marginBottom: "48px" }}>
          Last updated: May 2026
        </p>

        {[
          {
            title: "1. Information We Collect",
            body: "We collect information you provide directly: your name, email address, and document files you upload. We also collect usage data such as query counts and workspace preferences to improve our service. We never store the content of your queries or document answers on third-party servers.",
          },
          {
            title: "2. How We Use Your Information",
            body: "Your uploaded documents are used solely to answer your queries. We use your email to send account notifications, trial reminders, and service updates. You can opt out of marketing emails at any time from your Settings page.",
          },
          {
            title: "3. Document Storage & Security",
            body: "Documents are stored encrypted at rest using AES-256 encryption. Documents are automatically deleted 30 days after your last access. We do not use your documents to train any AI models. Enterprise customers may request immediate deletion at any time.",
          },
          {
            title: "4. Sharing of Information",
            body: "We do not sell your personal information. We share data only with service providers necessary to operate DocuMindAI (such as cloud storage and payment processors), and only under strict data processing agreements.",
          },
          {
            title: "5. Payment Data",
            body: "All payment processing is handled by Razorpay. DocuMindAI never stores your card details or UPI credentials. Payment data is governed by Razorpay's Privacy Policy.",
          },
          {
            title: "6. Your Rights",
            body: "You may request access to, correction of, or deletion of your personal data by emailing support@documindai.com. We will respond within 30 days. You may also export all your data from the Settings page.",
          },
          {
            title: "7. Contact",
            body: "For privacy-related questions, contact us at privacy@documindai.com or write to: DocuMindAI, India.",
          },
        ].map(({ title, body }) => (
          <section key={title} style={{ marginBottom: "36px" }}>
            <h2 style={{ fontSize: "var(--text-xl)", fontWeight: "var(--weight-semibold)", marginBottom: "12px" }}>{title}</h2>
            <p style={{ color: "var(--text-secondary)", lineHeight: "var(--leading-relaxed)", fontSize: "var(--text-base)" }}>{body}</p>
          </section>
        ))}

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "32px", display: "flex", gap: "24px" }}>
          <Link href="/terms" style={{ color: "var(--brand)", textDecoration: "none", fontSize: "var(--text-sm)" }}>Terms of Service</Link>
          <Link href="/" style={{ color: "var(--text-tertiary)", textDecoration: "none", fontSize: "var(--text-sm)" }}>Home</Link>
        </div>
      </div>
    </div>
  );
}
