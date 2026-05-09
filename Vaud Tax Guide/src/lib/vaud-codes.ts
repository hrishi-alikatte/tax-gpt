// Maps canonical extraction fields to VaudTax form codes + EN labels.
export interface VaudCodeEntry {
  code: string;
  label: string;
  group: "Income" | "Deductions" | "Assets" | "Other";
}

export const VAUD_CODES: Record<string, VaudCodeEntry> = {
  "salary.gross_annual_chf": { code: "100", label: "Gross salary", group: "Income" },
  "salary.net_annual_chf": { code: "100", label: "Net salary", group: "Income" },
  "secondary_income.chf": { code: "140", label: "Secondary income", group: "Income" },
  "pillar_3a.contribution_chf": { code: "310", label: "Pillar 3a contribution", group: "Deductions" },
  "pillar_2.buyback_chf": { code: "311", label: "2nd Pillar (LPP) buy-back", group: "Deductions" },
  "health_insurance.premium_chf": { code: "300", label: "Health insurance premium", group: "Deductions" },
  "transport.commute_chf": { code: "330", label: "Commute / transport costs", group: "Deductions" },
  "meal_allowance.method": { code: "325", label: "Meal allowance method", group: "Deductions" },
  "bank.interest_chf": { code: "410", label: "Bank interest income", group: "Income" },
  "bank.balance_chf": { code: "420", label: "Bank account balance", group: "Assets" },
  "foreign_assets.value_chf": { code: "440", label: "Foreign assets", group: "Assets" },
  "real_estate.value_chf": { code: "430", label: "Real estate value", group: "Assets" },
  "donations.chf": { code: "380", label: "Charitable donations", group: "Deductions" },
};

export function lookupCode(canonical: string): VaudCodeEntry {
  return (
    VAUD_CODES[canonical] ?? {
      code: "—",
      label: canonical
        .split(".")
        .pop()!
        .replace(/_/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase()),
      group: "Other",
    }
  );
}

export function formatFactValue(canonical: string, value: number | string | boolean): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") {
    return new Intl.NumberFormat("fr-CH", { maximumFractionDigits: 2 }).format(value) + " CHF";
  }
  // ISO date heuristic
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
    const [y, m, d] = value.slice(0, 10).split("-");
    return `${d}.${m}.${y}`;
  }
  return value;
}