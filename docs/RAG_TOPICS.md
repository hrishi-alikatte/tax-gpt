# VaudTaxAI — RAG Topics

> Topic catalogue for the active corpus. Each topic is a label attached to chunks during post-ingest tagging by the `vaud-tax-domain-analyst` agent. Drives retrieval boosts, completeness rule wiring, and UI labelling.

---

## 1. MVP topics (active in M1)

| Topic id              | English label                                  | French / Vaud terms                              | Rule owner              |
| --------------------- | ---------------------------------------------- | ------------------------------------------------ | ----------------------- |
| `permit_c_ordinary`   | C permit / ordinary taxation                   | Permis C, imposition ordinaire                   | n/a (intake gate)       |
| `salary_certificate`  | Salary certificate                             | Certificat de salaire                            | extraction layer        |
| `employment_income`   | Employment income                              | Revenu de l'activité dépendante                  | extraction layer        |
| `professional_expenses` | Professional expenses (general)              | Frais professionnels                             | `VD-EXPENSES-*` rules   |
| `commute`             | Commute / transport                            | Frais de déplacement, abonnement                 | `VD-COMMUTE-001`        |
| `meals`               | Meals at work                                  | Frais de repas, cantine                          | `VD-MEAL-001`           |
| `health_insurance`    | Health insurance premium                       | Prime d'assurance maladie (LAMal)                | `VD-INSURANCE-001`      |
| `pillar_3a`           | Pillar 3a                                      | 3e pilier A                                      | `VD-PILLAR3A-001`       |
| `bank_wealth`         | Bank accounts / wealth                         | Comptes bancaires, fortune                       | `VD-BANK-001`           |
| `securities`          | Securities (stocks, funds)                     | Titres, valeurs mobilières                       | `VD-SECURITIES-001`     |
| `debts`               | Debts                                          | Dettes                                           | `VD-DEBTS-001`          |
| `foreign_assets`      | Foreign assets                                 | Avoirs à l'étranger                              | `VD-FOREIGN-001`        |
| `supporting_docs`     | Supporting documents                           | Pièces justificatives                            | extraction layer        |

## 2. Deferred topics (post-M1 if time permits)

| Topic id              | English label                                  | Status                                           |
| --------------------- | ---------------------------------------------- | ------------------------------------------------ |
| `childcare`           | Childcare expenses                             | active rule already (`VD-CHILDCARE-001`); deepen |
| `alimony`             | Alimony / contributions to separated spouse    | deferred (rare for target persona)               |
| `donations`           | Charitable donations                           | deferred                                         |
| `medical_expenses`    | Out-of-pocket medical                          | deferred                                         |
| `disability`          | Disability deductions                          | deferred                                         |
| `real_estate_owned`   | Owner-occupied property                        | deferred (rare for renter persona)               |
| `private_pensions`    | Pillar 2 buy-back                              | deferred                                         |

## 3. Excluded topics (out of scope)

- Self-employed income (`revenu indépendant`).
- Business owners (`personnes morales`, `raison individuelle`).
- Quasi-residents / B-permit / G-permit special regimes.
- Source-tax (`impôt à la source`) reconciliation specifics.
- Inheritance and gift tax.
- Corporate tax of any kind.
- Other cantons (Geneva, Zurich, etc.).
- Federal direct tax (IFD) computation specifics.
- Tax optimization or planning advice.

If a user question lands on an excluded topic, the wrapper refuses with the standard refusal message.

## 4. Concept mapping (English → French/Vaud → topic → owner)

| English concept                        | French / Vaud term                       | Topic                  | Owner agent                         |
| -------------------------------------- | ---------------------------------------- | ---------------------- | ----------------------------------- |
| C permit                               | Permis C                                 | `permit_c_ordinary`    | `vaud-tax-domain-analyst`           |
| Ordinary taxation                      | Imposition ordinaire                     | `permit_c_ordinary`    | `vaud-tax-domain-analyst`           |
| Gross salary                           | Salaire brut                             | `employment_income`    | `ai-extraction-engineer`            |
| Net salary                             | Salaire net                              | `employment_income`    | `ai-extraction-engineer`            |
| Salary certificate                     | Certificat de salaire                    | `salary_certificate`   | `ai-extraction-engineer`            |
| AHV/IV/EO contributions                | Cotisations AVS/AI/APG                   | `employment_income`    | `ai-extraction-engineer`            |
| 2nd pillar (BVG/LPP) contributions     | Cotisations LPP                          | `employment_income`    | `ai-extraction-engineer`            |
| Commute / transport deduction          | Frais de déplacement                     | `commute`              | `completeness-engine-designer`      |
| Public transport pass                  | Abonnement de transport public           | `commute`              | `ai-extraction-engineer`            |
| Meal allowance                         | Frais de repas                           | `meals`                | `completeness-engine-designer`      |
| Health insurance premium               | Prime d'assurance maladie (LAMal)        | `health_insurance`     | `ai-extraction-engineer`            |
| Pillar 3a contribution                 | Cotisation 3e pilier A                   | `pillar_3a`            | `completeness-engine-designer`      |
| Bank balance year-end                  | Solde bancaire au 31 décembre            | `bank_wealth`          | `ai-extraction-engineer`            |
| Interest income                        | Intérêts perçus                          | `bank_wealth`          | `ai-extraction-engineer`            |
| Securities portfolio                   | Portefeuille de titres                   | `securities`           | `ai-extraction-engineer`            |
| Debts                                  | Dettes                                   | `debts`                | `ai-extraction-engineer`            |
| Foreign accounts                       | Avoirs à l'étranger                      | `foreign_assets`       | `vaud-tax-domain-analyst`           |
| Childcare expenses                     | Frais de garde des enfants               | `childcare`            | `completeness-engine-designer`      |
| Supporting documents                   | Pièces justificatives                    | `supporting_docs`      | `ai-extraction-engineer`            |

This table is the canonical EN↔FR mapping for retrieval-time topic boosts and UI labels. Updates flow through `vaud-tax-domain-analyst` PRs and must mirror `docs/DOMAIN_MODEL.md`.
