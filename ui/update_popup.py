import flet as ft

def open_popup(page, message, on_yes=None):
    # отладочный вывод, чтобы точно знать, что мы здесь
    print(">>> open_popup called from", __file__, "message:", message)

    # формируем кнопки
    if on_yes:
        actions = [
            ft.TextButton("Нет", on_click=lambda e: close_popup(page)),
            ft.TextButton("Обновить", on_click=on_yes),
        ]
    else:
        actions = [
            ft.TextButton("ОК", on_click=lambda e: close_popup(page)),
        ]

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Обновление"),
        content=ft.Text(message),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )
    # сохраняем и открываем через page.open
    page.dialog = dialog
    page.open(dialog)

def close_popup(page):
    print(">>> close_popup called")
    if hasattr(page, "dialog") and page.dialog:
        page.dialog.open = False
        page.update()
