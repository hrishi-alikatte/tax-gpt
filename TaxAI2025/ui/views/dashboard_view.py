import flet as ft
from TaxAI2025.ui.components.chat_bubble import create_chat_message

def get_dashboard_view(page: ft.Page, brain, db_manager, agent):
    chat_history = ft.ListView(expand=True, spacing=15, padding=20, auto_scroll=True)
    
    # Load previous session logic could go here
    chat_history.controls.append(create_chat_message("👋 **Hello!** I am TaxPilot, your Vaud tax assistant. Upload a PDF to start.", is_user=False))

    msg_input = ft.TextField(
        hint_text="Ask a question...", 
        expand=True, 
        border_radius=20, 
        bgcolor="#FFFFFF", 
        border_color="#CBD5E1",
        color="#1E293B",
        cursor_color="#4F46E5",
        content_padding=ft.padding.only(left=20, right=20, top=15, bottom=15),
        disabled=True, 
        on_submit=lambda e: send_message(e)
    )

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            status_text.value = f"Ingesting {e.files[0].name}..."
            page.update()
            
            try:
                brain.load_data(file_path)
                db_manager.log_document(e.files[0].name)
                
                status_text.value = "Ready!"
                status_text.color = "green"
                msg_input.disabled = False
                msg_input.focus()
                chat_history.controls.append(create_chat_message(f"✅ Analyzed **{e.files[0].name}**.", is_user=False))
            except PermissionError:
                status_text.value = "Upload Error"
                status_text.color = "red"
                chat_history.controls.append(create_chat_message(f"⚠️ **macOS Blocked Access!**\n\nYour Terminal/IDE does not have permission to read from the `Documents` folder.\n\n**Quick Fix:** Move the PDF to your `Desktop` folder (or directly inside the `VaudTaxAI` folder) and upload it from there!", is_user=False))
            except Exception as ex:
                status_text.value = "Upload Error"
                status_text.color = "red"
                chat_history.controls.append(create_chat_message(f"⚠️ Error reading file: {str(ex)}", is_user=False))
                
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # Sidebar components
    status_text = ft.Text("Upload PDF", color="#1E293B", weight="w500")
    
    def pick_files_click(e):
        file_picker.pick_files(allow_multiple=False, allowed_extensions=["pdf"])

    upload_btn = ft.Container(
        content=ft.Row([ft.Icon(ft.icons.UPLOAD_FILE), status_text], alignment=ft.MainAxisAlignment.CENTER),
        padding=15, bgcolor="#F1F5F9", border_radius=10, 
        on_click=pick_files_click, border=ft.border.all(1, "#CBD5E1")
    )

    def send_message(e):
        if not msg_input.value: return
        question = msg_input.value
        msg_input.value = ""
        
        chat_history.controls.append(create_chat_message(question, is_user=True))
        page.update()
        
        # Async-like update for loading
        loading = ft.Text("Thinking...", size=12, italic=True)
        chat_history.controls.append(loading)
        page.update()
        
        # Agent Invocation
        session_id = "session_1"
        initial_state = {
            "session_id": session_id,
            "messages": [{"role": "user", "content": question}],
            "profile": db_manager.get_user_profile(session_id),
            "next_action": "",
            "reply": "",
            "query_to_search": ""
        }
        
        try:
            result = agent.invoke(initial_state)
            response = result["reply"]
            # After invocation, update the profile display
            update_profile_display(session_id)
        except Exception as ex:
            response = f"⚠️ Agent Error: {str(ex)}"
            print(ex)
        
        chat_history.controls.pop()
        chat_history.controls.append(create_chat_message(response, is_user=False))
        
        # Log to DB
        db_manager.add_message(session_id, "user", question)
        db_manager.add_message(session_id, "ai", response)
        page.update()

    send_btn = ft.Container(
        content=ft.IconButton(ft.icons.SEND_ROUNDED, icon_color="white", on_click=send_message),
        bgcolor="#4F46E5",
        border_radius=20,
        padding=5
    )

    # Dynamic Profile Sidebar
    profile_col = ft.Column(spacing=10)
    def update_profile_display(session_id="session_1"):
        profile = db_manager.get_user_profile(session_id)
        profile_col.controls.clear()
        
        if not any(profile.values()):
            profile_col.controls.append(ft.Text("We are learning about you...", color="#94A3B8", italic=True, size=13))
        else:
            for k, v in profile.items():
                if v is not None:
                    nice_key = k.replace("_", " ").title()
                    profile_col.controls.append(ft.Text(f"• {nice_key}: {v}", size=14, color="#334155", weight="w500"))
        page.update()

    # Initial render
    update_profile_display()

    return ft.Row([
        # Sidebar
        ft.Container(width=280, bgcolor="#FFFFFF", padding=25, border=ft.border.only(right=ft.BorderSide(1, "#E2E8F0")), content=ft.Column([
            ft.Text("TaxPilot", size=26, weight="w900", color="#0F172A"),
            ft.Text("Vaud Assistant", size=13, color="#64748B", italic=True),
            ft.Divider(height=30, color="#E2E8F0"),
            upload_btn,
            ft.Divider(height=30, color="#E2E8F0"),
            ft.Text("User Profile", size=16, weight="w800", color="#0F172A"),
            profile_col
        ])),
        # Chat Area
        ft.Container(expand=True, bgcolor="#F8FAFC", padding=0, content=ft.Column([
            ft.Container(content=chat_history, expand=True, padding=ft.padding.only(left=20, right=20, top=20)),
            ft.Container(
                content=ft.Row([msg_input, send_btn]), 
                padding=20, 
                bgcolor="#FFFFFF",
                border=ft.border.only(top=ft.BorderSide(1, "#E2E8F0"))
            )
        ]))
    ], expand=True, spacing=0)
