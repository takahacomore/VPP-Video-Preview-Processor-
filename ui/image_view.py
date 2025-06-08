import os
import sys
# Добавляем родительскую директорию, чтобы Python видел папку modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import json
import chardet
import subprocess
import platform
import flet as ft
from pathlib import Path
from modules.favorites_manager import FavoritesManager
from modules.file_watcher import FileWatcher

def read_file_with_detect(fpath):
    """
    Считывает содержимое файла, определяя кодировку.
    """
    try:
        if not os.path.exists(fpath):
            return ""
        with open(fpath, 'rb') as f:
            content = f.read()
        if not content:
            return ""
        result = chardet.detect(content)
        encoding = result['encoding'] or 'utf-8'
        return content.decode(encoding, errors='replace')
    except Exception as e:
        print(f"Ошибка при чтении файла {fpath}: {e}")
        return ""

def create_image_view(page, current_file, all_files, return_page=0, search_query="", page_number=0, on_back=None, category_files=None):
    """
    Создает интерфейс просмотра стопкадра и его описания на основе списка all_files,
    отображённых на странице.
    
    Args:
        page (ft.Page): Страница приложения.
        current_file (str): Путь к выбранному стопкадру.
        all_files (list): Список путей к изображениям (стопкадрам), доступных для переключения.
        return_page (int): Параметр для возврата (0 – основное окно, 1 – избранное).
        search_query (str): Исходный поисковый запрос (для возврата).
        page_number (int): Номер страницы для возврата.
        on_back (callable, optional): Функция для возврата назад.
        category_files (list, optional): Дополнительный список файлов (при наличии) для переключения.
    
    Returns:
        ft.Container: Контейнер с интерфейсом просмотра.
    """
    # Приоритет: если передан category_files, используем его, иначе список all_files
    

    file_list = all_files.copy()
    if current_file in file_list:
        current_index = file_list.index(current_file)
    else:
        # Не показываем пустой стопкадр, если кадра нет в списке
        return ft.Container(
            content=ft.Text("Файл не найден или не принадлежит текущему поиску", color=ft.colors.RED),
            alignment=ft.alignment.center,
            expand=True
        )
    

    def load_current_data(file_path):
        """
        Загружает данные для стопкадра:
          - Описание из файла <имя стопкадра>_pixtral.json.
          - Дополнительные данные (source, timestamp, fps) из файла descriptions_loc.json.
        """
        base = os.path.splitext(file_path)[0]
        pixtral_json = f"{base}_pixtral.json"
        desc = ""
        if os.path.exists(pixtral_json):
            try:
                with open(pixtral_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    desc = data.get("text", "")
            except Exception as e:
                print(f"Ошибка при разборе {pixtral_json}: {e}")
        source, ts, fps_val = "", "", ""
        loc_json_path = os.path.join(os.path.dirname(file_path), "descriptions_loc.json")
        if os.path.exists(loc_json_path):
            try:
                with open(loc_json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_name = os.path.basename(file_path)
                    if file_name in data:
                        info = data[file_name]
                        if isinstance(info, dict):
                            source = info.get("source", "")
                            ts = info.get("timestamp", "")
                            fps_val = str(info.get("fps", ""))
                        else:
                            source = info
            except Exception as e:
                print(f"Ошибка при разборе {loc_json_path}: {e}")
        return desc, source, ts, fps_val

    # Загружаем данные для текущего стопкадра
    current_desc, current_source, current_ts, current_fps = load_current_data(current_file)

    # Определяем состояние избранного
    favorites_manager = FavoritesManager()
    is_favorite = favorites_manager.is_favorite(current_file)
    screenshot_data = favorites_manager.get_screenshot_data(current_file) if is_favorite else {}

    # Виджет изображения

    image_widget = ft.Container(
        alignment=ft.alignment.center,
        expand=True,
        content=ft.Image(
            src=current_file,
            fit=ft.ImageFit.CONTAIN,
            height=400
        )
    )
    

    def update_favorite_button():
        nonlocal is_favorite, screenshot_data
        previous_state = is_favorite
        is_favorite = favorites_manager.is_favorite(current_file)
        screenshot_data = favorites_manager.get_screenshot_data(current_file) if is_favorite else {}
        favorite_button.icon = ft.icons.FAVORITE if is_favorite else ft.icons.FAVORITE_BORDER
        favorite_button.icon_color = ft.colors.RED if is_favorite else ft.colors.GREY_500
        favorite_button.tooltip = "Изменить категории" if is_favorite else "Добавить в избранное"
        favorite_button.style = ft.ButtonStyle(
            color={
                "": ft.colors.RED if is_favorite else ft.colors.GREY_500,
                "hovered": ft.colors.RED,
            },
            overlay_color={"hovered": ft.colors.RED_50},
            animation_duration=300,
        )
        if is_favorite and not previous_state:
            page.snack_bar = ft.SnackBar(content=ft.Text("Изображение добавлено в избранное"))
            page.snack_bar.open = True
        elif not is_favorite and previous_state:
            page.snack_bar = ft.SnackBar(content=ft.Text("Изображение удалено из избранного"))
            page.snack_bar.open = True
        page.update()

    def open_category_dialog(e):
        print("Открываем диалог категорий...")
        page.snack_bar = ft.SnackBar(content=ft.Text("Открывается диалог категорий..."))
        page.snack_bar.open = True
        page.update()
        cats = favorites_manager.get_categories()
        print(f"Доступные категории: {cats}")
        if not cats:
            print("Создаем категорию 'Общее'")
            favorites_manager.add_category("Общее", "#1976D2")
            cats = favorites_manager.get_categories()
        if not cats:
            page.snack_bar = ft.SnackBar(content=ft.Text("Не удалось создать категории"))
            page.snack_bar.open = True
            page.update()
            return
        print(f"Категории после проверки: {cats}")
        checkboxes = []
        for cat in cats:
            is_checked = False
            if is_favorite and screenshot_data:
                categories = screenshot_data.get("categories", [])
                is_checked = cat in categories if categories else False

            cb = ft.Checkbox(
                label=cat,
                value=is_checked,
                fill_color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK,
                check_color=ft.colors.SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.WHITE,
                label_style=ft.TextStyle(
                    color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK
                )
            )
            
            checkboxes.append(cb)
        def close_overlay():
            print("Закрываем диалог категорий...")
            if hasattr(page, 'overlay') and len(page.overlay) > 0:
                page.overlay.pop()
                page.update()
        def save_categories(e):
            selected = [cb.label for cb in checkboxes if cb.value]
            print(f"Выбранные категории: {selected}")
            if selected:
                if is_favorite:
                    favorites_manager.update_screenshot_categories(current_file, selected)
                else:
                    favorites_manager.add_to_favorites(current_file, description="", categories=selected)
            else:
                favorites_manager.remove_from_favorites(current_file)
            close_overlay()
            page.snack_bar = ft.SnackBar(content=ft.Text("Изображение сохранено в избранное"))
            page.snack_bar.open = True
            update_favorite_button()
            page.update()
        def cancel_overlay(e):
            print("Отмена выбора категорий...")
            close_overlay()
        dialog_content = ft.Container(
            content=ft.Column(
                [

                    ft.Text(
                        "Выберите категории для избранного",
                        style="titleMedium",
                        color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK,
                    ),                        
                    ft.Column(controls=checkboxes, scroll=ft.ScrollMode.AUTO, height=300, width=400),

                    ft.Row(
                    [
                        ft.FilledButton("Отмена", on_click=cancel_overlay),
                        ft.FilledButton("Сохранить", on_click=save_categories),
                    ],
                    alignment=ft.MainAxisAlignment.END)
                    
                ],
                tight=True,
                spacing=20
            ),
            width=450,
            height=450,
            padding=20,
            bgcolor=ft.colors.SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.WHITE,
            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.colors.BLACK38,
                offset=ft.Offset(0, 0),
                blur_style=ft.ShadowBlurStyle.OUTER,
            )
        )
        overlay = ft.Stack(
            [
                ft.Container(expand=True, bgcolor=ft.colors.BLACK, opacity=0.5),
                ft.Container(content=dialog_content, alignment=ft.alignment.center)
            ],
            expand=True
        )
        if not hasattr(page, 'overlay'):
            page.overlay = []
        page.overlay.append(overlay)
        print("Оверлей с диалогом добавлен и показан")
        page.update()
        print("Страница обновлена")

    favorite_button = ft.IconButton(
        icon=ft.icons.FAVORITE if is_favorite else ft.icons.FAVORITE_BORDER,
        icon_color=ft.colors.RED if is_favorite else ft.colors.GREY_500,
        icon_size=30,
        tooltip="Добавить в избранное" if not is_favorite else "Изменить категории",
        on_click=open_category_dialog,
        style=ft.ButtonStyle(color={"": ft.colors.GREY_500})
    )


    def update_image(new_index):
        nonlocal current_index, current_file, current_desc, current_source, current_ts, current_fps
        if 0 <= new_index < len(file_list):
            current_index = new_index
            new_path = file_list[new_index]
            current_file = new_path  # Обновляем текущий путь
    
            # Обновляем изображение внутри контейнера
            image_widget.content.src = new_path
    
            # Загружаем новые данные описания/таймкода/FPS
            current_desc, current_source, current_ts, current_fps = load_current_data(new_path)
            update_favorite_button()
    
            # Обновляем текст описания
            description_container.content.controls[0].value = current_desc
            # Обновляем метаданные
            navigation_row.controls[1].controls[1].value = f"Таймкод: {current_ts}"
            navigation_row.controls[1].controls[2].value = f"FPS: {current_fps}"
    
            page.update()


    def go_prev(e):
        nonlocal current_index
        if current_index > 0:
            current_index -= 1
            update_image(current_index)

    def go_next(e):
        nonlocal current_index
        if current_index < len(file_list) - 1:
            current_index += 1
            update_image(current_index)

    def open_folder(e):
        target_path = current_source if current_source else current_file
        folder_path = os.path.dirname(target_path)
        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', target_path])
        elif platform.system() == "Darwin":
            subprocess.run(['open', folder_path])
        else:
            subprocess.run(['xdg-open', folder_path])

    navigation_row = ft.Row(
        controls=[
            ft.IconButton(icon=ft.icons.ARROW_BACK, tooltip="Предыдущее изображение", on_click=go_prev),
            ft.Row(
                controls=[
                    favorite_button,
                    ft.Text(f"Таймкод: {current_ts}", size=14),
                    ft.Text(f"FPS: {current_fps}", size=14),
                    ft.Text(f"Источник: {current_source}", size=14, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ft.IconButton(icon=ft.icons.FOLDER_OPEN, tooltip="Открыть папку с исходным видео", on_click=open_folder)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
                expand=True
            ),
            ft.IconButton(icon=ft.icons.ARROW_FORWARD, tooltip="Следующее изображение", on_click=go_next)
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        expand=True
    )

    description_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(current_desc or "Нет данных от Pixtral API", size=14, selectable=True, overflow=ft.TextOverflow.CLIP)
            ],
            scroll=ft.ScrollMode.AUTO
        ),
        height=200,
        border=ft.border.all(1, ft.colors.GREY),
        padding=10
    )

    content_column = ft.Column(
        controls=[
            ft.Row(controls=[ft.ElevatedButton(text="Назад", icon=ft.icons.ARROW_BACK, on_click=lambda e: on_back() if on_back else None)]),
            image_widget,
            navigation_row,
            description_container
        ],
        spacing=10,
        scroll=ft.ScrollMode.AUTO,
        expand=True
    )

    container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Просмотр стопкадра", size=24, weight="bold"),
                content_column
            ],
            spacing=10,
            expand=True
        ),
        padding=20,
        expand=True
    )

    return container

