// Single source of truth for pricing. Every surface — marketing landing,
// /pricing, /billing, UpgradeModal, Account — renders from this file.
//
// W1 (deep-debug session 4): three simple monthly tiers, ChatGPT-style.
// No annual/monthly toggle — the user explicitly asked for simpler.

export type PlanId = "go" | "plus" | "pro";

export interface Plan {
  id: PlanId;
  /** Display name — "Go" / "Plus" / "Pro" */
  name: string;
  /** Monthly price in rupees, integer */
  price: number;
  /** One-line ChatGPT-style description shown under the price */
  tagline: string;
  /** Bullet-list of capabilities */
  features: string[];
  /** Whether this card should be visually emphasised */
  featured?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: "go",
    name: "Go",
    price: 799,
    tagline: "Keep working with expanded access",
    features: [
      "200 queries per month",
      "All 7 workspaces",
      "Page-cited answers",
      "Trust scores on every reply",
      "Uploads up to 200 MB",
    ],
  },
  {
    id: "plus",
    name: "Plus",
    price: 999,
    tagline: "Unlock the full experience",
    features: [
      "Unlimited queries",
      "All 7 workspaces",
      "Priority processing",
      "PDF & DOCX audit reports",
      "Session export (PDF, DOCX)",
      "UPI & card payments",
    ],
    featured: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: 2999,
    tagline: "Maximize your output",
    features: [
      "Everything in Plus",
      "Multi-user access",
      "Email report delivery",
      "API access",
      "SLA + priority support",
    ],
  },
];

// Indian number formatting (lakhs/crores grouping)
const INR = new Intl.NumberFormat("en-IN");
export const fmtINR = (n: number): string => `₹${INR.format(n)}`;

// Lookup helpers — keep callers from indexing PLANS by position.
export const planById = (id: PlanId): Plan =>
  PLANS.find((p) => p.id === id) ?? PLANS[0];

// Backwards-compatibility re-exports for surfaces not yet migrated.
// New code should import PLANS / planById instead.
export const PRO_MONTHLY_PRICE = planById("plus").price;        // 999
export const PRO_ANNUAL_MONTHLY_PRICE = planById("go").price;   // 799
export const ENTERPRISE_MONTHLY_PRICE = planById("pro").price;  // 2999
export const PRO_ANNUAL_TOTAL = PRO_ANNUAL_MONTHLY_PRICE * 12;
export const PRO_ANNUAL_SAVINGS_PER_YEAR =
  (PRO_MONTHLY_PRICE - PRO_ANNUAL_MONTHLY_PRICE) * 12;
export const PRO_ANNUAL_LABEL = `${fmtINR(PRO_ANNUAL_MONTHLY_PRICE)}/mo`;
export const PRO_MONTHLY_LABEL = `${fmtINR(PRO_MONTHLY_PRICE)}/mo`;
export const PRO_ANNUAL_TOTAL_LABEL =
  `${fmtINR(PRO_ANNUAL_MONTHLY_PRICE)}/mo · ${fmtINR(PRO_ANNUAL_TOTAL)}/year`;
export const PRO_ANNUAL_SAVINGS_LABEL =
  `Saves ${fmtINR(PRO_ANNUAL_SAVINGS_PER_YEAR)}/year vs Plus`;
