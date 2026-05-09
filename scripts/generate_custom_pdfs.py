from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os

def create_salary_certificate(filename, name, employer):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Certificat de salaire / Titres de participations")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 65, "Lohnausweis / Beteiligungsverzeichnis")
    
    # Employer
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, height - 100, f"Employer: {employer}")
    c.setFont("Helvetica", 10)
    c.drawString(50, height - 115, "ACME Street 1, 1000 Lausanne")

    # Employee
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 100, f"Employee: {name}")
    c.setFont("Helvetica", 10)
    c.drawString(300, height - 115, "Chemin du Test 123, 1003 Lausanne")
    
    # Table headers
    c.line(50, height - 150, 550, height - 150)
    c.drawString(60, height - 170, "1. Salaire brut / Bruttolohn")
    c.drawString(450, height - 170, "CHF 140'000.00")
    
    c.drawString(60, height - 190, "8. Salaire net / Nettolohn")
    c.drawString(450, height - 190, "CHF 115'000.00")
    
    # Canteen Checkbox (Field G)
    c.rect(60, height - 220, 10, 10, fill=1)
    c.drawString(80, height - 215, "G. Repas gratuits à la cantine (X)")
    
    # Official Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 50, "Canton de Vaud - Document synthétique pour test AI.")
    
    c.save()

def create_bank_statement(filename, name):
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Relevé de compte - BCV")
    
    # Details
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Titulaire: {name}")
    c.drawString(50, height - 120, "Compte: 12-345678-9")
    
    c.drawString(50, height - 160, "Solde au 31.12.2024:")
    c.setFont("Helvetica-Bold", 12)
    c.drawString(300, height - 160, "CHF 52'450.00")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 180, "Intérêts annuels 2024:")
    c.drawString(300, height - 180, "CHF 125.40")

    # Childcare/Education
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 250, "Attestations Frais de Garde")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 270, "Garderie 'Les Petits Amis' - Lausanne")
    c.drawString(50, height - 290, "Enfant: Bébé Hrishi (2 ans)")
    c.drawString(50, height - 310, "Montant payé en 2024:")
    c.drawString(300, height - 310, "CHF 12'000.00")

    c.save()

if __name__ == "__main__":
    os.makedirs("demo/custom_tests", exist_ok=True)
    create_salary_certificate("demo/custom_tests/certificat_salaire_hrishi.pdf", "Hrishi", "Venkat")
    create_bank_statement("demo/custom_tests/documents_annexes_hrishi.pdf", "Hrishi")
    print("PDFs generated in demo/custom_tests/")
