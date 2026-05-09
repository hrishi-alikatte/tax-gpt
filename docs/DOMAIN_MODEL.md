# VaudTaxAI — Domain Model (DRAFT)

> Canonical Vaud tax schema for **employed C-permit residents in Canton Vaud**, with English ↔ French ↔ VaudTax-code mapping and the open-questions log.
>
> **DRAFT** — every entry must be validated against `TaxAI2025/Instructions_generales_2024.pdf` by `vaud-tax-domain-analyst` before being marked `vaud_official`. Page references with `?` are unverified.

---

## 1. Scope (hard fence)

- **Canton:** Vaud only.
- **Permit:** C only (settled residents).
- **Employment:** salaried employees only. No self-employed, no contractors, no business owners.
- **Residence:** Vaud-resident the full tax year.
- **Tax year (MVP):** 2024.
- **Filing system:** VaudTax.

Any concept outside this fence is **out of scope** — flag and stop.

---

## 2. Canonical user profile

| Canonical field          | Type                                | Required | Notes                                         |
| ------------------------ | ----------------------------------- | -------- | --------------------------------------------- |
| `first_name`             | str                                 | yes      | UI only                                       |
| `permit_type`            | Literal["C"]                        | yes      | Hard-pinned to C for MVP                      |
| `marital_status`         | Literal["single","married","divorced","widowed","registered_partnership"] | yes |  |
| `spouse_works`           | bool \| None                        | if married |                                          |
| `children_count`         | int                                 | yes      |                                               |
| `children_ages`          | list[int]                           | if `children_count > 0` |                                |
| `commune_of_residence`   | str                                 | yes      | must be in Vaud                               |
| `employer_name`          | str \| None                         | yes      |                                               |
| `work_commune`           | str \| None                         | yes      | drives commute deduction rule                 |
| `tax_year`               | int                                 | yes      | 2024 for MVP                                  |

---

## 3. Canonical document types (MVP)

| `DocumentType`               | English label                | French label                  | Primary fields extracted                                            |
| ---------------------------- | ---------------------------- | ----------------------------- | ------------------------------------------------------------------- |
| `salary_certificate`         | Salary certificate           | Certificat de salaire         | gross salary, net salary, social contributions, employer, period    |
| `health_insurance_premium`   | Health insurance premium     | Prime d'assurance maladie     | annual premium, insurer, insured persons                            |
| `daycare_invoice`            | Daycare / childcare invoice  | Facture de garde / crèche     | total paid, provider, child, period                                 |
| `pillar_3a_certificate`      | Pillar 3a certificate        | Attestation 3e pilier A       | annual contribution, institution, account                           |
| `transport_pass`             | Public transport subscription| Abonnement de transport       | annual cost, route                                                  |
| `bank_year_end_statement`    | Bank year-end statement      | Relevé bancaire de fin d'année| account balance 31-Dec, interest income                             |

---

## 4. Canonical tax facts (subset — MVP)

| `canonical_field`                    | Type    | English label                       | French label                          | VaudTax code (verify) |
| ------------------------------------ | ------- | ----------------------------------- | ------------------------------------- | --------------------- |
| `salary.gross_annual_chf`            | Decimal | Gross annual salary                 | Salaire brut annuel                   | Code 100 (?)          |
| `salary.net_annual_chf`              | Decimal | Net annual salary                   | Salaire net annuel                    | —                     |
| `salary.ahv_iv_eo_chf`               | Decimal | AHV/IV/EO contributions             | Cotisations AVS/AI/APG                | —                     |
| `salary.unemployment_chf`            | Decimal | Unemployment insurance              | Assurance chômage                     | —                     |
| `salary.pension_2nd_pillar_chf`      | Decimal | 2nd pillar contributions            | Cotisations LPP                       | —                     |
| `health_insurance.annual_premium_chf`| Decimal | Health insurance premium (annual)   | Prime d'assurance maladie (annuelle)  | Code 320 (?)          |
| `childcare.total_paid_chf`           | Decimal | Childcare expenses                  | Frais de garde des enfants            | Code 350 (?)          |
| `pillar_3a.annual_contribution_chf`  | Decimal | Pillar 3a contribution              | Cotisation 3e pilier A                | Code 380 (?)          |
| `transport.annual_cost_chf`          | Decimal | Commute / transport cost            | Frais de transport                    | Code 140 (?)          |
| `meal_allowance.method`              | Literal["canteen","none"]| Meal allowance method  | Frais de repas                        | Code 150 (?)          |
| `bank.year_end_balance_chf`          | Decimal | Bank balance 31 December            | Solde bancaire au 31 décembre         | Code 800 (?)          |
| `bank.annual_interest_chf`           | Decimal | Interest income                     | Intérêts perçus                       | Code 810 (?)          |

> All `(?)` codes are **unverified guesses** — `vaud-tax-domain-analyst` must validate against the official Vaud Instructions before any rule cites them.

