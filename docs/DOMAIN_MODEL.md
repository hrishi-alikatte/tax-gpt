# VaudTaxAI — Domain Model (DRAFT)

> Canonical Vaud tax schema for **employed C-permit residents in Canton Vaud**, with English ↔ French ↔ VaudTax-code mapping and the open-questions log.
>
> **DRAFT** — every entry must be validated against `TaxAI2025/Instructions_generales_2025.pdf` by `vaud-tax-domain-analyst` before being marked `vaud_official`. Page references with `?` are unverified.

---

## 1. Scope (hard fence)

- **Canton:** Vaud only.
- **Permit:** C only (settled residents).
- **Employment:** salaried employees only. No self-employed, no contractors, no business owners.
- **Residence:** Vaud-resident the full tax year.
- **Tax year (MVP):** 2025.
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
| `tax_year`               | int                                 | yes      | 2025 for MVP                                  |
| `has_workplace_canteen`  | bool \| None                        | optional | short-circuits `VD-MEAL-001` when `True`. Added M4 to keep the demo-spec finding count at three (Sarah is `True`). |

---

## 3. Canonical document types

| `DocumentType`               | English label                | French label                  | Primary fields extracted                                            |
| ---------------------------- | ---------------------------- | ----------------------------- | ------------------------------------------------------------------- |
| `salary_certificate`         | Salary certificate           | Certificat de salaire         | gross salary, net salary, social contributions, employer, period    |
| `health_insurance_premium`   | Health insurance premium     | Prime d'assurance maladie     | annual premium, insurer, insured persons                            |
| `daycare_invoice`            | Daycare / childcare invoice  | Facture de garde / crèche     | total paid, provider, child, period                                 |
| `pillar_3a_certificate`      | Pillar 3a certificate        | Attestation 3e pilier A       | annual contribution, institution, account                           |
| `transport_pass`             | Public transport subscription| Abonnement de transport       | annual cost, route                                                  |
| `bank_year_end_statement`    | Bank year-end statement      | Relevé bancaire de fin d'année| account balance 31-Dec, interest income                             |
| `mortgage_interest_statement`| Mortgage interest statement  | Attestation d'intérêts hypothécaires | annual mortgage interest                                      |
| `alimony_paid_received`      | Alimony statement            | Pension alimentaire / contribution d'entretien | alimony paid                                      |
| `donation_receipt`           | Donation receipt             | Attestation de don            | total donations paid                                                |
| `parental_support_receipt`   | Parental support receipt     | Aide aux parents / personne à charge | support paid                                                  |
| `medical_bills_unreimbursed` | Unreimbursed medical bills   | Frais médicaux non remboursés | unreimbursed medical/dental costs                                   |
| `education_invoice`          | Education invoice            | Frais de formation / perfectionnement | tuition/training paid                                        |
| `second_pillar_buyback_attestation` | Second-pillar buyback attestation | Attestation de rachat LPP | second-pillar buyback paid                                  |
| `foreign_income_attestation` | Foreign income attestation   | Attestation de revenu étranger | gross foreign income                                               |
| `disability_proof`           | Disability proof             | Attestation invalidité / rente AI | disability acknowledgement                                      |
| `unemployment_benefits_attestation` | Unemployment benefits attestation | Attestation chômage | unemployment benefits received                                  |

---

## 4. Canonical tax facts (subset — MVP)

Verified against `data/official/vd_2025.pdf` by `vaud-tax-domain-analyst`
(2026-05-09). `(?)` retained only where retrieval did not surface a CODE
heading on the rule's home page — see §7 open questions.

