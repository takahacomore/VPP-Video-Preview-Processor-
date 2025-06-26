import os
import threading  # для запуска фонового потока при обновлении
import flet as ft
from modules.settings_manager import load_settings, update_settings, save_settings
from modules.search_manager import start_search_monitoring, stop_search_monitoring, enable_smart_search, disable_smart_search
from functools import partial



from modules.enhanced_neural_processor import (
    start_enhanced_neural_processing,
    stop_enhanced_neural_processing
)

def create_settings_view(page, on_back=None):
    """
    Создает интерфейс настроек приложения
    
    Args:
        page (ft.Page): Страница для отображения интерфейса
        on_back (callable): Функция для возврата на предыдущий экран
        
    Returns:
        ft.Container: Контейнер с интерфейсом настроек
    """
    # Загружаем настройки
    settings = load_settings()
    
    # Получаем список API ключей
    api_keys = settings.get("api_keys", [])
    
    # Создаем виджеты
    title_text = ft.Text("Настройки", size=24, weight="bold")
    def check_and_show_update_popup(page):
      print("🔍 settings_view.check_and_show_update_popup вызван")  
      from modules.update_core import get_current_version, load_update_manifest, compare_versions, get_update_description, get_files_to_update

      from modules.updater import perform_update, restart_application

      from ui.update_popup import open_popup, close_popup

    
      manifest = load_update_manifest()
      if not manifest:
          open_popup(page, "Не удалось загрузить информацию об обновлении.", on_yes=None)
          return
    
      if compare_versions(get_current_version(), manifest["version"]):
          description = get_update_description(manifest)
          message = f"Доступна новая версия {manifest['version']}.\n\n{description}\n\nОбновить сейчас?"
    



          def on_yes(e):
              # Закрываем начальный диалог
              close_popup(page)

              def do_update():
                  # Скачиваем и накатываем файлы
                  files = get_files_to_update(manifest)
                  perform_update(files)
                  # После завершения показываем финальный попап
                  open_popup(
                      page,
                      "✅ Обновления установлены.\n\nПожалуйста, перезапустите программу.",
                      on_yes=None  # только кнопка "ОК"
                  )

              # Запускаем загрузку в фоне, чтобы UI не вис
              threading.Thread(target=do_update, daemon=True).start()
          
          
          open_popup(page, message, on_yes)

      else:
           open_popup(page, "Установлена последняя версия.")          
    def on_theme_toggle(e):
        settings["theme"] = "light" if e.control.value else "dark"
        save_settings(settings)
        page.theme_mode = settings["theme"]
        page.update()
    
    
    # Обработчики событий переключателей
    def on_theme_change(e):
        toggle_theme(e.control.value)
        
    def toggle_setting(key, value):
        settings[key] = value
        save_settings(settings)
    

    def on_smart_search_change(e):
        update_settings({"smart_search_enabled": e.control.value})
        
        if e.control.value:
            enable_smart_search()  # ЗАГРУЖАЕМ МОДЕЛЬ сразу
        else:
            disable_smart_search()  # ВЫГРУЖАЕМ МОДЕЛЬ
    
        
    def on_neural_processing_change(e):
        toggle_neural_processing(e.control.value)
        
    def on_scene_detection_change(e):
        update_settings({"scene_edit_detection": e.control.value})
    
    # Переключатель темы
   # ft.Switch(value=..., on_change=on_theme_toggle)

    
    # Переключатель умного поиска

    def on_very_smart_change(e):
        val = e.control.value
        # включаем/выключаем «супер‑умный»
        update_settings({"very_smart_enabled": val})
        # если включили super — выключаем обычный
        if val:
            smart_search_switch.value = False
            update_settings({"smart_search_enabled": False})
            disable_smart_search()
        page.update()
    
    def on_smart_change(e):
        val = e.control.value
        update_settings({"smart_search_enabled": val})
        if val:
            # если включили обычный — выключаем super
            very_smart_switch.value = False
            update_settings({"very_smart_enabled": False})
        # подгружаем/выгружаем модель
        if val:
            enable_smart_search()
        else:
            disable_smart_search()
        page.update()
    
    very_smart_switch = ft.Switch(
        label="Очень умный поиск (Pixtral)",
        value=settings.get("very_smart_enabled", False),
        on_change=on_very_smart_change
    )
    smart_search_switch = ft.Switch(
        label="Умный поиск с помощью нейросети",
        value=settings.get("smart_search_enabled", True),
        on_change=on_smart_change
    )
    # Переключатель автоматической нейрообработки
    neural_switch = ft.Switch(
        label="Автоматическая обработка нейросетями",
        value=settings.get("parallel_enabled", False),
        on_change=on_neural_processing_change
    )
    
    # Переключатель обнаружения сцен
    scene_detection_switch = ft.Switch(
        label="Обнаружение сцен",
        value=settings.get("scene_edit_detection", False),
        on_change=on_scene_detection_change
    )
    
    # Контейнер для списка API ключей
    api_keys_list = ft.ListView(
        spacing=10,
        height=200,
        padding=20,
    )
    
    api_key_field = ft.TextField(
        label="API ключ Pixtral",
        hint_text="Введите API ключ для Pixtral API",
        width=400,
        password=True
    )
    
    # Функции управления
    def toggle_theme(is_dark):
        """Переключает тему приложения"""
        theme = "dark" if is_dark else "light"
        update_settings({"theme": theme})
        page.theme_mode = ft.ThemeMode.DARK if is_dark else ft.ThemeMode.LIGHT
        page.update()
    
    def toggle_neural_processing(enabled):
        """Включает/выключает автоматическую обработку нейросетями"""
        update_settings({"parallel_enabled": enabled})
        
        if enabled:
            start_enhanced_neural_processing()
        else:
            stop_enhanced_neural_processing()
    
    def add_api_key():
        """Добавляет API ключ в настройки"""
        key = api_key_field.value.strip()
        
        if not key:
            page.snack_bar = ft.SnackBar(content=ft.Text("Введите API ключ"))
            page.snack_bar.open = True
            page.update()
            return
        
        # Проверяем, есть ли уже такой ключ
        if key in api_keys:
            page.snack_bar = ft.SnackBar(content=ft.Text("Этот API ключ уже добавлен"))
            page.snack_bar.open = True
            page.update()
            return
        
        # Добавляем ключ
        api_keys.append(key)
        update_settings({"api_keys": api_keys})
        
        # Очищаем поле ввода
        api_key_field.value = ""
        
        # Обновляем список
        update_api_keys_list()
        
        page.snack_bar = ft.SnackBar(content=ft.Text("API ключ добавлен"))
        page.snack_bar.open = True
        page.update()
    
    def remove_api_key(key):
        """Удаляет API ключ из настроек"""
        api_keys.remove(key)
        update_settings({"api_keys": api_keys})
        
        # Обновляем список
        update_api_keys_list()
        
        page.snack_bar = ft.SnackBar(content=ft.Text("API ключ удален"))
        page.snack_bar.open = True
        page.update()
    
    # Создаем вспомогательную функцию для обработчиков удаления
    def make_remove_key_handler(api_key):
        def handler(e):
            remove_api_key(api_key)
        return handler
            
    def update_api_keys_list():
        """Обновляет список API ключей"""
        api_keys_list.controls.clear()
        
        if not api_keys:
            api_keys_list.controls.append(
                ft.Text("Добавьте хотя бы один API ключ для использования нейросетей", italic=True)
            )
        else:
            for key in api_keys:
                # Маскируем ключ для отображения (первые 8 символов + ***)
                masked_key = key[:8] + "***" + key[-4:] if len(key) > 12 else key[:4] + "***"
                
                api_keys_list.controls.append(
                    ft.Row([
                        ft.Text(masked_key, expand=True),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            tooltip="Удалить",
                            on_click=make_remove_key_handler(key)
                        )
                    ])
                )
        
        page.update()
    
    # Обработчики для кнопок действий
    def on_back_click(e):
        if on_back:
            on_back()
            
    def on_add_key_click(e):
        add_api_key()

   

        
    # Кнопки действий
    back_button = ft.ElevatedButton(
        text="Назад",
        icon=ft.icons.ARROW_BACK,
        on_click=on_back_click
    )
    
    add_key_button = ft.ElevatedButton(
        text="Добавить ключ",
        icon=ft.icons.ADD,
        on_click=on_add_key_click
    )
    
    

    features_section = ft.Container(
        content=ft.Column([
            ft.Text("Функции", size=18, weight="bold"),
            smart_search_switch,
            very_smart_switch,
            neural_switch,
            scene_detection_switch,
        ], spacing=10),
        padding=ft.padding.only(bottom=20)
    )

    print("🔍 check_and_show_update_popup вызван")

    api_section = ft.Container(
        content=ft.Column([
            ft.Text("API ключи для Pixtral", size=18, weight="bold"),
            ft.Text(
                "Каждый новый ключ будет рассматриваться как отдельный workspace и использоваться для баланса нагрузки.",
                size=14,
                italic=True
            ),
            api_keys_list,
            ft.Row([
                api_key_field,
                add_key_button,
            ], spacing=10),
            ft.ElevatedButton(  # ← ДОБАВЛЯЕМ СЮДА!
                text="Проверить обновления",
                icon=ft.icons.UPDATE,
                on_click=lambda e: check_and_show_update_popup(page)
            ),
        ], spacing=10),
        padding=ft.padding.only(bottom=20)
    )

     # Обновляем список API ключей при первом отображении
    update_api_keys_list()
    
    # Категории промпта
    category_labels = {
        "general": "Общий",
        "chronicle": "Хроника",
        "architecture": "Архитектура",
        "archive": "Архив"
    }
    

    
    def on_category_toggle(selected_key):
        for key, switch in category_switches.items():
            switch.value = (key == selected_key)
        settings["active_prompt_category"] = selected_key
        save_settings(settings)
        page.update()
    
    category_switches = {}
    
    category_row = ft.Row(alignment=ft.MainAxisAlignment.START, spacing=20)
    
    for key, label in category_labels.items():
        switch = ft.Switch(
            label=label,
            value=settings.get("active_prompt_category", "general") == key,
            on_change=lambda e, k=key: on_category_toggle(k)
        )
        category_switches[key] = switch
        category_row.controls.append(switch)
       
    # --- Новая кнопка для связи ---
    def on_contact_click(e):
        page.launch_url("https://t.me/+1eMX83XrfDMzOWRi")

    contact_button = ft.TextButton(
        text="Связаться с разработчиком",
        icon=ft.icons.SEND_ROUNDED,
        on_click=on_contact_click,
        style=ft.ButtonStyle(color=ft.colors.BLUE_400)
    )

    # Компоновка интерфейса
    settings_container = ft.Container(
        content=ft.Column([
            ft.Row([
                back_button,
                title_text,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1),
            ft.Column([
                features_section,
                ft.Text("Категория промпта", style="titleMedium"),
                category_row,
                api_section,
                ft.Row(
                    controls=[contact_button],
                    alignment=ft.MainAxisAlignment.CENTER
                )
            ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True),
        ], spacing=20, expand=True),
        padding=20,
        expand=True,
    )
    
    # Обновляем список API ключей при первом отображении
    update_api_keys_list()

    

    
    return settings_container
