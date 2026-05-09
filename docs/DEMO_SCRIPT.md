# VaudTaxAI — Live Demo Script

> Exact 5-minute live demo flow. The fixtures below are committed (synthetic). The fallback plan covers OCR / LLM failure mid-demo.

---

## Synthetic user profile (THE persona)

**Sarah Müller**

- C-permit, 7 years in Switzerland.
- 34 years old, married to **David Müller** (also employed).
- 1 child, **Lina**, age 4, in daycare.
- Resides in **Lausanne**, works in **Renens**.
- Salaried at a synthetic company "Aurelius SA" as a software engineer.
- Tax year **2024**.

> Sarah's situation is engineered to trigger exactly **three** completeness findings: childcare deduction not yet provided, pillar 3a not yet provided, transport / commute not yet provided.

---

## Synthetic documents (committed under `demo/scenarios/expat_c_permit_basic/docs/`)

1. `salary_certificate_sarah_2024.pdf` — Certificat de salaire showing gross 110'000 CHF, net 92'000 CHF, pension contributions, etc.
2. `health_insurance_assura_2024.pdf` — annual premium 4'200 CHF, insured: Sarah + Lina.
3. `bank_yearend_2024.pdf` — UBS year-end statement, balance 18'400 CHF, interest 12 CHF.

> Note: childcare invoice, pillar 3a, and transport pass are deliberately **omitted** — that is what the completeness engine surfaces.

---

## Demo flow (5 minutes, narrated)

### 0:00 — Pitch (30s)

> *"Filing taxes in Vaud as an English-speaking C-permit resident is painful. The forms are in French, the deductions are obscure, and most expats don't know what they're missing. VaudTaxAI is a copilot that helps them understand, extract, confirm, and find what they forgot — all grounded in the official Vaud guide."*

### 0:30 — Intake screen (45s)

- Type "Sarah", select married, 1 child age 4, residence Lausanne, work Renens.
- Click "Continue".

### 1:15 — Upload screen (60s)

- Drag in `salary_certificate_sarah_2024.pdf`.
- Classifier shows: *"This looks like a Certificat de salaire. Confirm?"*
- Confirm. Repeat for the health insurance PDF and bank statement.

### 2:15 — Extracted-values screen (60s)

- Show every extracted value with source page + confidence badge.
- **Tick each Confirm checkbox** (this is the demo's most important moment — narrate: *"the AI never moves forward without me confirming").*
- "Continue" enables.

### 3:15 — Completeness screen (90s) — **the punchline**

Three findings render:

1. **You may have childcare deductions to claim** — Lina is 4, you mentioned daycare. Cite *[Vaud Instructions p.X]*. CTA: "Provide invoice".
2. **You may be missing your pillar 3a contribution** — Cite *[Vaud Instructions p.X]*. CTA: "Provide statement".
3. **You commute Lausanne → Renens** — Cite *[Vaud Instructions p.X]*. CTA: "Provide transport pass".

Narrate: *"None of these were in Sarah's documents. Each is grounded in a specific page of the official Vaud guide. The system didn't optimize her taxes — it just told her what she forgot."*

### 4:45 — Mapping + Explain (15s — kept short)

- Show mapping table briefly (English ↔ French ↔ VaudTax code).
- Ask the explain panel: *"What is the cap on pillar 3a contributions for an employed person in 2024?"*
- Answer renders with `[Vaud Instructions p.X]` inline citation.

---

## Expected per-screen outputs

| Screen          | Expected                                                                                            |
| --------------- | --------------------------------------------------------------------------------------------------- |
| Intake          | `UserProfile` saved, navigation enabled                                                             |
| Upload          | 3 `DocumentRecord`s, classifications confirmed                                                      |
| Extracted       | ≈ 9 `TaxFact`s (3 from salary cert, 1 from insurance, 2 from bank, plus identity), all confirmed    |
| Completeness    | Exactly 3 `Finding`s with rule ids `VD-CHILDCARE-001`, `VD-PILLAR3A-001`, `VD-COMMUTE-001`          |
| Mapping         | Table shows confirmed values with VaudTax codes                                                     |
| Explain         | Answer text contains at least one `[Vaud Instructions p.` citation                                  |

---

## Fallback plan

### If OCR fails on a real PDF mid-demo

- Switch to `DEMO_MODE=replay` (env var or in-app toggle).
- The pipeline reads `demo/scenarios/expat_c_permit_basic/extracted.json` instead of running live OCR.
- Same screens, same outputs. Audience cannot tell.

### If LLM call hangs / rate-limits

- `rag/explain.py` returns canned `GroundedAnswer` from `demo/scenarios/expat_c_permit_basic/answers/<question_hash>.json` when `DEMO_MODE=replay`.
- Pre-cached answers cover the explain-panel question(s) in this script.

### If the Flet UI hangs

- Last-resort: run `python -m vaudtax.demo.runner --scenario expat_c_permit_basic --verbose` in a terminal split. The runner prints the same six-screen output as plain text + JSON. Continue narration over the terminal.

### Pre-demo checklist (run 30 minutes before)

- [ ] `DEMO_MODE=replay python main.py` boots and walks the flow once.
- [ ] `python -m vaudtax.demo.runner --scenario expat_c_permit_basic` exits 0.
- [ ] All three fixture PDFs render correctly when opened.
- [ ] No `.env` opened on screen during demo (secrets hygiene).
- [ ] Wi-Fi backup tethered phone in case venue network drops.
