"""
Модуль для управления избранными скриншотами
"""

import os
import json
import time
from pathlib import Path

class FavoritesManager:
    """
    Класс для управления избранными скриншотами.
    Обеспечивает сохранение, загрузку и категоризацию избранных скриншотов.
    """
    
    def __init__(self, favorites_file="favorites.json"):
        """
        Инициализирует менеджер избранного
        
        Args:
            favorites_file (str): Путь к файлу с данными избранного
        """
        self.favorites_file = favorites_file
        self.favorites = {}
        self.categories = {}
        self._load_favorites()
        
    def _load_favorites(self):
        """
        Загружает данные избранного из файла
        """
        try:
            # Проверяем, существует ли файл с избранным
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Загружаем категории, проверяя структуру
                    if "categories" in data and isinstance(data["categories"], dict):
                        self.categories = data["categories"]
                    else:
                        self.categories = {}
                        
                    # Загружаем избранные скриншоты, проверяя структуру
                    if "favorites" in data and isinstance(data["favorites"], dict):
                        self.favorites = data["favorites"]
                    else:
                        self.favorites = {}
            else:
                # Если файл не существует, создаем начальные данные
                self.categories = {
                    "Общее": {
                        "color": "#1976D2",
                        "order": 0
                    }
                }
                self.favorites = {}
                
                # Сохраняем начальные данные
                self._save_favorites()
                
        except Exception as e:
            print(f"Ошибка при загрузке данных избранного: {e}")
            # В случае ошибки используем пустые данные
            self.categories = {
                "Общее": {
                    "color": "#1976D2",
                    "order": 0
                }
            }
            self.favorites = {}




    def rename_category(self, old_name, new_name):
        if old_name in self.categories:
            print(f"[DEBUG] До переименования: {self.categories}")
            self.categories[new_name] = self.categories.pop(old_name)
            self._save_favorites()
            print(f"[DEBUG] После переименования: {self.categories}")
            return True
        print(f"[DEBUG] Категория '{old_name}' не найдена для переименования")
        return False





    def remove_category(self, category_name):
        if category_name not in self.categories:
            print(f"[DEBUG] Категория '{category_name}' не найдена")
            return False
        if category_name == "Общее":
            print("[DEBUG] Нельзя удалить категорию 'Общее'")
            return False
        print(f"[DEBUG] До удаления: {self.categories}")
        del self.categories[category_name]
        for screenshot, data in self.favorites.items():
            if "categories" in data and category_name in data["categories"]:
                data["categories"].remove(category_name)
        self._save_favorites()
        print(f"[DEBUG] После удаления: {self.categories}")
        return True
    
                
    def _save_favorites(self):
        """
        Сохраняет данные избранного в файл
        """
        try:
            # Создаем структуру для сохранения
            data = {
                "categories": self.categories,
                "favorites": self.favorites
            }
            
            # Сохраняем в файл
            with open(self.favorites_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            print(f"Ошибка при сохранении данных избранного: {e}")
            
    def add_category(self, category_name, category_color="#1976D2"):
        """
        Добавляет новую категорию
        
        Args:
            category_name (str): Название категории
            category_color (str): Цвет категории в формате HEX
            
        Returns:
            bool: True, если категория успешно добавлена, иначе False
        """
        # Проверяем, существует ли уже такая категория
        if category_name in self.categories:
            print(f"Категория '{category_name}' уже существует")
            return False
            
        # Получаем максимальный порядковый номер для новой категории
        max_order = 0
        for cat in self.categories.values():
            if "order" in cat and cat["order"] > max_order:
                max_order = cat["order"]
                
        # Добавляем новую категорию
        self.categories[category_name] = {
            "color": category_color,
            "order": max_order + 1
        }
        
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def remove_category(self, category_name):
        """
        Удаляет категорию
        
        Args:
            category_name (str): Название категории
            
        Returns:
            bool: True, если категория успешно удалена, иначе False
        """
        # Проверяем, существует ли категория
        if category_name not in self.categories:
            print(f"Категория '{category_name}' не найдена")
            return False
            
        # Нельзя удалить категорию "Общее"
        if category_name == "Общее":
            print("Нельзя удалить категорию 'Общее'")
            return False
            
        # Удаляем категорию
        del self.categories[category_name]
        
        # Удаляем категорию из всех скриншотов
        for screenshot, data in self.favorites.items():
            if "categories" in data and category_name in data["categories"]:
                data["categories"].remove(category_name)
                
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def get_categories(self):
        """
        Возвращает список всех категорий
        
        Returns:
            dict: Словарь категорий в формате {название: {color: цвет, order: порядок}}
        """
        return self.categories
        
    def add_to_favorites(self, screenshot_path, description="", categories=None):
        """
        Добавляет скриншот в избранное
        
        Args:
            screenshot_path (str): Путь к скриншоту
            description (str): Описание скриншота
            categories (list): Список категорий для скриншота
            
        Returns:
            bool: True, если скриншот успешно добавлен, иначе False
        """
        # Проверяем, существует ли файл
        if not os.path.exists(screenshot_path):
            print(f"Файл '{screenshot_path}' не существует")
            return False
            
        # Если категории не указаны, используем "Общее"
        if not categories:
            categories = ["Общее"]
            
        # Проверяем, существуют ли указанные категории
        for category in categories:
            if category not in self.categories:
                print(f"Категория '{category}' не существует, добавляем в 'Общее'")
                categories = ["Общее"]
                break
                
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Добавляем скриншот в избранное
        self.favorites[norm_path] = {
            "description": description,
            "categories": categories,
            "added_at": self._get_timestamp()
        }
        
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def remove_from_favorites(self, screenshot_path):
        """
        Удаляет скриншот из избранного
        
        Args:
            screenshot_path (str): Путь к скриншоту
            
        Returns:
            bool: True, если скриншот успешно удален, иначе False
        """
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Проверяем, есть ли скриншот в избранном
        if norm_path not in self.favorites:
            print(f"Скриншот '{norm_path}' не найден в избранном")
            return False
            
        # Удаляем скриншот из избранного
        del self.favorites[norm_path]
        
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def is_favorite(self, screenshot_path):
        """
        Проверяет, находится ли скриншот в избранном
        
        Args:
            screenshot_path (str): Путь к скриншоту
            
        Returns:
            bool: True, если скриншот находится в избранном, иначе False
        """
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Проверяем наличие скриншота в избранном
        return norm_path in self.favorites
        
    def get_screenshot_data(self, screenshot_path):
        """
        Возвращает данные о скриншоте из избранного
        
        Args:
            screenshot_path (str): Путь к скриншоту
            
        Returns:
            dict: Данные о скриншоте или None, если скриншот не найден
        """
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Возвращаем данные о скриншоте, если он есть в избранном
        if norm_path in self.favorites:
            return self.favorites[norm_path]
            
        return None
        
    def get_favorites(self, category=None):
        """
        Возвращает список избранных скриншотов
        
        Args:
            category (str): Название категории для фильтрации (если указано)
            
        Returns:
            dict: Словарь скриншотов в формате {путь: {description: описание, categories: категории, added_at: дата}}
        """
        # Если категория не указана, возвращаем все избранное
        if not category:
            return self.favorites
            
        # Фильтруем скриншоты по категории
        filtered = {}
        for path, data in self.favorites.items():
            if "categories" in data and category in data["categories"]:
                filtered[path] = data
                
        return filtered
        
    def update_screenshot_categories(self, screenshot_path, categories):
        """
        Обновляет категории скриншота
        
        Args:
            screenshot_path (str): Путь к скриншоту
            categories (list): Новый список категорий
            
        Returns:
            bool: True, если категории успешно обновлены, иначе False
        """
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Проверяем, есть ли скриншот в избранном
        if norm_path not in self.favorites:
            print(f"Скриншот '{norm_path}' не найден в избранном")
            return False
            
        # Проверяем, существуют ли указанные категории
        for category in categories:
            if category not in self.categories:
                print(f"Категория '{category}' не существует")
                return False
                
        # Обновляем категории
        self.favorites[norm_path]["categories"] = categories
        
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def update_screenshot_description(self, screenshot_path, description):
        """
        Обновляет описание скриншота
        
        Args:
            screenshot_path (str): Путь к скриншоту
            description (str): Новое описание
            
        Returns:
            bool: True, если описание успешно обновлено, иначе False
        """
        # Нормализуем путь
        norm_path = os.path.normpath(screenshot_path)
        
        # Проверяем, есть ли скриншот в избранном
        if norm_path not in self.favorites:
            print(f"Скриншот '{norm_path}' не найден в избранном")
            return False
            
        # Обновляем описание
        self.favorites[norm_path]["description"] = description
        
        # Сохраняем изменения
        self._save_favorites()
        
        return True
        
    def _get_timestamp(self):
        """
        Возвращает текущую временную метку
        
        Returns:
            int: Текущее время в миллисекундах
        """
        return int(time.time() * 1000)
