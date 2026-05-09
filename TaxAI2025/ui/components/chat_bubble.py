import flet as ft

def create_chat_message(text, is_user=False):
    # User: Clean Light Indigo, AI: Crisp White with subtle border
    bg_color = "#E0E7FF" if is_user else "#FFFFFF"
    text_color = "#1E293B" # Very dark blue/grey for exceptional contrast
    align = ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START
    
    return ft.Row([
        ft.Container(
            content=ft.Markdown(
                text, 
                selectable=True
            ),
            bgcolor=bg_color,
            padding=ft.padding.all(16),
            border_radius=ft.border_radius.only(
                top_left=15, top_right=15, 
                bottom_left=15 if is_user else 5, 
                bottom_right=5 if is_user else 15
            ),
            width=500,
            border=ft.border.all(1, "#E2E8F0") if not is_user else None,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=4, color=ft.colors.with_opacity(0.04, ft.colors.BLACK))
        )
    ], alignment=align)