def load_description(image_path, base_path):
    """Load description and timestamp for a given image path."""
    pixtral_json_path = f"{base_path}_pixtral.json"
    descriptions_json_path = os.path.join(os.path.dirname(image_path), "descriptions_loc.json")
    try:
        with open(pixtral_json_path, 'r', encoding='utf-8') as f:
            pixtral_data = json.load(f)
            description = pixtral_data.get(os.path.basename(image_path), {}).get("description", "")
    except FileNotFoundError:
        description = ""
    try:
        with open(descriptions_json_path, 'r', encoding='utf-8') as f:
            descriptions_data = json.load(f)
            timestamp = descriptions_data.get(os.path.basename(image_path), {}).get("timestamp", "")
    except FileNotFoundError:
        timestamp = ""
    return description, timestamp

class CategoryManager:
    """
    Класс для управления категориями
    """
    def __init__(self, favorites_manager):
        self.favorites_manager = favorites_manager

    def open_category_dialog(self, page, image_path, update_favorite_button):
        cats = self.favorites_manager.get_categories()
        print(f"CategoryManager: доступные категории: {cats}")
        if not cats:
            print("CategoryManager: создаем категорию 'Общее'")
            self.favorites_manager.add_category("Общее", "#1976D2")
            cats = self.favorites_manager.get_categories()
        if not cats:
            print("CategoryManager: не удалось создать категории")
            page.snack_bar = ft.SnackBar(content=ft.Text("Не удалось создать категории"))
            page.snack_bar.open = True
            page.update()
            return
        print(f"CategoryManager: категории после проверки: {cats}")
        checkboxes = []
        for cat in cats:
            is_checked = False
            if self.favorites_manager.is_favorite(image_path):
                screenshot_data = self.favorites_manager.get_screenshot_data(image_path)
                if screenshot_data and "categories" in screenshot_data:
                    is_checked = cat in screenshot_data["categories"]
            cb = ft.Checkbox(
                label=cat,
                value=is_checked,
                fill_color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK,
                check_color=ft.colors.SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.WHITE,
                label_style=ft.TextStyle(
                    color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK
                )
            )
            checkboxes.append(cb)
        def close_overlay():
            print("CategoryManager: закрываем диалог категорий...")
            if hasattr(page, 'overlay') and len(page.overlay) > 0:
                page.overlay.pop()
                page.update()
        def save_categories(e):
            selected = [cb.label for cb in checkboxes if cb.value]
            print(f"CategoryManager: выбранные категории: {selected}")
            if self.favorites_manager.is_favorite(image_path):
                self.favorites_manager.update_screenshot_categories(image_path, selected)
            else:
                self.favorites_manager.add_to_favorites(image_path, description="", categories=selected)
            close_overlay()
            page.snack_bar = ft.SnackBar(content=ft.Text("Изображение сохранено в избранное"))
            page.snack_bar.open = True
            update_favorite_button()
            page.update()
        def cancel_overlay(e):
            print("CategoryManager: отмена выбора категорий...")
            close_overlay()
        dialog_content = ft.Container(
            content=ft.Column(
                [

                    ft.Text(
                        "Выберите категории для избранного",
                        style="titleMedium",
                        color=ft.colors.ON_SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.BLACK,
                    ),                    
                    ft.Column(controls=checkboxes, scroll=ft.ScrollMode.AUTO, height=300, width=400),
                    
                    ft.Row([
                        ft.FilledButton("Отмена", on_click=cancel_overlay),
                        ft.FilledButton("Сохранить", on_click=save_categories),
                    ],
                    alignment=ft.MainAxisAlignment.END)

                ],
                tight=True,
                spacing=20
            ),
            width=450,
            height=450,
            padding=20,
            bgcolor=ft.colors.SURFACE if page.theme_mode == ft.ThemeMode.DARK else ft.colors.WHITE,

            border_radius=10,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.colors.BLACK38,
                offset=ft.Offset(0, 0),
                blur_style=ft.ShadowBlurStyle.OUTER,
            )
        )
        overlay = ft.Stack(
            [
                ft.Container(expand=True, bgcolor=ft.colors.BLACK, opacity=0.5),
                ft.Container(content=dialog_content, alignment=ft.alignment.center)
            ],
            expand=True
        )
        if not hasattr(page, 'overlay'):
            page.overlay = []
        page.overlay.append(overlay)
        print("CategoryManager: оверлей с диалогом добавлен и показан")
        page.update()
        print("CategoryManager: страница обновлена")

def add_to_favorites(image_path, category, favorites_manager):
    """Add the image to the specified favorites category."""
    favorites_manager.add_image_to_category(image_path, category)
    return "Image added to favorites"

def remove_from_favorites(image_path, favorites_manager):
    """Remove the image from favorites."""
    favorites_manager.remove_from_favorites(image_path)
    return "Image removed from favorites"
