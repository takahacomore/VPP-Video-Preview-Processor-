"""
Модуль для управления установкой и использованием FFmpeg
"""

import os
import zipfile
import urllib.request
import shutil
import platform
import subprocess
import sys
import tempfile
import tarfile
import flet as ft
from pathlib import Path

# Константы для работы с FFmpeg
FFMPEG_DIR = Path("FFMPEG")
FFMPEG_ZIP = FFMPEG_DIR / "ffmpeg.zip"
FFMPEG_EXE = FFMPEG_DIR / "ffmpeg.exe"
FFPROBE_EXE = FFMPEG_DIR / "ffprobe.exe"
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def is_ffmpeg_installed():
    """
    Проверяет, установлен ли FFmpeg в системе
    
    Returns:
        bool: True, если FFmpeg найден, иначе False
    """
    # Проверяем только существование файлов в папке FFMPEG
    return FFMPEG_EXE.exists() and FFPROBE_EXE.exists()

def get_ffmpeg_path():
    """
    Возвращает путь к исполняемому файлу FFmpeg
    
    Returns:
        str: Путь к FFmpeg или None, если не найден
    """
    if FFMPEG_EXE.exists():
        return str(FFMPEG_EXE)
    
    # Если ffmpeg в локальной папке нет, пытаемся найти его в системе
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
        
    return None

def get_ffprobe_path():
    """
    Возвращает путь к исполняемому файлу FFprobe
    
    Returns:
        str: Путь к FFprobe или None, если не найден
    """
    if FFPROBE_EXE.exists():
        return str(FFPROBE_EXE)
    
    # Если ffprobe в локальной папке нет, пытаемся найти его в системе
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path:
        return ffprobe_path
        
    return None

def check_and_install_ffmpeg():
    """
    Проверяет наличие FFmpeg и устанавливает его, если не найден
    
    Returns:
        bool: True, если FFmpeg установлен (или был успешно установлен), иначе False
    """
    if is_ffmpeg_installed():
        print("✅ FFmpeg уже установлен")
        return True
        
    print("⏬ FFmpeg не найден, скачиваем...")
    
    try:
        # Создаем директорию для установки
        FFMPEG_DIR.mkdir(exist_ok=True)
        
        # Скачиваем архив
        urllib.request.urlretrieve(FFMPEG_URL, FFMPEG_ZIP)
        
        # Распаковываем архив
        with zipfile.ZipFile(FFMPEG_ZIP, "r") as zip_ref:
            zip_ref.extractall(FFMPEG_DIR)
        
        # Ищем исполняемые файлы ffmpeg и ffprobe в распакованных директориях
        for root, _, files in os.walk(FFMPEG_DIR):
            if "ffmpeg.exe" in files:
                src = Path(root) / "ffmpeg.exe"
                if src != FFMPEG_EXE:
                    os.replace(src, FFMPEG_EXE)
                    print(f"✅ Скопирован файл: ffmpeg.exe")
            if "ffprobe.exe" in files:
                src = Path(root) / "ffprobe.exe"
                if src != FFPROBE_EXE:
                    os.replace(src, FFPROBE_EXE)
                    print(f"✅ Скопирован файл: ffprobe.exe")
        
        # Удаляем архив
        try:
            os.remove(FFMPEG_ZIP)
        except Exception as e:
            print(f"⚠️ Ошибка при удалении ZIP: {e}")
        
        # Проверяем успешность установки
        if is_ffmpeg_installed():
            print("✅ FFmpeg успешно установлен")
            return True
        else:
            print("❌ Не удалось установить FFmpeg")
            return False
    except Exception as e:
        print(f"❌ Ошибка при установке FFmpeg: {e}")
        return False
        
def show_welcome_screen(page):
    """
    Показывает экран приветствия во время проверки и загрузки FFMPEG
    
    Args:
        page (ft.Page): Страница для отображения
        
    Returns:
        ft.Container: Контейнер с приветственным экраном
    """
    welcome_container = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Добро пожаловать в Video Processor", size=24, weight="bold"),
                ft.Text("Приложение для обработки видеофайлов", size=16),
                ft.Divider(),
                ft.Text("Выполняется проверка FFMPEG...", size=14),
                ft.ProgressRing(width=40, height=40),
                ft.Text(
                    "FFMPEG необходим для обработки видео и создания скриншотов", 
                    size=12, 
                    italic=True,
                    color=ft.colors.SECONDARY
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )
    
    # Добавляем контейнер на страницу
    page.controls.append(welcome_container)
    page.update()
    
    return welcome_container