---

## 5. Required user confirmations

For every `TaxFact` rendered to the user, the **extracted-values view** must show:

- `value` (formatted, with currency)
- `source_doc` (filename) + `source_page`
- `confidence` badge (high / medium / low / unknown)
- "Confirm" checkbox (default unchecked)

The "Continue" button on the extracted-values screen is **disabled** until every required `TaxFact` has `confirmed_by_user == True`.

---

## 6. Active completeness rules (initial set)

Each rule lives in `completeness/rules.py` and must carry a real Vaud Instructions citation. Page numbers below are **placeholders** until the domain analyst confirms.

| Rule id              | Triggers when                                                                    | Asks for                          | Source (verify)             | Severity        |
| -------------------- | -------------------------------------------------------------------------------- | --------------------------------- | --------------------------- | --------------- |
| `VD-CHILDCARE-001`   | `children_count > 0` AND no `childcare.total_paid_chf` fact                      | childcare invoices                | Vaud Instr. 2024 p. ??      | likely_missing  |
| `VD-PILLAR3A-001`    | `employer_name != None` AND no `pillar_3a.annual_contribution_chf` fact          | pillar 3a annual statement        | Vaud Instr. 2024 p. ??      | likely_missing  |
| `VD-COMMUTE-001`     | `commune_of_residence != work_commune` AND no `transport.annual_cost_chf` fact   | transport pass / commute proof    | Vaud Instr. 2024 p. ??      | likely_missing  |
| `VD-MEAL-001`        | `employer_name != None` AND no `meal_allowance.method` fact                      | meals method (canteen / none)     | Vaud Instr. 2024 p. ??      | nice_to_have    |
| `VD-INSURANCE-001`   | No `health_insurance.annual_premium_chf` fact                                    | health insurance year statement   | Vaud Instr. 2024 p. ??      | blocker         |
| `VD-BANK-001`        | No `bank.year_end_balance_chf` fact                                              | bank year-end statement           | Vaud Instr. 2024 p. ??      | blocker         |

A rule cannot be merged into the active set without:

1. A real source citation (page + section).
2. A golden test (positive + negative profile).
3. An entry in this table.

---

## 7. Open questions (must resolve before claiming "official")

### Tax-year scope (now 2025)

- [ ] Verify VaudTax field codes for every entry in §4. Current values are guesses.
- [ ] Verify exact page references for every rule in §6 against `vd_2025.pdf`.
- [ ] Childcare deduction cap for 2025 — does Vaud follow Federal cap or have its own?
- [ ] Transport deduction: kilometric vs actual public-transport-only — what does Vaud accept for 2025?
- [ ] Meal allowance default rate — confirm against Vaud 2025 Instructions.
- [ ] Pillar 3a employed cap 2025 — Federal value — verify.
- [ ] Treatment of foreign bank accounts for C-permit residents — likely full disclosure required, confirm wording.
- [ ] Health insurance deduction: actual paid vs forfait — confirm Vaud 2025 rule.
- [ ] Where Vaud is silent, identify Federal AFC source(s) and add them to the corpus.

### Citation token format (pinned 2026-05-09 — see `vaud-tax-domain-analyst` review)

- **Pinned format:** `[Vaud 2025 Instructions p.N]` (PDF page, 1-indexed = `pypdf.PdfReader.pages[i]` index + 1) and `[Vaud 2025 Instructions, page pending verification]` for unknown pages.
- **Deferred:** `§X.Y` section refs in the LLM-emitted token (chunks straddle sections; risk of hallucinated section numbers). Render `RagCitation.section_title` in the UI alongside the token instead.
- **Multi-citation:** keep separate tokens per chunk (1 token = 1 chunk for audit trail).
- [ ] Confirm PDF page vs printed page offset in `vd_2025.pdf` (cover + TOC count).
- [ ] Confirm exact French title string for UI footer (`Instructions générales sur la déclaration d'impôt 2025` vs shorter form).
- [ ] Decide whether `printed_page` is reliably extractable from `vd_2025.pdf` headers/footers; if not, drop `printed_page` field rather than leaving it always-None.
- [ ] Section-numbering scheme used by 2025 edition (numeric `4.3` vs `Ch. IV §3`) — defer §-token until confirmed.
- [ ] Should refusal-by-intent log to audit even when no retrieval occurs? (Currently `retrieval=None`.)
- [ ] Multi-source future: when Federal AFC is added, label collision (`Federal 2025 Instructions p.N`) — pick label namespace now to keep regex extensible.

---

## 8. Concept ownership

- New concepts → propose via `vaud-tax-domain-analyst`.
- New rules → propose via `vaud-tax-domain-analyst`, implemented by `completeness-engine-designer`.
- Schema changes → `TaxFact` and `UserProfile` are frozen after M2 (see `ROADMAP.md`).
- This file is the canonical source. PRs that change a code, label, or rule must update this file.
