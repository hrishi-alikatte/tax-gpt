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
| `has_workplace_canteen`  | bool \| None                        | optional | short-circuits `VD-MEAL-001` when `True`. Added M4 to keep the demo-spec finding count at three (Sarah is `True`). |

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

Verified against `data/official/vd_2025.pdf` by `vaud-tax-domain-analyst`
(2026-05-09). `(?)` retained only where retrieval did not surface a CODE
heading on the rule's home page — see §7 open questions.

| `canonical_field`                    | Type    | English label                       | French label                          | VaudTax code |
| ------------------------------------ | ------- | ----------------------------------- | ------------------------------------- | ------------ |
| `salary.gross_annual_chf`            | Decimal | Gross annual salary                 | Salaire brut annuel                   | — (salary-certificate line; not a separate VaudTax field) |
| `salary.net_annual_chf`              | Decimal | Net annual salary                   | Salaire net annuel                    | **Code 100** [verified vd_2025 p.31] |
| `salary.ahv_iv_eo_chf`               | Decimal | AHV/IV/EO contributions             | Cotisations AVS/AI/APG                | — (already netted into Code 100) |
| `salary.unemployment_chf`            | Decimal | Unemployment insurance              | Assurance chômage                     | — (already netted into Code 100) |
| `salary.pension_2nd_pillar_chf`      | Decimal | 2nd pillar contributions            | Cotisations LPP                       | — (already netted into Code 100) |
| `health_insurance.annual_premium_chf`| Decimal | Health insurance premium (annual)   | Prime d'assurance maladie (annuelle)  | **Code 300** [verified vd_2025 p.29] |
| `childcare.total_paid_chf`           | Decimal | Childcare expenses                  | Frais de garde des enfants            | (?) — see §7; rule home p.44 but no CODE heading in the chunk |
| `pillar_3a.annual_contribution_chf`  | Decimal | Pillar 3a contribution              | Cotisation 3e pilier A                | (?) — see §7; rule home p.31 but no CODE heading in the chunk. Code 235 (p.62) is double-activity-spouse, NOT pillar 3a |
| `transport.annual_cost_chf`          | Decimal | Commute / transport cost            | Frais de transport                    | (?) — see §7; rule home p.20 but no CODE heading in the chunk |
| `meal_allowance.method`              | Literal["canteen","none"]| Meal allowance method  | Frais de repas                        | **Code 150** [verified vd_2025 p.21, p.22] |
| `bank.year_end_balance_chf`          | Decimal | Bank balance 31 December            | Solde bancaire au 31 décembre         | **Code 410** [verified vd_2025 p.32; previous guess Code 800 was wrong — Code 800 = REVENU IMPOSABLE per p.51] |
| `bank.annual_interest_chf`           | Decimal | Interest income                     | Intérêts perçus                       | **Code 410** [verified vd_2025 p.32: "REVENU ET FORTUNE DE TITRES"; previous guess Code 810 was wrong — Code 810 = family situation per p.47] |

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
- [x] ~~Verify VaudTax field codes for every entry in §4.~~ Partially done 2026-05-09 — Code 100 (net salary, p.31), Code 150 (meals, p.21-22), Code 300 (insurance, p.29), Code 410 (bank/securities, p.32) verified. Three remain (?) — see new bullets below. Three previous guesses were **wrong** and have been corrected (Code 320 → 300, Code 800 → 410, Code 810 → 410).
- [ ] **VaudTax code for childcare** — retrieval pages 44/45/47/53 did not surface a CODE NNN heading for the childcare deduction. p.47 mentions code 810 (family situation) and code 690 (number of dependent persons) but those are profile codes, not the childcare expense field. Action: targeted retrieval over p.44-46 of vd_2025 looking for "Code 3..." adjacent to "frais de garde".
- [ ] **VaudTax code for pillar 3a contribution** — retrieval pages 30-31 did not surface a CODE NNN for the 3e pilier A line item. Code 235 on p.62 is "déduction double activité conjoints" (double-earner), **not** pillar 3a. Action: targeted retrieval for "3e pilier A code" on p.30-31.
- [ ] **VaudTax code for transport / commute** — retrieval pages 18-20 did not surface a CODE NNN heading. Action: targeted retrieval for "frais de déplacement code" on p.18-20.
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
