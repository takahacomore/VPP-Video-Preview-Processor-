"""
Модуль для работы с Pixtral API (обработка изображений)
"""

import os
import json
import base64
import requests
from modules.settings_manager import load_settings


class PixtralAPI:
    """
    Класс для работы с API Pixtral для обработки изображений
    """
    def __init__(self, api_keys=None):
        """
        Инициализирует экземпляр API
        
        Args:
            api_keys (list): Список API ключей для Pixtral API
        """
        self.api_keys = api_keys or []
        
        # Если ключи не переданы, пытаемся загрузить из настроек
        if not self.api_keys:
            settings = load_settings()
            self.api_keys = settings.get("api_keys", [])
                
        self.current_key_index = 0
        
    def _get_next_key(self):
        """
        Возвращает следующий API ключ из списка
        
        Returns:
            str: API ключ или None, если ключи не найдены
        """
        if not self.api_keys:
            return None
            
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key


    def ask_yes_no(self, image_path: str, query: str) -> bool:
        prompt = (
            "Ты — мультимодальная система. Посмотри на стопкадр и "
            f"реши, соответствует ли он поисковому запросу «{query}». "
            "Ответь только «да» или только «нет»."
        )
        response = self.process_image(image_path, prompt, language="ru")
        if not response:
            return False
        text = response.strip().lower()
        return text.startswith("д")
    
    def process_image(self, image_path, prompt, language="ru"):
        """
        Обрабатывает изображение с помощью модели Pixtral
        
        Args:
            image_path (str): Путь к изображению
            prompt (str): Текстовый запрос для обработки изображения
            language (str): Язык ответа (ru или en)
        
        Returns:
            str: Описание изображения или None в случае ошибки
        """
        api_key = self._get_next_key()
        if not api_key:
            print("Ошибка: API ключи не настроены")
            return None
            
        # Кодируем изображение
        image_base64 = self._encode_image(image_path)
        if not image_base64:
            return None
            
        try:
            # Pixtral API использует тот же эндпоинт, что и другие модели Mistral
            url = "https://api.mistral.ai/v1/chat/completions"
            

            with open(os.path.join(os.path.dirname(__file__), "prompt_categories.json"), encoding="utf-8") as f:
                prompt_templates = json.load(f)
            
            settings = load_settings()
            category = settings.get("active_prompt_category", "general")
            category_prompt = prompt_templates.get(category, "")
            
            base_prompt = f"""

            Ты — мультимодальная система анализа изображений. На вход подаётся стопкадр из видео. 
            Твоя задача — проанализировать сцену и создать точное описание содержимого без вводных фраз. 
            Не начинай описание со слов "На изображении", "Видно", "Можно увидеть" и подобных вводных конструкций. 
            Начинай сразу с описания ключевых объектов или действия. Используй фразы о содержимом изображения только при необходимости, например: "картина на изображении...".
            
            Определи видимые объекты, архитектурные стили, временные контексты, атмосферу, и любые отличимые элементы. 
            Если возможно, определи сезон (время года), исходя из ландшафта, освещения, одежды или других признаков. 
            Если сезон явно не определяется — не упоминай его.
            
            В конце обязательно добавь строку с тегами в формате: Теги: объект1, объект2, объект3.
   
            
            {category_prompt}
            """
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            # Создаем сообщение с изображением
            image_content = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            data = {
                "model": "pixtral-12b-2409",  # Используем Pixtral модель для изображений
                "messages": [
                    {
                        "role": "system",
                        "content": base_prompt.strip()
                    },
                    {
                        "role": "user",
                        "content": image_content
                    }
                ],
                "temperature": 0.7,
                "top_p": 1,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"].strip()
            else:
                print(f"Ошибка API Pixtral: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Ошибка при обработке изображения через Pixtral API: {e}")
            return None
            
    def _encode_image(self, image_path):
        """
        Кодирует изображение в base64
        
        Args:
            image_path (str): Путь к изображению
        
        Returns:
            str: Строка в формате base64 или None в случае ошибки
        """
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"Ошибка при кодировании изображения: {e}")
            return None
