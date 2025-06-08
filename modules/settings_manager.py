"""
Модуль для управления настройками приложения
"""

import os
import json

# Путь к файлу настроек
SETTINGS_FILE = "settings.json"

def load_settings():
    """
    Загружает настройки из файла
    
    Returns:
        dict: Словарь с настройками
    """
    try:
        # Проверяем, существует ли файл настроек
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                return settings
        else:
            # Если файл не существует, создаем настройки по умолчанию
            default_settings = {
                "theme": "dark",
                "language": "ru",
                "ffmpeg_installed": False,
                "active_prompt_category": "general",
                "smart_search_enabled": False,
                "very_smart_enabled": False,
                "parallel_enabled": False,
                "api_keys": [],  # Общий массив ключей для всех API
                "very_smart_enabled": False,
                "scene_edit_detection": False,
                "thumbnails_folder": "thumbnails",
                "prompt_templates": {
                    "image_description": "Опиши что изображено на этом кадре. Ответ должен быть подробным, но не слишком длинным (до 200 символов).",
                    "smart_search": "Ответь на вопрос: {query}. Найди все релевантные изображения из списка {images}. Возвращай только список имен файлов, которые соответствуют запросу."
                }
            }
            
            # Сохраняем настройки по умолчанию
            save_settings(default_settings)
            
            return default_settings
    except Exception as e:
        print(f"Ошибка при загрузке настроек: {e}")
        return {
            "theme": "dark",
            "language": "ru",
            "ffmpeg_installed": False,
            "very_smart_enabled": False,
            "smart_search_enabled": False,
            "api_keys": []
        }

def save_settings(settings):
    """
    Сохраняет настройки в файл
    
    Args:
        settings (dict): Словарь с настройками
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")

def update_settings(settings_update):
    """
    Обновляет настройки и сохраняет их в файл
    
    Args:
        settings_update (dict): Словарь с обновленными настройками
        
    Returns:
        dict: Обновленный словарь настроек
    """
    # Загружаем текущие настройки
    settings = load_settings()
    
    # Обновляем настройки
    settings.update(settings_update)
    
    # Сохраняем обновленные настройки
    save_settings(settings)

    
    return settings
