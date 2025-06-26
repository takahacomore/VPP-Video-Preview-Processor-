import os
import threading
import time
import flet as ft
import logging
from pathlib import Path
from modules.video_processor import start_processing, stop_processing, get_thumbnail_by_video_path
from modules.search_manager import (
    search_in_index,
    smart_search,
    very_smart_filter,
    get_current_index,
    start_search_monitoring,
    enable_smart_search,
    smart_keyword_search,
)
from modules.enhanced_neural_processor import start_enhanced_neural_processing, stop_enhanced_neural_processing
from ui.image_view import create_image_view
from modules.settings_manager import load_settings, get_server_enabled, set_server_enabled
from modules.update_core import get_current_version, load_update_manifest, compare_versions
from modules.server_manager import start_server, stop_server

logger = logging.getLogger(__name__)



def create_main_view(page, on_settings=None, on_favorites=None):
    page.snack_bar = ft.SnackBar(content=ft.Text(""))

    thumbs_dir = Path("thumbnails")
    thumbs_dir.mkdir(exist_ok=True)
    last_loaded_count = -1

    has_selected_files = False
    selected_files = []
    selected_directory = None

    current_view = "thumbnails"
    current_query = ""
    current_page = 0
    filtered_results = []
    page_thumbnails = []

    model_loader = ft.ProgressRing(width=24, height=24, visible=False)
   #def update_if_changed(query_str):
   #    nonlocal current_query
   #    # Если значение не изменилось, не отправляем новый запрос
   #    if query_str == current_query:
   #        return
   #    current_query = query_str
   #    update_search_results(perform_search(query_str))
   #
    def perform_search(query):
        query = query.strip()
        if not query:
            return list(get_current_index().keys())

        settings = load_settings()
        use_smart = settings.get("smart_search_enabled", False)
        use_very  = settings.get("very_smart_enabled", False)

        if use_very:
            candidates = smart_search(query, force=True)
            logger.info(f"Кандидатов от smart_search: {len(candidates)}")
            return very_smart_filter(candidates, query)

        if use_smart:
            return smart_search(query, force=True)

        return smart_keyword_search(query)
    def update_search_results(results):
        nonlocal filtered_results
        filtered_results = results
        load_thumbnails_from_results()




    def check_and_show_update_popup_async(page):
        threading.Thread(target=check_and_show_update_popup, args=(page,), daemon=True).start()

    
    def load_model_async():
        settings = load_settings()
        if settings.get("smart_search_enabled", False):
            model_loader.visible = True
            set_status("🧠 Загружается модель умного поиска...", loading=True)
            page.update()
    
            enable_smart_search()
    
            model_loader.visible = False
            set_status("✅ Модель загружена", loading=False)
            page.update()




    def on_select_files(e):
        """Выбирает видеофайлы для обработки"""
        nonlocal has_selected_files, selected_files
        set_status(f"📄 Выбрано {len(selected_files)} файлов", loading=False)
       
        def pick_files_result(e: ft.FilePickerResultEvent):
            nonlocal has_selected_files, selected_files
            
            if e.files:
                selected_files = [file.path for file in e.files]
                video_files_text.value = f"Выбрано {len(selected_files)} файлов"
                has_selected_files = True
                page.update()
        
        pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
        page.overlay.append(pick_files_dialog)
        page.update()
        
        # Показываем диалог выбора файлов
        pick_files_dialog.pick_files(
            allow_multiple=True,
            allowed_extensions=["mp4", "avi", "mov", "mkv", "mxf", "webm", "mkv", "ts", "mts"]
        )

    def on_select_directory(e):
        """Выбирает директорию для обработки"""
        nonlocal has_selected_files, selected_directory
        
        def pick_directory_result(e: ft.FilePickerResultEvent):
            nonlocal has_selected_files, selected_directory
            
            if e.path:
                selected_directory = e.path
                video_files_text.value = f"Выбрана папка: {os.path.basename(selected_directory)}"
                has_selected_files = True
                set_status(f"📂 Выбрана папка: {os.path.basename(selected_directory)}", loading=False)
                page.update()
        
        pick_directory_dialog = ft.FilePicker(on_result=pick_directory_result)
        page.overlay.append(pick_directory_dialog)
        page.update()
        
        # Показываем диалог выбора директории
        pick_directory_dialog.get_directory_path()

    def maybe_add_update_icon():
        manifest = load_update_manifest()
        if manifest and compare_versions(get_current_version(), manifest["version"]):
            update_icon.visible = True
            page.update()
    
    update_icon = ft.IconButton(
        icon=ft.icons.SYSTEM_UPDATE,
        tooltip="Обновление доступно!",
        visible=False,
        on_click=lambda e: check_and_show_update_popup_async(page)
    )

