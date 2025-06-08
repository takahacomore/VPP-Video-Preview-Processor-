import os
import json
import subprocess
import platform
import flet as ft

def create_favorites_image_view(page, image_path, on_back=None, category_files=None):
    back_button = ft.IconButton(
        icon=ft.icons.ARROW_BACK,
        tooltip="Назад",
        on_click=on_back
    )
    image_widget = ft.Image(src=image_path, fit=ft.ImageFit.CONTAIN, expand=True, height=400)

    current_index = category_files.index(image_path) if category_files else 0

    def load_current_data(img_path):
        """Загрузка таймкода и пути к исходнику видео из descriptions_loc.json."""
        source, timestamp = "", ""
        loc_json_path = os.path.join(os.path.dirname(img_path), "descriptions_loc.json")
        if os.path.exists(loc_json_path):
            try:
                with open(loc_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_name = os.path.basename(img_path)
                    if file_name in data:
                        info = data[file_name]
                        if isinstance(info, dict):
                            source = info.get("source", "")
                            timestamp = info.get("timestamp", "")
                        else:
                            source = info
            except Exception as e:
                print(f"Ошибка при разборе {loc_json_path}: {e}")
        return source, timestamp

    current_source, current_timestamp = load_current_data(image_path)

    def open_source_folder(e):
        """Открытие папки с исходным видеофайлом."""
        target_path = current_source if current_source else image_path
        folder_path = os.path.dirname(target_path)
        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', target_path])
        elif platform.system() == "Darwin":
            subprocess.run(['open', folder_path])
        else:
            subprocess.run(['xdg-open', folder_path])

    def update_image(new_index):
        """Обновление изображения и таймкода."""
        nonlocal current_index, current_source, current_timestamp, image_widget
        if category_files and 0 <= new_index < len(category_files):
            current_index = new_index
            new_path = category_files[new_index]
            image_widget.src = new_path
            current_source, current_timestamp = load_current_data(new_path)
            timestamp_text.value = f"Таймкод: {current_timestamp}"
            page.update()

    def prev_image(e):
        update_image(current_index - 1)

    def next_image(e):
        update_image(current_index + 1)

    prev_btn = ft.IconButton(
        icon=ft.icons.ARROW_LEFT,
        tooltip="Предыдущее изображение",
        on_click=prev_image
    )

    next_btn = ft.IconButton(
        icon=ft.icons.ARROW_RIGHT,
        tooltip="Следующее изображение",
        on_click=next_image
    )

    open_folder_btn = ft.IconButton(
        icon=ft.icons.FOLDER_OPEN,
        tooltip="Открыть папку с исходным видео",
        on_click=open_source_folder
    )

    timestamp_text = ft.Text(f"Таймкод: {current_timestamp}", size=14)

    nav_row = ft.Row(
        controls=[
            prev_btn, timestamp_text, open_folder_btn, next_btn
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=15
    )

    content = ft.Column(
        controls=[
            ft.Row([back_button]),
            image_widget,
            nav_row  # <-- Переместил блок под изображение
        ],
        spacing=15,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER
    )

    return ft.Container(content=content, expand=True, padding=20)
