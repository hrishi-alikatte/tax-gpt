"""Generate the synthetic Vaud demo PDFs for the `expat_c_permit_basic`
scenario (Sarah Müller, Lausanne, married, 1 child age 4, employed in
Renens).

Each builder writes one PDF whose French/German heading matches the
classifier's keyword heuristics (TaxAI2025/extraction/classify.py) so
that the extractor lands on the right `DocumentRecord.doc_type`.

All values are synthetic. No real PII. Output goes to
`demo/custom_tests/` (gitignored, never committed). Run from repo root:

    python scripts/generate_custom_pdfs.py
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

OUT_DIR = Path("demo/custom_tests")

# Shared synthetic identity — matches demo/scenarios/expat_c_permit_basic/profile.json
TAXPAYER = "Sarah Müller"
SPOUSE = "Marc Müller"
CHILD = "Léa Müller (4 ans)"
ADDRESS = "Avenue de la Gare 12, 1003 Lausanne"
EMPLOYER = "Aurelius SA"
EMPLOYER_ADDRESS = "Route de Cossonay 28, 1020 Renens"
TAX_YEAR = 2025


def _start(filename: Path, title_fr: str, title_de: str | None = None) -> tuple[canvas.Canvas, float, float]:
    """Stamp the standard heading + return the canvas + page dims."""
    filename.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(filename), pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, title_fr)
    if title_de:
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 65, title_de)
    return c, width, height


def _footer(c: canvas.Canvas) -> None:
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 50, "Document synthétique — démo VaudTaxAI. Aucune valeur réelle.")
    c.save()


def create_salary_certificate(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Certificat de salaire / Titres de participations",
        "Lohnausweis / Beteiligungsverzeichnis",
    )
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, f"Employer: {EMPLOYER}")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 115, EMPLOYER_ADDRESS)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 100, f"Employé: {TAXPAYER}")
    c.setFont("Helvetica", 10)
    c.drawString(300, height - 115, ADDRESS)

    c.line(50, height - 150, 550, height - 150)
    c.drawString(60, height - 170, "1. Salaire brut / Bruttolohn")
    c.drawString(450, height - 170, "CHF 110'000.00")
    c.drawString(60, height - 190, "8. Salaire net / Nettolohn")
    c.drawString(450, height - 190, "CHF 92'000.00")

    c.rect(60, height - 220, 10, 10, fill=1)
    c.drawString(80, height - 215, "G. Repas à la cantine de l'employeur (X)")

    _footer(c)


def create_health_insurance_premium(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Attestation de primes d'assurance-maladie 2025",
        "Bestätigung Krankenkassenprämien — Helsana",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Assuré: {TAXPAYER}")
    c.drawString(50, height - 115, ADDRESS)
    c.drawString(50, height - 130, "Police LAMal: 9876543210")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Prime annuelle 2025 (assurance-maladie de base)")
    c.drawString(450, height - 170, "CHF 4'200.00")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 200, "Cette attestation peut être utilisée pour la déduction fiscale.")
    _footer(c)


def create_pillar3a_certificate(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Attestation Pilier 3a / Säule 3a 2025",
        "UBS Vorsorge — 3e pilier lié",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Titulaire: {TAXPAYER}")
    c.drawString(50, height - 115, f"Adresse: {ADDRESS}")
    c.drawString(50, height - 130, "N° de compte: 3A-VD-118273")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Cotisation versée pour l'année 2025")
    c.drawString(450, height - 170, "CHF 7'056.00")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 195, "(Plafond fédéral salarié 2025: CHF 7'258.—)")

    _footer(c)


def create_daycare_invoice(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Crèche / Garderie — Récapitulatif annuel 2025",
        "Kita-Jahresbescheinigung",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, "Crèche Tournesol, Lausanne")
    c.drawString(50, height - 115, f"Famille: {TAXPAYER}")
    c.drawString(50, height - 130, f"Enfant: {CHILD}")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Total des frais de garde payés en 2025")
    c.drawString(450, height - 170, "CHF 14'400.00")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 195, "12 mensualités, structure d'accueil reconnue par l'État de Vaud.")

    _footer(c)


def create_bank_year_end_statement(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Relevé de compte annuel — BCV",
        "Banque Cantonale Vaudoise — Kontoauszug",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Titulaire: {TAXPAYER} & {SPOUSE}")
    c.drawString(50, height - 115, "Compte: 12-345678-9 (compte joint)")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 160, "Solde au 31.12.2025")
    c.drawString(450, height - 160, "CHF 18'400.00")
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 180, "Intérêts annuels 2025")
    c.drawString(450, height - 180, "CHF 12.00")

    _footer(c)


def create_transport_pass(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Abonnement CFF / SBB — Mobilis Vaud",
        "Annual transport pass — facture",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Voyageur: {TAXPAYER}")
    c.drawString(50, height - 115, f"Trajet domicile-travail: Lausanne ↔ Renens")
    c.drawString(50, height - 130, "Type: Abonnement annuel Mobilis zones 11+12")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Coût total 2025")
    c.drawString(450, height - 170, "CHF 1'140.00")

    _footer(c)


def create_donation_receipt(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Attestation de don — Croix-Rouge Suisse",
        "Spendenbescheinigung",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Donateur: {TAXPAYER}")
    c.drawString(50, height - 115, ADDRESS)
    c.drawString(50, height - 130, "Reçu n°: CR-2025-00871")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 170, "Don total versé en 2025")
    c.drawString(450, height - 170, "CHF 600.00")
    c.setFont("Helvetica", 10)
    c.drawString(
        50,
        height - 200,
        "Organisation reconnue d'utilité publique. Don déductible selon l'art. 33a LIFD.",
    )

    _footer(c)


def create_medical_bills(filename: Path) -> None:
    c, _, height = _start(
        filename,
        "Frais médicaux non remboursés 2025",
        "Nicht erstattete Krankheitskosten",
    )
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 100, f"Patient: {TAXPAYER}")
    c.drawString(50, height - 115, ADDRESS)

    c.drawString(50, height - 150, "Détail:")
    c.drawString(70, height - 170, "• Soins dentaires (Dr. Renaud, Lausanne)         CHF 950.00")
    c.drawString(70, height - 190, "• Franchise et quote-part LAMal                    CHF 300.00")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 230, "Total non remboursé 2025")
    c.drawString(450, height - 230, "CHF 1'250.00")

    _footer(c)


SPEC: list[tuple[str, callable]] = [
    ("01_certificat_salaire.pdf", create_salary_certificate),
    ("02_assurance_maladie.pdf", create_health_insurance_premium),
    ("03_pilier_3a.pdf", create_pillar3a_certificate),
    ("04_garderie.pdf", create_daycare_invoice),
    ("05_releve_bcv.pdf", create_bank_year_end_statement),
    ("06_abonnement_cff.pdf", create_transport_pass),
    ("07_attestation_don.pdf", create_donation_receipt),
    ("08_frais_medicaux.pdf", create_medical_bills),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in SPEC:
        path = OUT_DIR / name
        builder(path)
        size = path.stat().st_size
        print(f"  ✓ {path}  ({size:,} bytes)")
    print(f"\n{len(SPEC)} PDFs written to {OUT_DIR}/")


if __name__ == "__main__":
    main()