# в appbar.append(update_icon) — и потом вызвать maybe_add_update_icon()
    def on_start_processing(e):
        nonlocal has_selected_files, selected_directory, selected_files
    
        if not has_selected_files:
            set_status("❌ Ошибка: файлы не выбраны", loading=False)
            return
    
        if selected_directory:
            set_status(f"📂 Обработка видео из папки: {os.path.basename(selected_directory)}...", loading=True)
        elif selected_files:
            if len(selected_files) == 1:
                set_status(f"🎞️ Обработка видео: {os.path.basename(selected_files[0])}...", loading=True)
            else:
                set_status(f"🎞️ Обработка {len(selected_files)} видеофайлов...", loading=True)
        else:
            set_status("❌ Ошибка: не удалось найти файлы для обработки", loading=False)
            return
    
        def on_processing_complete():
            set_status("✅ Обработка завершена", loading=False)
            perform_search(current_query)  # обновляем результат
            settings = load_settings()
            if settings.get("parallel_enabled", False):
                from modules.enhanced_neural_processor import start_enhanced_neural_processing
                start_enhanced_neural_processing()
                set_status("🧠 Запущена автоматическая нейрообработка", loading=True)
            page.update()
    
        if selected_directory:
            start_processing(folder_path=selected_directory, on_update=on_processing_complete)
        elif selected_files:
            start_processing(file_paths=selected_files, on_update=on_processing_complete)
    
    

        def on_processing_complete():
            set_status("✅ Обработка завершена", loading=False)
            perform_search(current_query)  # обновляем результат
            settings = load_settings()
        
            if settings.get("parallel_enabled", False):
                from modules.enhanced_neural_processor import (
                    start_enhanced_neural_processing,
                    get_enhanced_neural_processor
                )
                start_enhanced_neural_processing()
        
                # После старта задаём коллбэк на завершение обработки
                processor = get_enhanced_neural_processor()
        
                # вызывается при завершении обработки каждого кадра
                def on_neural_done(path, result):
                    # Если очередь пуста — сбрасываем статус
                    if not processor.queued_files:
                        set_status("✅ Нейрообработка завершена", loading=False)
        
                processor.on_file_processed = on_neural_done
        
            page.update()

    

    def on_stop_processing(e):
        stop_processing()
        set_status("🛑 Обработка остановлена", loading=False)
        stop_enhanced_neural_processing()
        page.update()

    
    
    def load_thumbnails_from_results():
        nonlocal current_page, filtered_results, page_thumbnails
        items_per_page = 25
        total_thumbnails = len(filtered_results)
        total_pages = (total_thumbnails + items_per_page - 1) // items_per_page
    
        if current_page >= total_pages and total_pages > 0:
            current_page = total_pages - 1
        elif current_page < 0:
            current_page = 0
    
        prev_button.disabled = current_page <= 0
        next_button.disabled = (current_page >= total_pages - 1 or total_pages <= 1)
        page_text.value = f"Страница {current_page + 1} из {max(total_pages, 1)}"
    
        start_idx = current_page * items_per_page
        end_idx = min(start_idx + items_per_page, total_thumbnails)
        page_thumbnails = filtered_results[start_idx:end_idx]
    
        thumbnails_grid.controls.clear()
    
        if not page_thumbnails:
            thumbnails_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.IMAGE_NOT_SUPPORTED, size=50),
                        ft.Text("Нет доступных изображений", style="bodyMedium"),
                        ft.Text("Попробуйте изменить запрос или загрузить новые файлы", style="bodySmall"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
        else:
            for path in page_thumbnails:
                thumbnails_grid.controls.append(
                    ft.Container(
                        width=150,
                        height=150,
                        bgcolor=ft.colors.with_opacity(0.04, ft.colors.ON_BACKGROUND),
                        border_radius=ft.border_radius.all(10)
                    )
                )
    
        page.update()
    
        def update_images():
            for i, path in enumerate(page_thumbnails):
                full_path = os.path.join("thumbnails", path)
                image = ft.Image(
                    src=full_path,
                    width=150,
                    height=150,
                    fit=ft.ImageFit.COVER,
                    border_radius=ft.border_radius.all(10)
                )
                container = ft.Container(
                    content=image,
                    width=150,
                    height=150,
                    border_radius=ft.border_radius.all(10),
                    ink=True,
                    on_click=lambda e, p=path, img_list=page_thumbnails: on_image_click(
                        os.path.join("thumbnails", p),
                        [os.path.join("thumbnails", i) for i in img_list]
                    ),
                )
                thumbnails_grid.controls[i] = container
                page.update()
    
        threading.Thread(target=update_images, daemon=True).start()
    
    
    def load_thumbnails_from_results_page(page_num):
        nonlocal current_page
        current_page = page_num
        load_thumbnails_from_results()
    
    





    
    def perform_search(query):
        query = query.strip()
        if not query:
            return list(get_current_index().keys())
    
        settings = load_settings()
        use_smart = settings.get("smart_search_enabled", False)
        use_very  = settings.get("very_smart_enabled", False)
    
        # 1) «Супер‑умный» = сначала semantic‑search, потом Pixtral‑filter

        if use_very:
            candidates = smart_search(query, force=True)
            logger.info(f"Кандидатов от smart_search: {len(candidates)}")
            return very_smart_filter(candidates, query)

    
        # 2) Только semantic
        if use_smart:
            return smart_search(query, force=True)
    
        # 3) Обычный keyword‑search
        return smart_keyword_search(query)
    
    
    

    # Элементы интерфейса
    video_files_text = ft.Text("Выбрано 0 файлов", size=14, color=ft.colors.ON_SURFACE_VARIANT)
    processing_status = ft.Text("Готов к обработке", size=14, color=ft.colors.ON_SURFACE_VARIANT)


    settings = load_settings()

    status_text = ft.Text("Готов к обработке", size=14, color=ft.colors.ON_SURFACE_VARIANT)
    status_spinner = ft.ProgressRing(width=16, height=16, visible=False)
    # Создаем поле поиска

    search_field = ft.TextField(
        label="Поиск",
        hint_text="Введите текст для поиска",
        prefix_icon=ft.icons.SEARCH,
        expand=True,
    )
    # Используем только on_submit – запрос отправляется при нажатии Enter


    search_field.on_submit = lambda e: (
        set_status("🔍 Поиск...", loading=True),
        update_search_results(perform_search(e.control.value)),
        set_status("✅ Результаты обновлены", loading=False)
    )



    # добавим on_change, чтобы при очистке сразу вернуть все без Enter
    def on_search_change(e):
        # если поле опустело — сбрасываем поиск
        if not e.control.value.strip():
            update_search_results(perform_search(""))
    
    search_field.on_change = on_search_change
    




    #search_field.on_submit = lambda e: update_search_results(perform_search(e.control.value))

        
    

    # Сетка для отображения 12 миниатюр (например, 4 столбца, 3 ряда)
    thumbnails_grid = ft.GridView(
        expand=True,
        runs_count=4,
        max_extent=200,
        child_aspect_ratio=1.0,
        spacing=10,
        run_spacing=10,
        padding=20,
    )

    # Контейнер для просмотра изображения, по умолчанию скрыт
    image_view_container = ft.Container(expand=True, visible=False)

    # Панель пагинации



    prev_button = ft.IconButton(
        icon=ft.icons.ARROW_BACK,
        tooltip="Предыдущая страница",
        disabled=True,
        on_click=lambda e: load_thumbnails_from_results_page(current_page - 1),
    )
    
    next_button = ft.IconButton(
        icon=ft.icons.ARROW_FORWARD,
        tooltip="Следующая страница",
        disabled=True,
        on_click=lambda e: load_thumbnails_from_results_page(current_page + 1),
    )
    

    page_text = ft.Text("Страница 1", size=14)

    pagination = ft.Row(
        controls=[prev_button, page_text, next_button],
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # Панель инструментов

    toolbar = ft.Row([
        ft.IconButton(icon=ft.icons.INSERT_DRIVE_FILE, tooltip="Выбрать видео", on_click=on_select_files),
        ft.IconButton(icon=ft.icons.FOLDER_OPEN, tooltip="Выбрать папку", on_click=on_select_directory),
        ft.IconButton(icon=ft.icons.PLAY_ARROW, tooltip="Обработать", on_click=on_start_processing),
        ft.IconButton(icon=ft.icons.STOP, tooltip="Остановить", on_click=on_stop_processing),
        ft.Container(width=20),
        search_field,
        model_loader,  # <-- добавили сюда
    ], alignment=ft.MainAxisAlignment.START)



    # Индикатор активности
    status_spinner = ft.ProgressRing(width=16, height=16, visible=False)
    
    # Текст статуса
    status_text = ft.Text("Готов к обработке", size=14, color=ft.colors.ON_SURFACE_VARIANT)
    
    status_bar = ft.Row([
        status_text,
        ft.Container(width=10),
        status_spinner,
    ], alignment=ft.MainAxisAlignment.START)

    # Основной контейнер со всеми элементами
    view = ft.Container(
        content=ft.Column([
            toolbar,
            ft.Divider(height=1),
            ft.Stack([thumbnails_grid, image_view_container], expand=True),
            ft.Divider(height=1),
            pagination,
            status_bar,
        ], spacing=10, expand=True),
        padding=10,
        expand=True,
    )

    # Контейнер загрузки
    loading_container = ft.Container(
        content=ft.Column([
            ft.ProgressRing(width=40, height=40),
            ft.Text("Загрузка...", style="bodyMedium"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        alignment=ft.alignment.center,
        expand=True,
        bgcolor=ft.colors.with_opacity(0.7, ft.colors.BLACK),
        visible=False,
    )

    container_with_loading = ft.Stack(
        controls=[view, loading_container],
        expand=True,
    )

    # Функция для возврата к просмотру миниатюр


    def set_status(message: str, loading: bool = False):
        status_text.value = message
        status_spinner.visible = loading
        page.update()


    def show_thumbnails():
        image_view_container.visible = False
        thumbnails_grid.visible = True
        load_thumbnails_from_results()  # восстанавливаем ту же страницу
        page.update()


    # Обновленный обработчик клика по миниатюре. Теперь принимает два параметра:
    # image_path и список изображений с текущей страницы.
    def on_image_click(image_path, image_list):
        image_view = create_image_view(
            page,
            current_file=image_path,
            all_files=image_list,
            return_page=0,
            search_query=current_query,
            page_number=current_page,
            on_back=show_thumbnails
        )
        thumbnails_grid.visible = False
        image_view_container.visible = True
        image_view_container.content = image_view
        page.update()


    
    def update_images():
        for i, path in enumerate(page_thumbnails):
            full_path = os.path.join("thumbnails", path)
            image = ft.Image(
                src=full_path,
                width=150,
                height=150,
                fit=ft.ImageFit.COVER,
                border_radius=ft.border_radius.all(10)
            )
            container = ft.Container(
                content=image,
                width=150,
                height=150,
                border_radius=ft.border_radius.all(10),
                ink=True,
                on_click=lambda e, p=path, img_list=page_thumbnails: on_image_click(
                    os.path.join("thumbnails", p),
                    [os.path.join("thumbnails", i) for i in img_list]
                ),
            )
            thumbnails_grid.controls[i] = container
            page.update()
    
    #threading.Thread(target=update_images, daemon=True).start()
    

    # Первичная загрузка миниатюр (в отдельном потоке)
    threading.Thread(target=lambda: update_search_results(perform_search("")), daemon=True).start()


    # Обработчики для кнопок AppBar
    def on_favorites_click(e):
        if on_favorites:
            on_favorites()
            
    def on_settings_click(e):
        if on_settings:
            on_settings()
    def on_theme_toggle(e):
        settings = load_settings()
        settings["theme"] = "light" if e.control.value else "dark"
        from modules.settings_manager import save_settings
        save_settings(settings)
        page.theme_mode = settings["theme"]
        page.update()
    
    theme_switch = ft.Switch(
        value=load_settings().get("theme", "dark") == "light",
        on_change=on_theme_toggle
    )    
    def on_server_toggle(e):
        enabled = e.control.value
        set_server_enabled(enabled)
        if enabled:
            start_server()
            page.snack_bar = ft.SnackBar(content=ft.Text("Сервер запущен"))
        else:
            stop_server()
            page.snack_bar = ft.SnackBar(content=ft.Text("Сервер остановлен"))
        page.snack_bar.open = True
        page.update()

    server_switch = ft.Switch(
        value=get_server_enabled(),
        label="API сервер",
        on_change=on_server_toggle
    )

    # --- Новый кликабельный копирайт ---
    def on_copyright_click(e):
        page.launch_url("https://www.takahacomore.ru/about/")

    copyright_link = ft.TextButton(
        content=ft.Text(
            "©takahacomore",
            size=12,
            color="grey",
            italic=True
        ),
        on_click=on_copyright_click,
        style=ft.ButtonStyle(
            padding=ft.padding.only(left=10),
            overlay_color=ft.colors.TRANSPARENT,
        )
    )

    # Создаем AppBar для страницы, если его еще нет
    if not page.appbar:

        page.appbar = ft.AppBar(
            leading=ft.Icon(ft.icons.VIDEO_CAMERA_BACK_ROUNDED),
            leading_width=40,
            title=ft.Row([
                ft.Text("Video Processor"),
                copyright_link  # Добавляем копирайт
            ]),
            center_title=False,
            bgcolor=ft.colors.SURFACE_VARIANT,
            actions=[
                ft.Row(
                    controls=[
                        ft.Icon(name=ft.icons.DARK_MODE),
                        theme_switch,
                        ft.Icon(name=ft.icons.LIGHT_MODE),
                        server_switch,
                    ],
                    spacing=5,
                ),                                  
                update_icon,  # вот сюда добавь!
                ft.IconButton(
                    icon=ft.icons.FAVORITE,
                    tooltip="Избранное",
                    on_click=on_favorites_click,
                ),
                ft.IconButton(
                    icon=ft.icons.SETTINGS,
                    tooltip="Настройки",
                    on_click=on_settings_click,
                ),
            ],
        )
        
        page.update()    
    threading.Thread(target=start_search_monitoring, daemon=True).start()



    def start_thumbnail_auto_refresh():
        def refresh_loop():
            nonlocal last_loaded_count
            while True:
                current_index = get_current_index()
                count = len(current_index)
    
                if count != last_loaded_count:
                    last_loaded_count = count
    
                    # обновляем только если ты в главном окне и НЕ в предпросмотре
                    if current_view == "main" and not image_view_container.visible:
                        print("🔁 Обнаружены новые стопкадры — обновляем интерфейс")
                        update_search_results(perform_search(current_query))
    
                time.sleep(5)  # можно уменьшить до 3 для большей "живости"
    
        threading.Thread(target=refresh_loop, daemon=True).start()
    

    
    
    start_thumbnail_auto_refresh()
    
    maybe_add_update_icon()

    return container_with_loading
