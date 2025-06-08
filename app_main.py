import os
import time
import threading
import flet as ft
import logging
import sys
import subprocess

# Убираем детальные логи от flet, urllib3 и нашего search_manager
logging.getLogger("flet").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("modules.search_manager").setLevel(logging.INFO)

from pathlib import Path
from modules.ffmpeg_manager import (
    check_and_install_ffmpeg,
    show_welcome_screen
)
from modules.settings_manager import load_settings
from ui.main_view import create_main_view
from ui.settings_view import create_settings_view
from ui.favorites_view import create_favorites_view
import platform
import ctypes
from modules.search_manager import load_index, smart_search, build_index, save_index_chunks, get_current_index, start_search_monitoring

# Определяем путь к портативному Python (предполагаем, что он лежит рядом с main.py)
portable_python = os.path.join(os.path.dirname(__file__), 'python.exe')
requirements = os.path.join(os.path.dirname(__file__), 'requirements.txt')

# Попытка импортировать все модули из requirements.txt, если что-то не найдено — установить всё и перезапустить main.py
req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
if os.path.exists(req_path):
    with open(req_path, encoding="utf-8") as f:
        pkgs = [line.strip().split('==')[0].split('>=')[0].split('<=')[0] for line in f if line.strip() and not line.startswith('#')]
    need_install = False
    for pkg in pkgs:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            need_install = True
            break
    if need_install:
        python_exe = sys.executable
        subprocess.check_call([python_exe, "-m", "pip", "install", "-r", req_path])
        os.execl(python_exe, python_exe, *sys.argv)

# Если портативный Python существует, устанавливаем зависимости
if os.path.exists(portable_python) and os.path.exists(requirements):
    subprocess.run([portable_python, '-m', 'pip', 'install', '-r', requirements], check=True)

load_index()  # загружаем индекс из thumbnail_index.json
results = smart_search("ваш поисковый запрос")

load_index()
if not get_current_index():  # если индекс пуст
    index = build_index()
    save_index_chunks(index)

start_search_monitoring()  # Запуск фонового мониторинга индекса




def main(page: ft.Page):
    from modules.settings_manager import load_settings, save_settings
    from modules.enhanced_neural_processor import (
        start_enhanced_neural_processing,
        start_enhanced_neural_auto_loop
    )
    
    settings = load_settings()



    # Желаемый размер окна
    win_w, win_h = 1000, 1200

    # Устанавливаем размер
    page.window.width      = win_w
    page.window.height     = win_h
    # Фиксируем размер
    page.window.resizable  = False
    page.window.min_width  = win_w
    page.window.min_height = win_h
    page.window.max_width  = win_w
    page.window.max_height = win_h

    # Центрируем окно
    page.window.center()  # метод центрации встроен в Window API :contentReference[oaicite:0]{index=0}

    # Применяем изменения
    page.update()

    # …дальнейшая инициализация UI…


    # …далее ваша обычная инициализация UI…

    

    

    # Настройки страницы
    page.title = "Video Processor"
    page.theme_mode = ft.ThemeMode.LIGHT if settings.get("theme", "dark") == "light" else ft.ThemeMode.DARK



    # Создаем директории, если их нет
    Path("thumbnails").mkdir(exist_ok=True)



    # Состояние приложения
    current_view = "welcome"  # welcome, main, settings, favorites

    # Создаем контейнер для текущего вида
    views_container = ft.Container(expand=True)

    # Индикатор загрузки
    loading_indicator = ft.ProgressRing(width=40, height=40, visible=False)
    # Оборачиваем индикатор загрузки в контейнер с visible=False, чтобы он не перехватывал клики,
    # когда индикатор не используется.
    loading_container = ft.Container(
        content=loading_indicator,
        alignment=ft.alignment.center,
        visible=False  # Контейнер невидим по умолчанию
    )


    # Функции навигации
    def navigate_to(view_name):
        """
        Переключение между экранами приложения
        """
        nonlocal current_view

        current_view = view_name

        if view_name == "main":
            views_container.content = create_main_view(
                page,
                on_settings=lambda: navigate_to("settings"),
                on_favorites=lambda: navigate_to("favorites")
            )
        elif view_name == "settings":
            views_container.content = create_settings_view(
                page,
                on_back=lambda: navigate_to("main")
            )
        elif view_name == "favorites":
            views_container.content = create_favorites_view(
                page,
                on_back=lambda: navigate_to("main")
            )
        elif view_name == "welcome":
            views_container.content = show_welcome_screen(page)

        page.update()

    # Функции для управления отображением индикатора загрузки
    def show_loading(msg):
        loading_container.visible = True
        page.update()

    def hide_loading():
        loading_container.visible = False
        page.update()

    # Создаем структуру страницы: Stack гарантирует, что loading_container отображается поверх views_container
    page.add(
        ft.Stack([
            views_container,
            loading_container,
        ], expand=True)
    )

    # Показываем экран загрузки / приветствия
    navigate_to("welcome")

    # Проверяем наличие FFmpeg
    ffmpeg_installed = check_and_install_ffmpeg()

    # Обновляем настройки

    settings["ffmpeg_installed"] = ffmpeg_installed
    save_settings(settings)
    if settings.get("parallel_enabled", False):
        start_enhanced_neural_processing()
        start_enhanced_neural_auto_loop()
        
    # Переходим на основной экран
    navigate_to("main")


ft.app(target=main)
