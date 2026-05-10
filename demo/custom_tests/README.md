# Demo PDFs — `expat_c_permit_basic` scenario

Synthetic Vaud documents for the **Sarah Müller** scenario. Used to
walk through Stages 1-6 of the live UI at https://tax-gpt.online.

PDFs are **not committed** (gitignored). Regenerate any time:

```bash
python scripts/generate_custom_pdfs.py
```

## Stage 1 — Profile values to type into the form

| Field | Value |
|---|---|
| First name | `Sarah` |
| Permit type | `C` |
| Marital status | `Married` |
| Spouse works | `Yes` |
| Children count | `1` |
| Children ages | `4` |
| Commune of residence | `Lausanne` |
| Employer name | `Aurelius SA` |
| Work commune | `Renens` |
| Tax year | `2025` |
| Has workplace canteen | `Yes` |

These mirror [demo/scenarios/expat_c_permit_basic/profile.json](../scenarios/expat_c_permit_basic/profile.json).

## Stage 2 — Documents to upload

Drop all 8 PDFs from this folder onto the upload zone. Each file maps
1:1 to a classifier `doc_type` and produces the canonical facts below.

| File | Classifies as | Facts produced |
|---|---|---|
| `01_certificat_salaire.pdf` | `salary_certificate` | `salary.gross_annual_chf=110000`, `salary.net_annual_chf=92000` |
| `02_prime_assurance_maladie.pdf` | `health_insurance_premium` | `health_insurance.annual_premium_chf=4200` |
| `03_pilier_3a.pdf` | `pillar_3a_certificate` | `pillar_3a.annual_contribution_chf=7056` |
| `04_garderie.pdf` | `daycare_invoice` | `childcare.total_paid_chf=14400` |
| `05_releve_bcv.pdf` | `bank_year_end_statement` | `bank.year_end_balance_chf=18400`, `bank.annual_interest_chf=12` |
| `06_abonnement_cff.pdf` | `transport_pass` | `transport.annual_cost_chf=1140` |
| `07_attestation-don.pdf` | `donation_receipt` | `donations.total_chf=600` |
| `08_facture_medical.pdf` | `medical_bills_unreimbursed` | `medical.unreimbursed_chf=1250` |

## Expected behaviour per stage

- **Stage 3 — Review extracted facts.** Each row shows "Ready" with a
  `N facts extracted` counter > 0 (medical may show 0 on some local
  builds — known classifier weakness, doesn't break the demo). Click
  **Confirm all** on each card.
- **Stage 4 — Interview.** With this full bundle uploaded, the engine
  has no blockers and at most 1 nice-to-have question (workplace
  canteen = Yes short-circuits the meal-allowance question).
- **Stage 5 — Completeness dashboard.** Three columns render:
  - `Missing` — empty.
  - `Likely missing` — empty (everything required is present).
  - `Complete` — empty too (the engine emits `Finding`s only for
    rules that **trigger**, not for rules that pass cleanly; a future
    iteration can populate the third column).
- **Stage 6 — Copilot.** Ask "What is Pillar 3a in VaudTax?" and
  expect an answer with a citation token like
  `[Vaud 2025 Instructions p.30]`.

## Caveats

- All amounts are synthetic. No real bank accounts, IBANs, or
  insurance policy numbers.
- Headings are bilingual French/German because the classifier's
  keyword heuristics target the actual official Vaud doc layouts.
- The medical-bills PDF is the most fragile classification; if you
  see "0 facts extracted" you can still proceed — it's a known
  classifier weakness, not a UI bug.
