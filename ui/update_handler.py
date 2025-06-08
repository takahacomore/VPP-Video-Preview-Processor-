import threading
import flet as ft
from modules.update_core import (
    get_current_version,
    load_update_manifest,
    compare_versions,
    get_update_description,
    get_files_to_update
)
from modules.updater import perform_update

def maybe_add_update_icon(update_icon, page):
    """
    Проверяет наличие обновлений и делает иконку обновлений видимой, если они доступны.
    
    Args:
        update_icon (ft.IconButton): Кнопка для отображения доступности обновлений
        page (ft.Page): Страница Flet
    """
    manifest = load_update_manifest()
    if manifest and compare_versions(get_current_version(), manifest["version"]):
        update_icon.visible = True
        page.update()

def check_and_show_update_popup(page):
    """
    Проверяет наличие обновлений и показывает диалог, если они доступны.
    
    Args:
        page (ft.Page): Страница Flet
    """
    from ui.update_popup import open_popup, close_popup
    
    manifest = load_update_manifest()
    if not manifest:
        open_popup(page, "Не удалось загрузить информацию об обновлении.", on_yes=None)
        return
    
    if compare_versions(get_current_version(), manifest["version"]):
        description = get_update_description(manifest)
        message = (
            f"Доступна новая версия {manifest['version']}.\n\n"
            f"{description}\n\n"
            "Обновить сейчас?"
        )
        
        def on_yes(e):
            # Закрываем первоначальный диалог
            close_popup(page)
            
            def do_update():
                # Скачиваем и накатываем обновления
                files = get_files_to_update(manifest)
                perform_update(files)
                # Показываем финальный диалог с инструкцией
                open_popup(
                    page,
                    "✅ Обновления установлены.\n\nПожалуйста, перезапустите программу.",
                    on_yes=None
                )
            
            # Запускаем скачивание в фоновом потоке, чтобы UI не блокировался
            threading.Thread(target=do_update, daemon=True).start()
        
        open_popup(page, message, on_yes)
    else:
        open_popup(page, "Установлена последняя версия.", on_yes=None)