| `canonical_field`                    | Type    | English label                       | French label                          | VaudTax code |
| ------------------------------------ | ------- | ----------------------------------- | ------------------------------------- | ------------ |
| `salary.gross_annual_chf`            | Decimal | Gross annual salary                 | Salaire brut annuel                   | — (salary-certificate line; not a separate VaudTax field) |
| `salary.net_annual_chf`              | Decimal | Net annual salary                   | Salaire net annuel                    | **Code 100** [verified vd_2025 p.31] |
| `salary.ahv_iv_eo_chf`               | Decimal | AHV/IV/EO contributions             | Cotisations AVS/AI/APG                | — (already netted into Code 100) |
| `salary.unemployment_chf`            | Decimal | Unemployment insurance              | Assurance chômage                     | — (already netted into Code 100) |
| `salary.pension_2nd_pillar_chf`      | Decimal | 2nd pillar contributions            | Cotisations LPP                       | — (already netted into Code 100); **Code 320** = 2nd-pillar **buyback** only (RACHATS D'ANNÉES D'ASSURANCE) [verified p.31] |
| `health_insurance.annual_premium_chf`| Decimal | Health insurance premium (annual)   | Prime d'assurance maladie (annuelle)  | **Code 300** [verified vd_2025 p.29] |
| `childcare.total_paid_chf`           | Decimal | Childcare expenses                  | Frais de garde des enfants            | **Code 670** [verified vd_2025 p.44: "DÉDUCTION POUR FRAIS DE GARDE CODE 670" — max CHF 15'200/child <14] |
| `pillar_3a.annual_contribution_chf`  | Decimal | Pillar 3a contribution              | Cotisation 3e pilier A                | **Code 310** [verified vd_2025 p.30: "PRÉVOYANCE INDIVIDUELLE LIÉE 3 EME PILIER A (OPP3) CODE 310"] |
| `transport.annual_cost_chf`          | Decimal | Commute / transport cost            | Frais de transport                    | **Code 140** [verified vd_2025 p.18: "FRAIS DE TRANSPORT DU DOMICILE AU LIEU DE TRAVAIL CODE 140"] |
| `meal_allowance.method`              | Literal["canteen","none"]| Meal allowance method  | Frais de repas                        | **Code 150** [verified vd_2025 p.21, p.22] |
| `bank.year_end_balance_chf`          | Decimal | Bank balance 31 December            | Solde bancaire au 31 décembre         | **Code 410** [verified vd_2025 p.32; previous guess Code 800 was wrong — Code 800 = REVENU IMPOSABLE per p.51] |
| `bank.annual_interest_chf`           | Decimal | Interest income                     | Intérêts perçus                       | **Code 410** [verified vd_2025 p.32: "REVENU ET FORTUNE DE TITRES"; previous guess Code 810 was wrong — Code 810 = family situation per p.47] |
| `mortgage.annual_interest_chf`       | Decimal | Mortgage interest                   | Intérêts hypothécaires                | **Code 480** [verified vd_2025 p.40: "DÉDUCTION DES INTÉRÊTS DE CAPITAUX D'ÉPARGNE CODE 480"] |
| `alimony.paid_chf`                   | Decimal | Alimony paid                        | Pension alimentaire versée            | **Code 630** [verified vd_2025 p.42: "PENSIONS ALIMENTAIRES VERSÉES CODE 630"] |
| `donations.total_chf`                | Decimal | Donations paid                      | Dons / versements                     | **Code 720** [verified vd_2025 p.49: "DONS À DES INSTITUTIONS D'UTILITÉ PUBLIQUE CODE 720"; previous Phase B preview guess Code 620 was wrong for general donations] |
| `parental_support.paid_chf`          | Decimal | Support paid to parents/dependents  | Personne à charge / aide aux parents  | **Code 680** [verified vd_2025 p.45: "DÉDUCTION POUR PERSONNE À CHARGE CODE 680"] |
| `medical.unreimbursed_chf`           | Decimal | Unreimbursed medical costs          | Frais médicaux non remboursés         | **Code 710** [verified vd_2025 p.48: "FRAIS MÉDICAUX ET DENTAIRES CODE 710"] |
| `education.tuition_paid_chf`         | Decimal | Education / training fees paid      | Frais de formation / perfectionnement | **Code 618** [verified vd_2025 p.42: "FRAIS DE FORMATION, DE PERFECTIONNEMENT ET DE RECONVERSION CODE 618"] |
| `pillar2.buyback_chf`                | Decimal | Second-pillar buyback               | Rachat d'années d'assurance LPP       | **Code 320** [verified vd_2025 p.31] |
| `real_estate.maintenance_chf`        | Decimal | Real-estate maintenance costs       | Frais d'entretien d'immeubles         | **Code 540** [verified vd_2025 p.40: "FRAIS D'ENTRETIEN D'IMMEUBLES CODE 540"; details refer to the Vaud property instructions] |
| `foreign_income.gross_chf`           | Decimal | Gross foreign income                | Revenu étranger brut                  | **Code 100** [verified vd_2025 p.17: foreign salary declared under same Code 100 as Swiss salary; foreign income attestation required for documentation] |
| `disability.acknowledged`            | Boolean | Disability proof acknowledged       | Attestation invalidité / rente AI     | Related to **Code 200/250** [p.10-11: disability pensions declared under loss-of-gain or pension sections; disability-related medical costs under Code 710] |
| `unemployment.benefits_chf`          | Decimal | Unemployment benefits               | Indemnités de chômage                 | **Code 200** [verified vd_2025 p.26: "ASSURANCE-CHOMAGE, SERVICE MILITAIRE (AC + APG) CODE 200" for direct AC benefits; employer-paid RHT benefits under Code 100]

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

Each rule lives in `TaxAI2025/completeness/rules.py` and ships with a
`verification_status` discriminator on `CompletenessRule`. The values:

- `vaud_official` — `pdf_page` confirmed by `vaud-tax-domain-analyst`
  against `data/official/vd_2025.pdf` and a chunk-level citation can be
  produced from the live RAG index.
- `pending` — rule is implemented and golden-tested, but the Vaud 2025
  Instructions page has not yet been pinned. The UI renders
  `[Vaud 2025 Instructions, page pending verification]`.
- `inferred` — reserved for federal-fallback or non-Vaud rules; must
  carry a §7 open-questions entry. Currently unused.

**User-facing rule policy (Phase B hardening):** the Completeness screen and
default `evaluate()` path show only `vaud_official` rules. `pending` and
`inferred` checks belong in the Adaptive Interview as proactive questions until
their sources and trigger logic are verified. Tests may call
`evaluate(..., include_unverified=True)` to keep the pending registry auditable.

All six initial rules pinned 2026-05-09 by `vaud-tax-domain-analyst`
against `data/official/vd_2025.pdf`.

| Rule id              | Triggers when                                                                                  | Asks for                          | Severity        | `verification_status` | `pdf_page` |
| -------------------- | ---------------------------------------------------------------------------------------------- | --------------------------------- | --------------- | --------------------- | ---------- |
| `VD-CHILDCARE-001`   | `children_count > 0` AND no confirmed `childcare.total_paid_chf` fact                          | childcare invoices                | likely_missing  | vaud_official         | 44         |
| `VD-PILLAR3A-001`    | `employer_name` non-empty AND no confirmed `pillar_3a.annual_contribution_chf` fact            | pillar 3a annual statement        | likely_missing  | vaud_official         | 31         |
| `VD-COMMUTE-001`     | `commune_of_residence != work_commune` (both set) AND no confirmed `transport.annual_cost_chf` | transport pass / commute proof    | likely_missing  | vaud_official         | 20         |
| `VD-MEAL-001`        | `employer_name` non-empty AND `has_workplace_canteen != True` AND no confirmed `meal_allowance.method` | meals method (canteen / none) | nice_to_have    | vaud_official         | 21         |
| `VD-INSURANCE-001`   | No confirmed `health_insurance.annual_premium_chf` fact                                        | health insurance year statement   | blocker         | vaud_official         | 29         |
| `VD-BANK-001`        | No confirmed `bank.year_end_balance_chf` fact                                                  | bank year-end statement           | blocker         | vaud_official         | 32         |

> **Engine confirmation gate**: `evaluate()` filters facts to
> `confirmed_by_user is True` before any rule runs. A fact extracted by
> the LLM but not yet ticked by the user is invisible to the engine —
> see `CLAUDE.md` §5 ("Downstream code must refuse unconfirmed values")
> and `tests/test_completeness_engine.py::test_evaluate_filters_unconfirmed_facts_before_rules_run`.

A rule cannot be promoted from `pending` to `vaud_official` without:

1. A confirmed Vaud 2025 Instructions PDF page (1-indexed).
2. A golden test (positive + negative profile) — already in place for the six initial rules.
3. An entry in this table reflecting the new `verification_status` and `pdf_page`.

---

## 7. Open questions (must resolve before claiming "official")

### Tax-year scope (now 2025)

- [x] ~~Verify exact PDF page references for every rule in §6.~~ Done 2026-05-09 — all six pinned (44 / 31 / 20 / 21 / 29 / 32).
- [x] ~~Verify VaudTax field codes for every entry in §4.~~ Done 2026-05-09 — Code 100 (net salary, p.31), Code 140 (transport, p.18), Code 150 (meals, p.21-22), Code 300 (insurance, p.29), Code 310 (3a contribution, p.30), Code 320 (2nd-pillar buyback only, p.31), Code 410 (bank/securities, p.32), Code 670 (childcare, p.44). Three previous guesses were **wrong** and have been corrected (Code 320 → 300, Code 800 → 410, Code 810 → 410). Three previously-open guesses were resolved by direct PDF read (Code 350 → 670 childcare, Code 380 → 310 pillar 3a, Code 140 confirmed transport).
- [x] ~~**VaudTax code for childcare**~~ Resolved 2026-05-09 → **Code 670** (vd_2025 p.44).
- [x] ~~**VaudTax code for pillar 3a contribution**~~ Resolved 2026-05-09 → **Code 310** (vd_2025 p.30: PRÉVOYANCE INDIVIDUELLE LIÉE 3 EME PILIER A (OPP3) CODE 310).
- [x] ~~**VaudTax code for transport / commute**~~ Resolved 2026-05-09 → **Code 140** (vd_2025 p.18).
- [x] ~~**Phase B first source-verification batch**~~ Done 2026-05-09 → Code 320 (2nd-pillar buyback, p.31), Code 540 (real-estate maintenance, p.40), Code 618 (formation/perfectionnement, p.42), Code 630 (alimony paid, p.42), Code 720 (eligible public-interest donations, p.49). These concepts are source-verified for Interview prompts; broad Completeness checks remain `pending` until their triggers are specific enough to be user-facing findings.
- [x] ~~**Phase 2 verification batch (2026-05-13)**~~ Done 2026-05-13 → Code 480 (mortgage/capital interest deduction, p.40), Code 680 (dependent-person social deduction, p.45), Code 710 (medical/dental costs, p.48), Code 200 (loss-of-gain/indemnities AC/APG, p.26-27), Code 100 (foreign salary declared same as Swiss, p.17). Five previously-pending codes now verified; corresponding completeness rules promoted to `vaud_official`.
- [ ] **Dependent-support / person-in-need source split** — Vaud p.65 lists a social deduction for a person in need, but the exact canonical fact, code, eligibility wording, and whether this should model support paid or household/dependent status still need a dedicated source pass before promotion. Partially resolved: Code 680 covers dependent-person deduction (p.45); Code 630 covers alimony paid (p.42). Gap: direct household support to parents not in same household.
- [ ] **Phase B Vaud codes (remaining preview)** harvested in the same PDF read for the planned interview-question registry: Code 105 (secondary activity), 110 (non-employer allowances), 120 (company directors), 165 (secondary activity flat-rate), 195 (other revenues), 250 (2nd pillar pensions), 270 (annuity contracts), 330 (self-employed pension contributions), 620 (party payments / charges durables), 640 (AVS/AI/APG/AC for non-active), 650 (rent/rental value), 660 (social housing), 695 (modest-taxpayer deduction), 725 (family deduction), 800 (taxable income), 810 (family situation parts). All to be cited in the Phase B interview registry — verification pass per code still required before each entry ships.
- [ ] **Confirm pillar 3a married-couple cap CHF 9'900 attribution** — the figure surfaced on p.30 in the pillar 3a query but the textual context sits inside the CODE 300 insurance section. Risk: cap is for insurance-premium deduction, not pillar 3a. Resolve before any rule cites this figure.
- [ ] Childcare deduction cap for 2025 — does Vaud follow Federal cap or have its own?
- [ ] Transport deduction: kilometric vs actual public-transport-only — what does Vaud accept for 2025?
- [ ] Meal allowance default rate — confirm against Vaud 2025 Instructions.
- [ ] Pillar 3a employed cap 2025 — Federal value — verify.
- [ ] Treatment of foreign bank accounts for C-permit residents — likely full disclosure required, confirm wording.
- [ ] Health insurance deduction: actual paid vs forfait — confirm Vaud 2025 rule (p.29-30 shows the family-status cap interplay with subsides; not yet modelled).
- [ ] Where Vaud is silent, identify Federal AFC source(s) and add them to the corpus.
- [ ] **Code 235 mis-classification risk** — anyone reading the pillar 3a retrieval out of context could conflate code 235 (double activity) with pillar 3a. Note added to §4 row.

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
