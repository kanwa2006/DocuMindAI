// Single source of truth for pricing — every surface (marketing /pricing,
// /billing, UpgradeModal, landing page) renders from here. Don't hardcode
// rupee amounts anywhere else.

export const PRO_MONTHLY_PRICE = 999;      // ₹ / month, billed monthly
export const PRO_ANNUAL_MONTHLY_PRICE = 799; // ₹ / month when billed annually
export const ENTERPRISE_MONTHLY_PRICE = 2999;

export const PRO_ANNUAL_TOTAL = PRO_ANNUAL_MONTHLY_PRICE * 12;          // 9,588
export const PRO_ANNUAL_SAVINGS_PER_YEAR =
  (PRO_MONTHLY_PRICE - PRO_ANNUAL_MONTHLY_PRICE) * 12;                  // 2,400

// Indian number formatting (lakhs/crores grouping)
const INR = new Intl.NumberFormat("en-IN");
export const fmtINR = (n: number): string => `₹${INR.format(n)}`;

// Common copy fragments — used across surfaces so wording stays identical
export const PRO_ANNUAL_LABEL = `${fmtINR(PRO_ANNUAL_MONTHLY_PRICE)}/mo billed annually`;
export const PRO_MONTHLY_LABEL = `${fmtINR(PRO_MONTHLY_PRICE)}/mo billed monthly`;
export const PRO_ANNUAL_TOTAL_LABEL =
  `${fmtINR(PRO_ANNUAL_MONTHLY_PRICE)}/mo billed annually = ${fmtINR(PRO_ANNUAL_TOTAL)}/year`;
export const PRO_ANNUAL_SAVINGS_LABEL =
  `Saves ${fmtINR(PRO_ANNUAL_SAVINGS_PER_YEAR)}/year`;
