"""Upload view: file picker + classification result.

Calls `extract_from_upload` (the M2 entrypoint). Honors DEMO_MODE=replay
so the demo can run without real PDFs. For each upload, the user must
click "Confirm document type" before the document type is treated as
trusted.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import flet as ft

from TaxAI2025.core import config
from TaxAI2025.core.documents import DocumentRecord
from TaxAI2025.ui.components.footer import build_footer
from TaxAI2025.ui.navigation import Navigator, Screen
from TaxAI2025.ui.state import AppState


_DOC_TYPE_LABELS: dict[str, str] = {
    "salary_certificate": "Salary certificate (Certificat de salaire)",
    "health_insurance_premium": "Health insurance premium (Prime d'assurance maladie)",
    "daycare_invoice": "Daycare invoice (Facture de garde)",
    "pillar_3a_certificate": "Pillar 3a certificate (Attestation 3e pilier A)",
    "transport_pass": "Public transport subscription (Abonnement)",
    "bank_year_end_statement": "Bank year-end statement (Relevé bancaire)",
    "mortgage_interest_statement": "Mortgage interest statement (Intérêts hypothécaires)",
    "alimony_paid_received": "Alimony statement (Pension alimentaire)",
    "donation_receipt": "Donation receipt (Attestation de don)",
    "parental_support_receipt": "Parental support receipt (Aide aux parents)",
    "medical_bills_unreimbursed": "Unreimbursed medical bills (Frais médicaux)",
    "education_invoice": "Education invoice (Frais de formation)",
    "second_pillar_buyback_attestation": "Second-pillar buyback attestation (Rachat LPP)",
    "foreign_income_attestation": "Foreign income attestation (Revenu étranger)",
    "disability_proof": "Disability proof (Attestation invalidité)",
    "unemployment_benefits_attestation": "Unemployment benefits attestation (Chômage)",
    "unknown": "Unknown — needs your input",
}


def build_upload_view(
    state: AppState,
    navigator: Navigator,
    page: ft.Page,
) -> ft.Control:
    is_replay = config.DEMO_MODE == "replay"
    confirmed_doc_ids: set[str] = set()
    error_banner = ft.Container(visible=False)
    docs_column = ft.Column(spacing=12)
    
    # Progress indicator
    progress_bar = ft.ProgressBar(width=400, color="#4F46E5", visible=False)
    status_text = ft.Text(size=12, color="#64748B", visible=False)

    def render_error(message: str, hint: str | None = None) -> None:
        error_banner.content = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.ERROR_OUTLINE, color="#B91C1C"),
                            ft.Text(message, color="#B91C1C", weight="w600"),
                        ],
                        spacing=8,
                    ),
                    ft.Text(hint or "", size=12, color="#7F1D1D"),
                ],
                spacing=4,
            ),
            padding=12,
            bgcolor="#FEE2E2",
            border=ft.border.all(1, "#FCA5A5"),
            border_radius=8,
        )
        error_banner.visible = True
        progress_bar.visible = False
        status_text.visible = False
        page.update()

    def clear_error() -> None:
        error_banner.visible = False
        page.update()

    def set_loading(is_loading: bool, text: str = "") -> None:
        progress_bar.visible = is_loading
        status_text.visible = is_loading
        status_text.value = text
        pick_btn.disabled = is_loading
        page.update()

    def render_doc_card(record: DocumentRecord) -> ft.Control:
        confirmed = record.doc_id in confirmed_doc_ids
        type_label = _DOC_TYPE_LABELS.get(record.document_type, record.document_type)
        confidence = (
            f"{record.classifier_confidence:.0%}"
            if record.classifier_confidence is not None
            else "—"
        )

        confirm_btn = ft.ElevatedButton(
            "Confirm document type" if not confirmed else "Confirmed",
            icon=ft.icons.CHECK if confirmed else ft.icons.HOW_TO_REG,
            bgcolor="#10B981" if confirmed else "#4F46E5",
            color="white",
            disabled=confirmed,
        )

        def on_confirm(_e: Any, doc_id: str = record.doc_id) -> None:
            confirmed_doc_ids.add(doc_id)
            state.confirm_document_type(doc_id)
            rerender()

        confirm_btn.on_click = on_confirm

        facts_for_doc = [f for f in state.facts if f.source_doc == record.filename]
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.icons.PICTURE_AS_PDF, color="#4F46E5"),
                            ft.Text(record.filename, weight="w700", size=14),
                            ft.Container(expand=True),
                            ft.Text(
                                f"classifier: {record.classifier_method} "
                                f"({confidence})",
                                size=11, color="#64748B",
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Text(
                        f"We think this is a {type_label}. Confirm?",
                        size=13, color="#1E293B",
                    ),
                    ft.Text(
                        f"{len(facts_for_doc)} value(s) extracted (you'll confirm "
                        "each one on the next screen).",
                        size=12, color="#64748B",
                    ),
                    ft.Row([confirm_btn]),
                ],
                spacing=8,
            ),
            padding=14,
            bgcolor="#FFFFFF",
            border=ft.border.all(1, "#E2E8F0"),
            border_radius=10,
        )

    def rerender() -> None:
        docs_column.controls = [render_doc_card(d) for d in state.documents]
        if not state.documents:
            docs_column.controls.append(
                ft.Text(
                    "No documents uploaded yet.",
                    size=13, color="#94A3B8", italic=True,
                )
            )
        continue_btn.disabled = not (
            state.documents
            and len(confirmed_doc_ids) == len(state.documents)
        )
        page.update()

    def ingest_path(path: Path) -> None:
        try:
            from TaxAI2025.extraction import extract_from_upload

            set_loading(True, f"AI is extracting data from {path.name}...")
            record, facts = extract_from_upload(path)
            state.add_document(record, facts)
            clear_error()
            set_loading(False)
            rerender()
        except Exception as ex:  # noqa: BLE001
            render_error(
                "We couldn't process that document.",
                hint=f"{type(ex).__name__}: {ex}",
            )

    def handle_upload_result(e: ft.FilePickerResultEvent) -> None:
        if not e.files:
            return
        
        set_loading(True, "Uploading files...")
        for f in e.files:
            # For web, we need to upload the file to the server
            upload_url = page.get_upload_url(f.name, 600)
            file_picker.upload([ft.FilePickerUploadFile(f.name, upload_url)])

    def handle_upload_progress(e: ft.FilePickerUploadEvent) -> None:
        if e.progress == 1.0:
            # File is on server, now process it
            # Flet uploads to the 'uploads' directory relative to the app root
            upload_path = Path("uploads") / e.file_name
            if upload_path.exists():
                ingest_path(upload_path)
            else:
                render_error("Upload failed: File not found on server.")

    file_picker = ft.FilePicker(on_result=handle_upload_result)
    file_picker.on_upload_progress = handle_upload_progress
    page.overlay.append(file_picker)

    def pick_files(_e: Any) -> None:
        clear_error()
        file_picker.pick_files(
            allow_multiple=True,
            allowed_extensions=["pdf"],
        )

    def use_synthetic(_e: Any) -> None:
        clear_error()
        try:
            ingest_path(Path("synthetic_certificat_de_salaire_2024.pdf"))
        except Exception as ex:  # noqa: BLE001
            render_error(
                "Could not load synthetic Sarah documents.",
                hint=f"{type(ex).__name__}: {ex}",
            )

    pick_btn = ft.ElevatedButton(
        "Upload PDF(s)",
        icon=ft.icons.UPLOAD_FILE,
        bgcolor="#4F46E5",
        color="white",
        on_click=pick_files,
    )
    synthetic_btn = ft.OutlinedButton(
        "Use synthetic Sarah documents",
        icon=ft.icons.AUTO_AWESOME,
        on_click=use_synthetic,
        visible=is_replay,
    )

    continue_btn = ft.ElevatedButton(
        "Continue to confirm values",
        icon=ft.icons.ARROW_FORWARD,
        bgcolor="#4F46E5",
        color="white",
        disabled=True,
        on_click=lambda _e: navigator.go(Screen.EXTRACTED),
    )

    body = ft.Column(
        [
            ft.Text("Upload your documents", size=26, weight="w800", color="#0F172A"),
            ft.Text(
                "We classify each PDF and extract the values. Nothing leaves "
                "this step until you confirm the document type.",
                size=14, color="#475569",
            ),
            ft.Row([pick_btn, synthetic_btn], spacing=12),
            ft.Column([progress_bar, status_text], spacing=4),
            error_banner,
            ft.Divider(color="#E2E8F0"),
            docs_column,
            ft.Container(height=10),
            ft.Row([continue_btn], alignment=ft.MainAxisAlignment.END),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
    )

    rerender()
    return ft.Column(
        [
            ft.Container(content=body, padding=30, expand=True),
            build_footer(),
        ],
        expand=True,
        spacing=0,
    )


__all__ = ["build_upload_view"]
