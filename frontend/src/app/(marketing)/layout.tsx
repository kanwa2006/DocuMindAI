import type { Metadata } from "next";
import Link from "next/link";
import MarketingNav from "@/components/MarketingNav";

export const metadata: Metadata = {
  title: "DocuMindAI — Document Intelligence for Indian Professionals",
  description:
    "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations. Built for CAs, Lawyers, Teachers & HR professionals in India.",
  keywords: [
    "RAG",
    "document AI",
    "PDF chat",
    "Indian AI tool",
    "document intelligence",
    "CA tool",
    "legal AI India",
  ],
  openGraph: {
    title: "DocuMindAI — Ask Anything About Your Documents",
    description:
      "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations. Built for CAs, Lawyers, Teachers & HR professionals in India.",
    url: "https://documindai.com",
    siteName: "DocuMindAI",
    images: ["/og-image.png"],
    type: "website",
    locale: "en_IN",
  },
  twitter: {
    card: "summary_large_image",
    title: "DocuMindAI",
    description:
      "Ask questions about your PDFs, contracts & notes. Get verified answers with exact page citations.",
  },
  robots: { index: true, follow: true },
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <style>{`
        html { scroll-behavior: smooth; }
        @media (max-width: 480px) {
          .marketing-nav { padding-left: 16px !important; padding-right: 16px !important; }
          .marketing-nav .nav-pricing { display: none; }
        }
      `}</style>

      {/* Client component handles auth-aware nav buttons */}
      <MarketingNav />

      <main id="main">{children}</main>
    </>
  );
}
