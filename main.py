import sys
import os
import flet as ft

# Ensure the package is in path
sys.path.append(os.getcwd())

from TaxAI2025.brain.rag import TaxKnowledgeBase
from TaxAI2025.core.database import DatabaseManager
from TaxAI2025.brain.agent_graph import build_tax_agent
from TaxAI2025.ui.views.welcome_view import get_welcome_view
from TaxAI2025.ui.views.dashboard_view import get_dashboard_view

def main(page: ft.Page):
    page.title = "TaxPilot - Vaud Tax Assistant"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F8FAFC"
    page.window_width = 1100
    
    # --- Dependencies ---
    brain = TaxKnowledgeBase()
    db = DatabaseManager()
    agent = build_tax_agent(brain, db)

    # --- Navigation ---
    def go_to_dashboard(e):
        page.clean()
        page.add(get_dashboard_view(page, brain, db, agent))
        page.update()

    def go_to_welcome(e=None):
        page.clean()
        page.add(get_welcome_view(on_start_click=go_to_dashboard))
        page.update()

    # --- Start ---
    go_to_welcome()

if __name__ == "__main__":
    ft.app(main)
