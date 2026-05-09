import flet as ft

def get_welcome_view(on_start_click):
    return ft.Column([
        ft.Container(height=60), # Spacer
        ft.Container(
            padding=ft.padding.symmetric(vertical=40, horizontal=40),
            content=ft.Column([
                ft.Container(content=ft.Icon(ft.icons.SMART_TOY_ROUNDED, size=120, color="#818CF8"), padding=20, bgcolor="#EEF2FF", border_radius=100),
                ft.Container(height=30),
                ft.Text("File your Vaud taxes in under 45 minutes", size=32, weight="bold", color="#1E293B", text_align=ft.TextAlign.CENTER),
                ft.Text("Private AI Assistant. Official Sources Only.", size=16, color="#64748B", text_align=ft.TextAlign.CENTER),
                ft.Container(height=30),
                ft.ElevatedButton("Start New Filing", color="white", bgcolor="#4F46E5", icon=ft.icons.ROCKET_LAUNCH, 
                                  style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12), padding=25), on_click=on_start_click),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        ),
    ], scroll=ft.ScrollMode.AUTO)
